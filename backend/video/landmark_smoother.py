"""Temporal smoothing for pose landmarks to reduce jitter.

Supports EMA and One Euro Filter. Optional camera stabilization.
"""

import logging
from typing import Dict, Optional, Tuple

import cv2
import numpy as np

from backend.config import POSE_SMOOTHING_ALPHA

logger = logging.getLogger("sport_analysis.smoother")


class OneEuroFilter:
    """One Euro Filter for low-latency smoothing with adaptive cutoff."""

    def __init__(self, min_cutoff: float = 1.0, beta: float = 0.007, d_cutoff: float = 1.0):
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self._x_prev: Optional[float] = None
        self._dx_prev: float = 0.0
        self._t_prev: float = 0.0

    def _alpha(self, dt: float, cutoff: float) -> float:
        tau = 1.0 / (2 * np.pi * cutoff) if cutoff > 0 else 1.0
        return 1.0 / (1.0 + tau / dt) if dt > 0 else 1.0

    def __call__(self, x: float, t: float) -> float:
        if self._x_prev is None:
            self._x_prev = x
            self._dx_prev = 0.0
            self._t_prev = t
            return x
        dt = max(1e-6, t - self._t_prev)
        dx = (x - self._x_prev) / dt
        ed_val = dx * self._alpha(dt, self.d_cutoff) + (1 - self._alpha(dt, self.d_cutoff)) * self._dx_prev
        cutoff = self.min_cutoff + self.beta * abs(ed_val)
        x_filt = self._alpha(dt, cutoff) * x + (1 - self._alpha(dt, cutoff)) * self._x_prev
        self._x_prev = x_filt
        self._dx_prev = ed_val
        self._t_prev = t
        return x_filt

    def reset(self):
        self._x_prev = None
        self._dx_prev = 0.0


class LandmarkSmoother:
    """Smooth pose landmarks across frames. Supports EMA or One Euro Filter."""

    def __init__(self, alpha: Optional[float] = None, use_one_euro: bool = True):
        """
        alpha: smoothing factor (0-1) for EMA. Lower = smoother but more lag.
        use_one_euro: if True, use One Euro Filter (less lag, better for motion).
        Default from config POSE_SMOOTHING_ALPHA when alpha is None.
        """
        self.alpha = float(alpha if alpha is not None else POSE_SMOOTHING_ALPHA)
        self.use_one_euro = use_one_euro
        self._prev: Dict[str, Tuple[float, float, float]] = {}
        self._filters: Dict[str, Tuple[OneEuroFilter, OneEuroFilter, OneEuroFilter]] = {}
        self._frame_time: float = 0.0

    def smooth(
        self, landmarks: Dict[str, Tuple[float, float, float]]
    ) -> Dict[str, Tuple[float, float, float]]:
        """
        Apply temporal smoothing. First frame returns as-is; later frames smoothed.
        Returns new landmarks dict (does not modify input).
        """
        if not landmarks:
            return {}
        self._frame_time += 1.0
        out = {}
        for name, pt in landmarks.items():
            x, y, z = float(pt[0]), float(pt[1]), float(pt[2])
            if self.use_one_euro:
                if name not in self._filters:
                    self._filters[name] = (
                        OneEuroFilter(min_cutoff=1.0, beta=0.007),
                        OneEuroFilter(min_cutoff=1.0, beta=0.007),
                        OneEuroFilter(min_cutoff=1.0, beta=0.007),
                    )
                fx, fy, fz = self._filters[name]
                x = fx(x, self._frame_time)
                y = fy(y, self._frame_time)
                z = fz(z, self._frame_time)
            elif name in self._prev:
                px, py, pz = self._prev[name]
                x = self.alpha * x + (1 - self.alpha) * px
                y = self.alpha * y + (1 - self.alpha) * py
                z = self.alpha * z + (1 - self.alpha) * pz
            self._prev[name] = (x, y, z)
            out[name] = (x, y, z)
        return out

    def reset(self):
        """Reset state for new video."""
        self._prev.clear()
        self._filters.clear()
        self._frame_time = 0.0


def stabilize_frame(frame: np.ndarray, prev_gray: Optional[np.ndarray], prev_pts: Optional[np.ndarray]) -> Tuple[np.ndarray, Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Lightweight camera stabilization via optical flow.
    Returns (stabilized_frame, gray_for_next, pts_for_next).
    If prev_gray/prev_pts is None, returns (frame, gray, feature_pts) for first frame.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if prev_gray is None or prev_pts is None:
        pts = cv2.goodFeaturesToTrack(gray, maxCorners=200, qualityLevel=0.01, minDistance=10)
        return frame, gray, pts
    pts = cv2.goodFeaturesToTrack(gray, maxCorners=200, qualityLevel=0.01, minDistance=10)
    if pts is None or len(pts) < 4:
        return frame, gray, pts
    # Optical flow
    next_pts, status, _ = cv2.calcOpticalFlowPyrLK(prev_gray, gray, prev_pts, None)
    if next_pts is None or status is None:
        return frame, gray, pts
    mask = status.ravel() == 1
    if mask.sum() < 4:
        return frame, gray, pts
    src = prev_pts[mask].astype(np.float32)
    dst = next_pts[mask].astype(np.float32)
    M, _ = cv2.estimateAffinePartial2D(src, dst)
    if M is None:
        return frame, gray, pts
    h, w = frame.shape[:2]
    stabilized = cv2.warpAffine(frame, M, (w, h), borderMode=cv2.BORDER_REPLICATE)
    return stabilized, gray, pts
