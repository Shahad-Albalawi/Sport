"""
Video preprocessing for efficient analysis.

- Resize to 720p (or lower) for faster processing
- Frame skipping (analyze every 2-3 frames)
- Crop to athlete + equipment region
- Camera stabilization
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, Tuple

import cv2
import numpy as np

from backend.video.landmark_smoother import stabilize_frame

logger = logging.getLogger("sport_analysis.preprocessor")

# Default target height (720p)
TARGET_HEIGHT = 720
TARGET_WIDTH = 1280  # 16:9 at 720p
# Minimum dimension for crop (avoid too small)
MIN_CROP_DIM = 320
# Padding around detected region
CROP_PADDING = 0.15  # 15% padding


@dataclass
class PreprocessOptions:
    """Options for video preprocessing."""

    target_height: int = TARGET_HEIGHT
    target_width: int = TARGET_WIDTH
    frame_skip: int = 2  # Analyze every Nth frame (1=all, 2=every 2nd, 3=every 3rd)
    enable_stabilization: bool = True
    enable_crop: bool = False  # Crops to pose bbox when landmarks available
    min_crop_dim: int = MIN_CROP_DIM
    crop_padding: float = CROP_PADDING


def resize_frame(
    frame: np.ndarray,
    target_height: int = TARGET_HEIGHT,
    target_width: Optional[int] = None,
) -> np.ndarray:
    """
    Resize frame to target dimensions. Maintains aspect ratio if target_width is None.
    Downscales only (never upscales) for speed.
    """
    h, w = frame.shape[:2]
    if target_height <= 0 or h <= 0 or w <= 0:
        return frame
    if target_width is None:
        if h <= target_height:
            return frame
        scale = target_height / h
        target_width = int(w * scale)
    if h <= target_height and w <= (target_width or w):
        return frame
    scale_h = target_height / h
    scale_w = (target_width or w) / w
    scale = min(scale_h, scale_w, 1.0)  # Never upscale
    if scale >= 1.0:
        return frame
    new_w = max(1, int(w * scale))
    new_h = max(1, int(h * scale))
    if new_w <= 0 or new_h <= 0:
        return frame
    return cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)


def crop_to_region(
    frame: np.ndarray,
    landmarks: Optional[dict] = None,
    bbox: Optional[Tuple[float, float, float, float]] = None,
    padding: float = CROP_PADDING,
    min_dim: int = MIN_CROP_DIM,
) -> np.ndarray:
    """
    Crop frame to region containing athlete/equipment.
    landmarks: dict of name -> (x, y, z) normalized 0-1
    bbox: (x, y, w, h) normalized 0-1
    Returns cropped frame.
    """
    h, w = frame.shape[:2]
    if landmarks:
        xs = [v[0] for v in landmarks.values() if isinstance(v, (tuple, list)) and len(v) >= 2]
        ys = [v[1] for v in landmarks.values() if isinstance(v, (tuple, list)) and len(v) >= 2]
        if not xs or not ys:
            return frame
        x_min, x_max = min(xs), max(xs)
        y_min, y_max = min(ys), max(ys)
    elif bbox:
        x_min, y_min, bw, bh = bbox
        x_max = x_min + bw
        y_max = y_min + bh
    else:
        return frame

    pad_w = (x_max - x_min) * padding
    pad_h = (y_max - y_min) * padding
    x_min = max(0, x_min - pad_w)
    x_max = min(1, x_max + pad_w)
    y_min = max(0, y_min - pad_h)
    y_max = min(1, y_max + pad_h)

    x1 = int(x_min * w)
    x2 = int(x_max * w)
    y1 = int(y_min * h)
    y2 = int(y_max * h)

    cw = x2 - x1
    ch = y2 - y1
    if cw < min_dim or ch < min_dim:
        return frame

    return frame[y1:y2, x1:x2].copy()


class VideoPreprocessor:
    """
    Preprocess video frames for efficient analysis.
    Resize, stabilize, optional crop. Tracks frame skip.
    """

    def __init__(self, options: Optional[PreprocessOptions] = None):
        self.opts = options or PreprocessOptions()
        self._prev_gray: Optional[np.ndarray] = None
        self._prev_pts: Optional[np.ndarray] = None
        self._frame_count = 0

    def reset(self) -> None:
        """Reset state for new video."""
        self._prev_gray = None
        self._prev_pts = None
        self._frame_count = 0

    def should_process_frame(self, frame_idx: int) -> bool:
        """Return True if this frame should be processed (frame skip logic)."""
        skip = self.opts.frame_skip
        if skip <= 1:
            return True
        return frame_idx % skip == 0

    def process(
        self,
        frame: np.ndarray,
        frame_idx: int = 0,
        landmarks: Optional[dict] = None,
    ) -> np.ndarray:
        """
        Preprocess a single frame: resize, stabilize, optional crop.
        Returns processed frame ready for pose estimation.
        """
        self._frame_count += 1
        out = frame

        if self.opts.enable_stabilization:
            out, self._prev_gray, self._prev_pts = stabilize_frame(
                out, self._prev_gray, self._prev_pts
            )

        out = resize_frame(
            out,
            target_height=self.opts.target_height,
            target_width=self.opts.target_width,
        )

        if self.opts.enable_crop and landmarks:
            out = crop_to_region(
                out,
                landmarks=landmarks,
                padding=self.opts.crop_padding,
                min_dim=self.opts.min_crop_dim,
            )

        return out
