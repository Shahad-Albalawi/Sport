"""
Hybrid pose estimation: Lite for fast scan, Heavy only on key frames.

- Lite: runs on every processed frame for key-movement detection
- Heavy: runs only on Landing, Jump, Strike, Throw frames for high accuracy
"""

import logging
from typing import Dict, Optional, Tuple

import numpy as np

from backend.models.pose_estimator import PoseEstimator, LANDMARK_NAMES, POSE_CONNECTIONS

logger = logging.getLogger("sport_analysis.hybrid_pose")


class HybridPoseEstimator:
    """
    Lite for scanning + Heavy only on key frames.
    API compatible with PoseEstimator for overlay and evaluation.
    """

    def __init__(self):
        self._lite = PoseEstimator(model_variant="lite")
        self._heavy: Optional[PoseEstimator] = None  # Lazy load
        self._frame_timestamp_ms = 0
        self._last_result = None  # For overlay compatibility

    @property
    def landmarker(self):
        """For overlay draw_landmarks compatibility - use heavy if loaded, else lite."""
        return self._heavy.landmarker if self._heavy else self._lite.landmarker

    def _get_heavy(self) -> PoseEstimator:
        if self._heavy is None:
            logger.info("Loading Heavy pose model for key-frame refinement")
            self._heavy = PoseEstimator(model_variant="heavy")
        return self._heavy

    def process_frame(
        self,
        frame: np.ndarray,
        is_key_frame: bool = False,
        timestamp_ms: Optional[int] = None,
    ) -> Tuple[Optional[object], Dict[str, Tuple[float, float, float]]]:
        """
        Process frame: Lite on all, Heavy only when is_key_frame=True.
        Returns (result, landmarks). Uses Heavy landmarks for key frames.
        """
        ts = timestamp_ms if timestamp_ms is not None else self._frame_timestamp_ms
        self._frame_timestamp_ms = ts + 33  # Advance for next frame

        # Always run Lite for key-frame detection (or lightweight eval)
        result, landmarks = self._lite.process_frame(frame, timestamp_ms=ts)

        if is_key_frame and landmarks:
            # Refine with Heavy for higher accuracy
            try:
                heavy = self._get_heavy()
                result, landmarks = heavy.process_frame(frame, timestamp_ms=ts)
                self._last_result = result
                return result, landmarks
            except Exception as e:
                logger.warning("Heavy pose failed on key frame, using Lite: %s", e)

        self._last_result = result
        self._last_ts = ts  # For upgrade_to_heavy same-frame
        return result, landmarks

    def upgrade_to_heavy(
        self, frame: np.ndarray
    ) -> Tuple[Optional[object], Dict[str, Tuple[float, float, float]]]:
        """
        Re-run pose with Heavy model on the same frame (for key-frame refinement).
        Uses the timestamp from the last process_frame call.
        """
        if not hasattr(self, "_last_ts"):
            return self._lite.process_frame(frame)
        try:
            heavy = self._get_heavy()
            result, landmarks = heavy.process_frame(frame, timestamp_ms=self._last_ts)
            self._last_result = result
            return result, landmarks
        except Exception as e:
            logger.warning("Heavy pose failed: %s", e)
            return self._last_result, self._last_landmarks_from_lite(frame)

    def _last_landmarks_from_lite(self, frame):
        """Fallback: re-run Lite to get landmarks."""
        r, lm = self._lite.process_frame(frame, timestamp_ms=getattr(self, "_last_ts", 0))
        return lm

    def draw_landmarks(self, frame, results, draw_connections=True):
        """Delegate to Lite (same skeleton structure)."""
        return self._lite.draw_landmarks(frame, results, draw_connections)

    def close(self):
        self._lite.close()
        if self._heavy:
            self._heavy.close()
            self._heavy = None
