"""Download the MediaPipe pose landmarker model (runs automatically on first analysis).

Run this script to pre-download the model (~3MB) so the first analysis is faster.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from backend.models.pose_estimator import _ensure_model

if __name__ == "__main__":
    path = _ensure_model()
    print(f"Model ready: {path}")
