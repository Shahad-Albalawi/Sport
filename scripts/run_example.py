"""
Example: Process a video file and generate overlay + reports.
Run from project root: python scripts/run_example.py [path_to_video]
If no path given, uses camera (0) for a few seconds or creates a test frame.
"""

import sys
from pathlib import Path

# Add project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def create_test_video(path: Path, num_frames: int = 60):
    """Create a minimal test video (colored frames) for demo."""
    import cv2
    import numpy as np

    out = cv2.VideoWriter(
        str(path),
        cv2.VideoWriter_fourcc(*"mp4v"),
        15,
        (640, 480),
    )
    for i in range(num_frames):
        # Vary color slightly to simulate motion
        frame = np.ones((480, 640, 3), dtype=np.uint8) * (50 + (i % 100))
        cv2.putText(
            frame, f"Frame {i} - Test Video",
            (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2,
        )
        out.write(frame)
    out.release()
    print(f"Created test video: {path}")


def main():
    from backend.config import setup_logging
    from backend.pipeline import AnalysisPipeline

    setup_logging()
    pipeline = AnalysisPipeline()

    source = sys.argv[1] if len(sys.argv) > 1 else None
    if not source:
        # Create test video
        test_path = ROOT / "output" / "test_input.mp4"
        test_path.parent.mkdir(parents=True, exist_ok=True)
        create_test_video(test_path)
        source = str(test_path)

    print(f"Analyzing: {source}")
    sport = sys.argv[2] if len(sys.argv) > 2 else "football"
    result = pipeline.run_analysis(source, sport=sport)

    print("\n--- Analysis Complete ---")
    print(f"Sport: {result.get('sport')}")
    print(f"Score: {result.get('overall_score')}")
    print(f"Frames: {result.get('total_frames')}")
    print(f"Output video: {result.get('output_video_path')}")
    print("Reports: check reports/ folder")
    print("\nExport paths:")
    for fmt in ["csv", "pdf", "json"]:
        for p in (ROOT / "reports").glob(f"*.{fmt}"):
            print(f"  {p}")


if __name__ == "__main__":
    main()
