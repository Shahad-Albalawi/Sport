"""Pytest configuration and shared fixtures."""

import sys
from pathlib import Path

# Ensure project root in path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _create_test_video(tmp_path: Path, frames: int = 30) -> str:
    """Create minimal synthetic video for integration tests."""
    import cv2
    import numpy as np
    w, h, fps = 320, 240, 10
    path = tmp_path / "test_video.mp4"
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, fps, (w, h))
    for i in range(frames):
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        frame[:] = (i % 50, 100, 150)  # Slight variation per frame
        writer.write(frame)
    writer.release()
    return str(path)
