"""
Video processing pipeline with sport-specific movement analysis.

Processes video frame-by-frame:
- Pose estimation (MediaPipe)
- Movement recognition (generic -> sport-specific mapping)
- Sport-specific evaluation (0-10 scale per movement)
- Per-movement score aggregation for professional report
"""

import base64
import logging
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any

import cv2
import numpy as np

from backend.analysis.evaluator import MovementEvaluator, MovementEvaluation, RecommendationEngine
from backend.utils import safe_get
from backend.analysis.sport_profiles import (
    get_sport_profile,
    get_movement_by_generic,
    get_technical_movements,
    get_coaching_feedback,
    get_coaching_feedback_with_equipment,
    get_equipment_validation_warnings,
    get_relevant_object_labels,
)
from backend.config import OUTPUT_DIR, FRAME_SKIP, POSE_SMOOTHING_ALPHA
from backend.models.movement_recognizer import MovementRecognizer
from backend.video.landmark_smoother import LandmarkSmoother
from backend.models.object_tracker import ObjectTracker
from backend.models.pose_estimator import PoseEstimator
from backend.models.sport_inferencer import infer_sport
from backend.video.overlay import VideoOverlay

logger = logging.getLogger("sport_analysis.processor")


def _score_100_to_10(score_100: float) -> float:
    """Convert 0-100 score to 0-10 scale."""
    return round(min(10.0, max(0.0, score_100 / 10.0)), 1)


