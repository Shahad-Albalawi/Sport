"""Temporal smoothing for pose landmarks to reduce jitter.

Uses exponential moving average (EMA) for stable landmark positions.
"""

import logging
from typing import Dict, Optional, Tuple

import numpy as np

from backend.config import POSE_SMOOTHING_ALPHA

logger = logging.getLogger("sport_analysis.smoother")


class LandmarkSmoother:
    """Smooth pose landmarks across frames using EMA."""

    def __init__(self, alpha: float = 0.5):
        """
        alpha: smoothing factor (0-1). Lower = smoother but more lag.
        Default from config POSE_SMOOTHING_ALPHA.
        """
        self.alpha = float(alpha)
        self._prev: Dict[str, Tuple[float, float, float]] = {}

    def smooth(
        self, landmarks: Dict[str, Tuple[float, float, float]]
    ) -> Dict[str, Tuple[float, float, float]]:
        """
        Apply EMA smoothing. First frame returns as-is; later frames smoothed.
        Returns new landmarks dict (does not modify input).
        """
        if not landmarks:
            return {}
        out = {}
        for name, pt in landmarks.items():
            x, y, z = float(pt[0]), float(pt[1]), float(pt[2])
            if name in self._prev:
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
