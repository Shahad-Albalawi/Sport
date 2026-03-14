"""
Sport-specific batch video processor for training data collection.

Processes only videos relevant to the sport. Applies preprocessing:
- Camera stabilization (optional)
- Temporal smoothing (One Euro Filter)
- Pose landmark tracking

Extracts and stores: joint angles, symmetry, CoM, stability, angular velocity.
"""

import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from backend.analysis.sport_profiles import get_technical_movements
from backend.sport_registry import get_sport_videos_dir
from backend.training.data_store import TrainingDataStore
from backend.video.processor import VideoProcessor

logger = logging.getLogger("sport_analysis.training")


class SportBatchProcessor:
    """
    Process video batches for a single sport. Collects training data only.
    No data from other sports is mixed.
    """

    def __init__(
        self,
        sport_id: str,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
        skip_overlay: bool = True,
    ):
        self.sport_id = (sport_id or "unknown").lower().strip()
        self.on_progress = on_progress
        self.skip_overlay = skip_overlay
        self._store = TrainingDataStore(self.sport_id)

    def _get_videos(self, video_paths: Optional[List[str]] = None) -> List[Path]:
        """Get video paths: explicit list or from sport videos dir."""
        if video_paths:
            return [Path(p) for p in video_paths if Path(p).exists()]
        videos_dir = get_sport_videos_dir(self.sport_id)
        out: List[Path] = []
        for ext in ("*.mp4", "*.avi", "*.mov", "*.mkv"):
            out.extend(sorted(videos_dir.glob(ext)))
        return out

    def process_batch(
        self,
        video_paths: Optional[List[str]] = None,
        run_improvement: bool = True,
    ) -> Dict[str, Any]:
        """
        Process all videos for this sport. Collect training data and optionally run improvement.

        Returns summary with videos_processed, movement_stats, error_counts, improvements_applied.
        """
        videos = self._get_videos(video_paths)
        if not videos:
            logger.warning("No videos found for sport %s", self.sport_id)
            return {
                "sport_id": self.sport_id,
                "videos_processed": 0,
                "videos_found": 0,
                "movement_stats": {},
                "error_counts": {},
                "improvements_applied": None,
            }

        processor = VideoProcessor(on_progress=self.on_progress)
        total_videos = len(videos)
        all_errors: List[str] = []

        for i, vpath in enumerate(videos):
            if self.on_progress:
                try:
                    self.on_progress(i, total_videos, f"Processing {vpath.name}")
                except Exception:
                    pass
            try:
                summary = processor.process_video(str(vpath), sport=self.sport_id, skip_overlay=self.skip_overlay)
                self._ingest_summary(summary, str(vpath))
                all_errors.extend(summary.get("errors", []))
            except Exception as e:
                logger.warning("Failed to process %s: %s", vpath, e)

        improvements = None
        if run_improvement and (self._store.data.get("videos_processed", 0) > 0):
            from backend.training.improvement import ImprovementEngine
            engine = ImprovementEngine(self.sport_id)
            improvements = engine.run_and_apply()

        return {
            "sport_id": self.sport_id,
            "videos_processed": total_videos,
            "videos_found": len(videos),
            "movement_stats": self._store.get_movement_stats(),
            "error_counts": self._store.get_error_counts(),
            "improvements_applied": improvements,
        }

    def _ingest_summary(self, summary: Dict[str, Any], video_path: str) -> None:
        """Convert pipeline summary to training records and store."""
        frame_evals = summary.get("frame_evaluations", [])
        total_frames = len(frame_evals)

        movement_scores: Dict[str, List[float]] = defaultdict(list)
        movement_injury: Dict[str, List[float]] = defaultdict(list)
        movement_errors: Dict[str, List[str]] = defaultdict(list)
        frame_samples: List[Dict[str, Any]] = []

        for ev in frame_evals:
            mov = ev.get("movement", "unknown")
            movement_scores[mov].append(ev.get("overall_score", 0) / 10.0)
            movement_injury[mov].append(ev.get("injury_risk_score", 0))
            movement_errors[mov].extend(ev.get("errors", []) or [])

            ft = ev.get("features_for_training", {})
            if ft:
                angles = {}
                for k, v in ft.items():
                    if "angles" in k and isinstance(v, dict):
                        angles.update(v)
                if angles:
                    frame_samples.append({"angles": angles, "movement": mov})

        movement_summaries = []
        for mov_id, scores in movement_scores.items():
            if not scores:
                continue
            injury_list = movement_injury.get(mov_id, [])
            movement_summaries.append({
                "id": mov_id,
                "score": sum(scores) / len(scores),
                "avg_score": sum(scores) / len(scores),
                "injury_risk_score": sum(injury_list) / len(injury_list) if injury_list else 0,
                "frames_count": len(scores),
                "errors": movement_errors.get(mov_id, []),
            })

        error_list = list(summary.get("errors", []))
        self._store.add_video_result(
            video_path=video_path,
            total_frames=total_frames,
            movement_summaries=movement_summaries,
            frame_samples=frame_samples,
            error_list=error_list,
        )
