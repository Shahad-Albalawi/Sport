"""Overlay analysis results on video frames.

Draws skeleton, landmarks, joint angles, sport, score, errors, and recommendations.
"""

import logging
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from backend.models.pose_estimator import PoseEstimator
from backend.models.object_tracker import TrackedObject

logger = logging.getLogger("sport_analysis.overlay")

# Overlay layout constants (pixels)
PANEL_HEIGHT_MAX = 200
PANEL_WIDTH_MAX = 380
PROGRESS_BAR_HEIGHT = 6
PROGRESS_BAR_MARGIN = 25
PROGRESS_BAR_PADDING = 10
MAX_ERR_TEXT_LEN = 60
MAX_REC_TEXT_LEN = 50


def _angle_deg(
    p1: Tuple[float, float],
    p2: Tuple[float, float],
    p3: Tuple[float, float],
    w: int,
    h: int,
) -> Optional[float]:
    """Compute angle at p2 (vertex) in degrees. Points normalized 0-1."""
    pt1 = (p1[0] * w, p1[1] * h)
    pt2 = (p2[0] * w, p2[1] * h)
    pt3 = (p3[0] * w, p3[1] * h)
    v1 = (pt1[0] - pt2[0], pt1[1] - pt2[1])
    v2 = (pt3[0] - pt2[0], pt3[1] - pt2[1])
    dot = v1[0] * v2[0] + v1[1] * v2[1]
    mag1 = (v1[0]**2 + v1[1]**2) ** 0.5 or 1e-6
    mag2 = (v2[0]**2 + v2[1]**2) ** 0.5 or 1e-6
    cos_a = max(-1, min(1, dot / (mag1 * mag2)))
    return np.degrees(np.arccos(cos_a))


class VideoOverlay:
    """Draw analysis results on video frames."""

    LANDMARK_NAMES = [
        "nose", "left_eye_inner", "left_eye", "left_eye_outer",
        "right_eye_inner", "right_eye", "right_eye_outer",
        "left_ear", "right_ear", "mouth_left", "mouth_right",
        "left_shoulder", "right_shoulder", "left_elbow", "right_elbow",
        "left_wrist", "right_wrist", "left_pinky", "right_pinky",
        "left_index", "right_index", "left_thumb", "right_thumb",
        "left_hip", "right_hip", "left_knee", "right_knee",
        "left_ankle", "right_ankle", "left_heel", "right_heel",
        "left_foot_index", "right_foot_index",
    ]

    def __init__(self, pose_estimator: PoseEstimator):
        self.pose_estimator = pose_estimator

    def _extract_joint_angles(self, results, w: int, h: int) -> List[Tuple[str, float, Tuple[int, int]]]:
        """Extract key joint angles and their draw positions."""
        angles = []
        if not results or not results.pose_landmarks or len(results.pose_landmarks) == 0:
            return angles
        lm = results.pose_landmarks[0]
        names = self.LANDMARK_NAMES

        def get(i):
            if i < len(lm):
                return (lm[i].x, lm[i].y)
            return None

        checks = [
            ("L-Knee", 23, 25, 27, "left_hip", "left_knee", "left_ankle"),
            ("R-Knee", 24, 26, 28, "right_hip", "right_knee", "right_ankle"),
            ("L-Elb", 11, 13, 15, "left_shoulder", "left_elbow", "left_wrist"),
            ("R-Elb", 12, 14, 16, "right_shoulder", "right_elbow", "right_wrist"),
        ]
        for label, i1, i2, i3, _, _, _ in checks:
            p1, p2, p3 = get(i1), get(i2), get(i3)
            if p1 and p2 and p3:
                a = _angle_deg(p1, p2, p3, w, h)
                if a is not None:
                    px = int(p2[0] * w)
                    py = int(p2[1] * h)
                    angles.append((label, a, (px, py)))
        return angles

    def draw_overlay(
        self,
        frame: np.ndarray,
        sport: str,
        score: float,
        errors: List[str],
        recommendations: List[str],
        objects: List[TrackedObject],
        frame_idx: int,
        processing_time_ms: float,
        movement: str = "",
        draw_skeleton: bool = True,
        results: Optional[object] = None,
        total_frames: int = 0,
    ) -> np.ndarray:
        """Draw all overlay elements: skeleton, landmarks, joint angles, progress bar."""
        h, w = frame.shape[:2]
        overlay = frame.copy()

        panel_h = min(PANEL_HEIGHT_MAX, h // 3)
        cv2.rectangle(overlay, (0, 0), (min(PANEL_WIDTH_MAX, w), panel_h), (30, 30, 30), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, overlay)

        cv2.putText(overlay, f"Sport: {sport}", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 200), 2)
        if movement and movement != "unknown":
            cv2.putText(overlay, f"Movement: {movement}", (10, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 255, 150), 1)
        cv2.putText(overlay, f"Score: {score/10:.1f}/10", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 200), 2)
        cv2.putText(overlay, f"Frame: {frame_idx}", (10, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.putText(overlay, f"Time: {processing_time_ms:.0f}ms", (10, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        if errors:
            err_text = "; ".join(errors[:2])[:MAX_ERR_TEXT_LEN]
            cv2.putText(overlay, f"Errors: {err_text}", (10, 135), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 100, 255), 1)
        if recommendations:
            rec_text = (recommendations[0] if recommendations else "")[:MAX_REC_TEXT_LEN]
            cv2.putText(overlay, f"Tip: {rec_text}", (10, 155), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 255, 100), 1)

        # Playback timeline / progress bar at bottom
        if total_frames > 0:
            bar_h = PROGRESS_BAR_HEIGHT
            bar_y = h - bar_h - PROGRESS_BAR_MARGIN
            bar_w = w - PROGRESS_BAR_PADDING * 2
            bar_x = PROGRESS_BAR_PADDING
            pct = min(1.0, max(0.0, frame_idx / total_frames))
            cv2.rectangle(overlay, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (80, 80, 80), -1)
            cv2.rectangle(overlay, (bar_x, bar_y), (bar_x + int(bar_w * pct), bar_y + bar_h), (0, 200, 100), -1)

        cv2.putText(overlay, f"#{frame_idx}", (w - 80, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        if draw_skeleton and results:
            self.pose_estimator.draw_landmarks(overlay, results)

            for label, angle, (px, py) in self._extract_joint_angles(results, w, h):
                if 0 <= py < h and 0 <= px < w:
                    cv2.putText(overlay, f"{angle:.0f}", (px + 5, py), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)

        for obj in objects[:5]:
            try:
                bbox = getattr(obj, "bbox", None) or []
                if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
                    x, y, bw, bh = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
                    px = int(x * w)
                    py = int(y * h)
                    pw = max(10, int(bw * w))
                    ph = max(10, int(bh * h))
                    cv2.rectangle(overlay, (px, py), (px + pw, py + ph), (255, 200, 0), 2)
                    label = getattr(obj, "label", "obj")[:12]
                    cv2.putText(overlay, label, (px, py - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 200, 0), 1)
            except (ValueError, TypeError, IndexError):
                pass

        return overlay