class VideoProcessor:
    """Process video through full analysis pipeline with sport-specific scoring."""

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        on_stop: Optional[Callable] = None,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
        on_frame: Optional[Callable[[int, int, str, float, str], None]] = None,
    ):
        self.output_dir = output_dir or OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.on_stop = on_stop
        self.on_progress = on_progress
        self.on_frame = on_frame
        self._stop_requested = False

    def stop(self):
        """Request stop of processing."""
        self._stop_requested = True
        if self.on_stop:
            self.on_stop()

    def process_video(
        self,
        source: str,
        sport: str,
        output_path: Optional[str] = None,
        skip_overlay: bool = False,
    ) -> Dict[str, Any]:
        """
        Full pipeline: read video, pose, movement recognition, evaluate per sport.
        sport: user-selected sport (required)
        Returns summary with per-movement scores (0-10), errors, coaching feedback.
        """
        self._stop_requested = False
        sport = (sport or "unknown").lower().strip()
        use_auto_sport = sport == "auto"

        cap = cv2.VideoCapture(source)
        if not cap.isOpened():
            from backend.exceptions import VideoSourceError
            raise VideoSourceError(f"Cannot open video source: {source}", source=str(source))

        fps = cap.get(cv2.CAP_PROP_FPS) or 30
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0

        overlay_name = f"overlay_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
        out_path = (output_path or str(self.output_dir / overlay_name)) if not skip_overlay else None
        writer = None
        if not skip_overlay and out_path:
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            writer = cv2.VideoWriter(out_path, fourcc, fps, (w, h))

        pose_estimator = PoseEstimator()
        landmark_smoother = LandmarkSmoother(alpha=POSE_SMOOTHING_ALPHA)
        movement_recognizer = MovementRecognizer()
        object_tracker = ObjectTracker()
        overlay = VideoOverlay(pose_estimator)
        rec_engine = RecommendationEngine()
        evaluator = MovementEvaluator()

        # Per-movement score aggregation: movement_id -> list of frame scores (0-100)
        movement_scores: Dict[str, List[float]] = defaultdict(list)
        all_errors: List[str] = []
        all_evaluations: List[Dict] = []
        all_objects: List[Dict] = []

        frame_idx = 0
        movement = "unknown"
        inferred_sport = "unknown"
        inferred_sport_conf = 0.0
        sport_votes: Dict[str, int] = {}  # Temporal smoothing: sport votes over recent frames
        frame_errors_last_30: List[str] = []  # For error logging every 30 frames

        # For long videos (>30 sec), process every 2nd frame to reduce time
        dynamic_skip = 2 if (total_frames or 0) > 900 else FRAME_SKIP
        try:
            while cap.isOpened() and not self._stop_requested:
                ret, frame = cap.read()
                if not ret:
                    break
                if dynamic_skip > 1 and frame_idx > 0 and frame_idx % dynamic_skip != 0:
                    frame_idx += 1
                    if frame_idx % 60 == 0 and self.on_progress:
                        try:
                            self.on_progress(frame_idx, total_frames or frame_idx, "Processing")
                        except (TypeError, ValueError, RuntimeError) as e:
                            logger.debug("Progress callback failed: %s", e)
                    continue
                t0 = time.perf_counter()
                results, landmarks = None, {}

                try:
                    results, landmarks_raw = pose_estimator.process_frame(frame)
                    landmarks = landmark_smoother.smooth(landmarks_raw)
                except Exception as e:
                    frame_errors_last_30.append(f"pose:{str(e)[:50]}")
                    logger.warning("Pose estimation failed frame %d: %s", frame_idx, e)
                    landmarks = {}

                try:
                    movement, _ = movement_recognizer.recognize(landmarks)
                except Exception as e:
                    logger.debug("Movement recognition failed: %s", e)

                objs = []
                try:
                    objs = object_tracker.detect_objects(frame, frame_idx)
                except Exception as e:
                    logger.debug("Object detection failed frame %d: %s", frame_idx, e)
                obj_labels = [str(getattr(o, "label", "")) for o in objs]
                # Auto sport inference (with hysteresis: require confidence >= 0.5)
                inf_sport, inf_conf = infer_sport(movement, obj_labels)
                if inf_conf >= 0.5:
                    sport_votes[inf_sport] = sport_votes.get(inf_sport, 0) + 1
                    if sport_votes.get(inf_sport, 0) >= 3:  # Sticky: 3+ votes
                        inferred_sport = inf_sport
                        inferred_sport_conf = inf_conf
                # Effective sport and object filter (before use)
                effective_sport = sport
                if use_auto_sport:
                    effective_sport = inferred_sport if inferred_sport_conf >= 0.5 else "unknown"
                relevant_labels = get_relevant_object_labels(effective_sport)
                objs_filtered = [o for o in objs if str(getattr(o, "label", "")).lower() in {l.lower() for l in relevant_labels}] if relevant_labels else objs
                for o in objs_filtered:
                    bbox = getattr(o, "bbox", [])
                    if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
                        try:
                            bbox = [float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])]
                        except (TypeError, ValueError):
                            bbox = []
                    else:
                        bbox = []
                    all_objects.append({
                        "label": str(getattr(o, "label", "")),
                        "frame_idx": frame_idx,
                        "confidence": float(getattr(o, "confidence", 0)),
                        "bbox": bbox,
                    })

                # Map generic movement to sport-specific
                sport_movement = get_movement_by_generic(effective_sport, movement)
                if sport_movement:
                    movement_id = sport_movement.get("id", movement)
                else:
                    movement_id = movement if movement != "unknown" else "general"

                # Evaluation uses effective_sport (inferred when auto mode) + equipment for interaction metrics
                try:
                    eval_result = evaluator.evaluate_frame(
                        landmarks, frame_idx, effective_sport, movement=movement, objects=objs_filtered
                    )
                    score_100 = eval_result.overall_score
                    movement_scores[movement_id].append(score_100)
                    all_errors.extend(eval_result.errors or [])
                    joint_dicts = [
                        {
                            "name": str(j.name),
                            "score": float(j.score),
                            "is_correct": bool(j.is_correct),
                            "feedback": str(j.feedback),
                        }
                        for j in (eval_result.joint_scores or [])
                    ]
                    all_evaluations.append({
                        "frame_idx": frame_idx,
                        "overall_score": score_100,
                        "movement": movement_id,
                        "errors": list(eval_result.errors or []),
                        "joint_scores": joint_dicts,
                    })
                    eval_result_for_overlay = eval_result
                except Exception as e:
                    logger.warning("Evaluation failed frame %d: %s", frame_idx, e)
                    all_evaluations.append({
                        "frame_idx": frame_idx,
                        "overall_score": 0.0,
                        "movement": movement_id,
                        "errors": ["Evaluation failed"],
                        "joint_scores": [],
                    })
                    eval_result_for_overlay = MovementEvaluation(
                        frame_idx=frame_idx, overall_score=0.0, is_correct=False,
                        errors=["Evaluation failed"], sport=sport, movement=movement
                    )
                    frame_errors_last_30.append("evaluation:failed")

                rec_names = []
                try:
                    recs = rec_engine.get_recommendations(
                        eval_result_for_overlay.errors or [],
                        eval_result_for_overlay.joint_scores or [],
                        sport,
                    )
                    rec_names = [r.name for r in recs]
                except (AttributeError, TypeError, KeyError) as e:
                    logger.debug("Recommendations failed frame %d: %s", frame_idx, e)

                frame_out = frame
                if writer and not skip_overlay:
                    try:
                        frame_out = overlay.draw_overlay(
                            frame,
                            sport=effective_sport,
                            movement=movement_id,
                            score=eval_result_for_overlay.overall_score,
                            errors=eval_result_for_overlay.errors or [],
                            recommendations=rec_names,
                            objects=objs_filtered,
                            frame_idx=frame_idx,
                            processing_time_ms=(time.perf_counter() - t0) * 1000,
                            draw_skeleton=True,
                            results=results,
                            total_frames=total_frames or 0,
                        )
                        writer.write(frame_out)
                    except (cv2.error, TypeError, ValueError) as e:
                        logger.warning("Overlay draw failed frame %d: %s", frame_idx, e)
                        writer.write(frame)

                if self.on_frame and not skip_overlay:
                    try:
                        _, jpeg = cv2.imencode(".jpg", frame_out)
                        if jpeg is not None:
                            errs = eval_result_for_overlay.errors or []
                            strengths = [
                                f"{safe_get(j, 'name', '').replace('_', ' ').title()} alignment"
                                for j in (eval_result_for_overlay.joint_scores or [])
                                if safe_get(j, "score", 0) >= 80
                            ]
                            obj_labels = [getattr(o, "label", "") for o in objs_filtered][:5]
                            fb = ""
                            if errs:
                                obj_labels_str = [getattr(o, "label", "") for o in objs_filtered]
                                fb = get_coaching_feedback_with_equipment(effective_sport, errs[0], obj_labels_str)
                            elif eval_result_for_overlay.overall_score < 70:
                                fb = "Focus on form and alignment"
                            else:
                                fb = "Good form"
                            self.on_frame(
                                frame_idx,
                                total_frames or (frame_idx + 1),
                                effective_sport,
                                _score_100_to_10(eval_result_for_overlay.overall_score),
                                base64.b64encode(jpeg.tobytes()).decode("ascii"),
                                movement_id,
                                errors=errs,
                                feedback=fb,
                                strengths=strengths,
                                objects=obj_labels,
                            )
                    except (TypeError, ValueError, RuntimeError, OSError) as e:
                        logger.debug("Frame callback failed frame %d: %s", frame_idx, e)

                frame_idx += 1
                if frame_idx % 30 == 0:
                    logger.info("Processed %d frames", frame_idx)
                    if frame_errors_last_30:
                        logger.warning(
                            "Frame errors in last 30 frames (at %d): %s",
                            frame_idx,
                            ", ".join(frame_errors_last_30[-10:]),
                        )
                        frame_errors_last_30.clear()
                    if self.on_progress:
                        try:
                            self.on_progress(frame_idx, total_frames or frame_idx, "Processing")
                        except (TypeError, ValueError, RuntimeError) as e:
                            logger.debug("Progress callback failed: %s", e)

        finally:
            cap.release()
            if writer:
                writer.release()
            pose_estimator.close()

        # Final sport for report: inferred when auto, else user-selected
        final_sport = inferred_sport if (use_auto_sport and inferred_sport_conf >= 0.5) else sport
        if final_sport == "auto":
            final_sport = inferred_sport if inferred_sport_conf >= 0.5 else "unknown"

        # Build per-movement summary (0-10 scale)
        movements_analyzed: List[Dict] = []
        for mov in get_technical_movements(final_sport):
            mov_id = mov.get("id", "")
            scores = movement_scores.get(mov_id, [])
            if not scores and mov.get("generic"):
                # Check generic key
                for k, v in movement_scores.items():
                    if k == mov.get("generic"):
                        scores = v
                        break
            if scores:
                avg_100 = float(np.mean(scores))
                score_10 = _score_100_to_10(avg_100)
                strengths_mov = ["Good form", "Solid technique"] if score_10 >= 7 else []
                weaknesses_mov = [] if score_10 >= 7 else ["Needs technique refinement"]
                movements_analyzed.append({
                    "id": mov_id,
                    "name_en": mov.get("name_en", mov_id),
                    "name": mov.get("name_en", mov_id),
                    "score": score_10,
                    "frames_count": len(scores),
                    "feedback": "Good form - continue practice" if score_10 >= 7 else "Focus on improvement - see recommendations",
                    "strengths": strengths_mov,
                    "weaknesses": weaknesses_mov,
                    "improvement_note": "" if score_10 >= 7 else "Practice slow, controlled repetitions with focus on joint alignment.",
                })
        # Add any detected movements not in technical list
        for mov_id, scores in movement_scores.items():
            if not any(m["id"] == mov_id for m in movements_analyzed):
                avg_100 = float(np.mean(scores))
                score_10 = _score_100_to_10(avg_100)
                movements_analyzed.append({
                    "id": mov_id,
                    "name_en": mov_id.replace("_", " ").title(),
                    "name": mov_id.replace("_", " ").title(),
                    "score": score_10,
                    "frames_count": len(scores),
                    "feedback": "Detected movement" if score_10 >= 5 else "Needs improvement",
                    "strengths": [],
                    "weaknesses": [],
                    "improvement_note": "",
                })

        unique_errors = list(dict.fromkeys(all_errors))[:10]
        object_labels_seen = list(dict.fromkeys(o.get("label", "") for o in all_objects if o.get("label")))
        equipment_warnings = get_equipment_validation_warnings(final_sport, object_labels_seen)
        unique_errors = equipment_warnings + unique_errors
        joint_scores_agg = all_evaluations[-1].get("joint_scores", []) if all_evaluations else []
        avg_score = (
            sum(e["overall_score"] for e in all_evaluations) / len(all_evaluations)
            if all_evaluations else 0
        )
        strengths_observed = [
            safe_get(j, "name", "").replace("_", " ").title() + " alignment"
            for j in (joint_scores_agg or [])
            if safe_get(j, "score", 0) >= 80
        ]
        if not strengths_observed:
            strengths_observed = ["Overall form" if avg_score >= 70 else "Stable posture"]
        final_recs = rec_engine.get_recommendations(
            unique_errors, joint_scores_agg, final_sport
        )
        development_plan = rec_engine.get_development_plan(final_sport, avg_score, unique_errors)

        # Coaching feedback for each error (equipment-aware when objects detected)
        coaching_feedback = []
        for err in unique_errors:
            if "expected" in err.lower() and "not detected" in err.lower():
                coaching_feedback.append({"error": err, "feedback": err})
                continue
            err_lower = err.lower()
            tip = None
            for key in get_sport_profile(final_sport).get("coaching_tips", {}):
                if key in err_lower or err_lower in key:
                    tip = get_coaching_feedback_with_equipment(final_sport, key, object_labels_seen)
                    break
            if not tip:
                tip = get_coaching_feedback_with_equipment(final_sport, err, object_labels_seen)
            coaching_feedback.append({"error": err, "feedback": tip})

        sport_profile = get_sport_profile(final_sport)

        # Inferred sport from movement+objects (for UI hint)
        final_inferred = inferred_sport if inferred_sport_conf >= 0.5 else None
        summary = {
            "sport": final_sport,
            "sport_name": sport_profile.get("name_en", sport_profile.get("name", final_sport)),
            "sport_name_en": sport_profile.get("name_en", final_sport),
            "sport_was_auto": use_auto_sport,
            "inferred_sport": final_inferred,
            "inferred_sport_confidence": round(inferred_sport_conf, 2) if final_inferred else None,
            "movements_analyzed": movements_analyzed,
            "overall_score": _score_100_to_10(avg_score),
            "overall_score_100": round(avg_score, 1),
            "total_frames": frame_idx,
            "video_width": w,
            "video_height": h,
            "video_fps": fps,
            "errors": unique_errors,
            "strengths": strengths_observed[:8],
            "coaching_feedback": coaching_feedback,
            "recommendations": [
                {
                    "name": str(r.name),
                    "description": str(r.description),
                    "target_joint": str(r.target_joint),
                    "reps_sets": str(r.reps_sets),
                    "sport_focus": str(getattr(r, "sport_focus", "")),
                }
                for r in final_recs
            ],
            "joint_scores": [
                {**js, "score": round(min(10.0, max(0.0, safe_get(js, "score", 0) / 10.0)), 1)}
                for js in (joint_scores_agg or [])
            ],
            "object_tracking": all_objects[:50],
            "development_plan": development_plan,
            "frame_evaluations": all_evaluations,
            "output_video_path": out_path,
            "output_filename": Path(out_path).name if out_path else None,
        }
        return summary
