"""Configuration and constants.

All magic numbers and tunables are centralized here for maintainability.
"""

import logging
import sys
from pathlib import Path
from typing import List, Optional

# Version (semantic versioning)
VERSION = "1.0.0"

# Paths (centralized)
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
REPORTS_DIR = BASE_DIR / "reports"
FRONTEND_DIR = BASE_DIR / "frontend"

# Performance
MAX_STREAM_FRAMES = 500  # Limit frames buffered for SSE
FRAME_SKIP = 1  # 1=all frames, 2=every 2nd, etc.
ANALYSIS_TIMEOUT_SEC = 3600  # 1 hour max per video

# Job cleanup
JOB_EXPIRY_MINUTES = 60

# Ensure directories exist
for d in (UPLOADS_DIR, OUTPUT_DIR, REPORTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

# MediaPipe pose settings
# "heavy" = more accurate body tracking (recommended), "lite" = faster, less accurate
POSE_MODEL_VARIANT = "heavy"
# Temporal smoothing: EMA alpha for pose landmarks (0=no smooth, 0.3=moderate, 0.6=strong)
POSE_SMOOTHING_ALPHA = 0.4
# YOLO model: "yolov8n"=fast, "yolov8s"=better accuracy (recommended)
YOLO_MODEL = "yolov8s"
MIN_DETECTION_CONFIDENCE = 0.5
MIN_TRACKING_CONFIDENCE = 0.5

# Landmark temporal smoothing (reduce jitter)
# Higher = smoother but more lag (0.0 = off, 0.7 = recommended)
LANDMARK_SMOOTHING_ALPHA = 0.7

# YOLO: "yolov8n" (fast), "yolov8s" (balanced, better accuracy), "yolov8m" (slower, best)
YOLO_MODEL = "yolov8s"

# Video processing
DEFAULT_FPS = 30
MAX_VIDEO_DURATION_SEC = 300  # 5 minutes
MAX_UPLOAD_MB = 500  # Max video file size

# Security - CORS allowed origins (add production origin when deploying)
CORS_ORIGINS: List[str] = [
    "http://localhost:8000", "http://127.0.0.1:8000",
    "http://localhost:8001", "http://127.0.0.1:8001",
    "http://localhost:8002", "http://127.0.0.1:8002",
    "http://localhost:8888", "http://127.0.0.1:8888",
    "http://localhost:34567", "http://127.0.0.1:34567",
    "http://localhost:5050", "http://127.0.0.1:5050",
    "http://localhost:9000", "http://127.0.0.1:9000",
    "http://localhost:3000", "http://127.0.0.1:3000",
]

# Sport recognition
SUPPORTED_SPORTS = [
    "basketball", "soccer", "tennis", "golf", "baseball", "volleyball",
    "weightlifting", "running", "boxing", "yoga", "swimming", "unknown"
]

# Joint groups for scoring
JOINT_GROUPS = {
    "upper_body": ["shoulder", "elbow", "wrist", "hip"],
    "lower_body": ["knee", "ankle", "hip"],
    "core": ["hip", "shoulder"],
}


def setup_logging(level: int = logging.INFO, log_file: Optional[str] = None) -> logging.Logger:
    """Configure application logging. Returns root sport_analysis logger."""
    handlers = [logging.StreamHandler(sys.stdout)]
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_path, encoding="utf-8"))
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=handlers,
    )
    return logging.getLogger("sport_analysis")
