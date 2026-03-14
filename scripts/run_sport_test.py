"""
Run sport-specific analysis on a video.

Usage:
  python scripts/run_sport_test.py SPORT [VIDEO_PATH]

  SPORT: football, tennis, basketball, weightlifting, soccer, etc.
  VIDEO_PATH: optional. If omitted, uses first .mp4 from sports/{SportName}/videos/
              or creates a synthetic test video.

Examples:
  python scripts/run_sport_test.py football
  python scripts/run_sport_test.py tennis sports/Tennis/videos/serve_sample.mp4
  python scripts/run_sport_test.py basketball --skip-overlay

Run from project root.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def create_synthetic_video(path: Path, frames: int = 60) -> str:
    """Create minimal synthetic video for testing when no sample available."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        raise RuntimeError("OpenCV (cv2) required. Install: pip install opencv-python")

    path.parent.mkdir(parents=True, exist_ok=True)
    w, h, fps = 320, 240, 10
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, fps, (w, h))
    for i in range(frames):
        frame = np.zeros((h, w, 3), dtype=np.uint8)
        frame[:] = (i % 50, 100, 150)
        writer.write(frame)
    writer.release()
    return str(path)


def find_sample_video(sport_id: str) -> str | None:
    """Look for sample video in sports/{SportName}/videos/."""
    from backend.sport_registry import get_sport_folder, get_sport_videos_dir

    videos_dir = get_sport_videos_dir(sport_id)
    for ext in ("*.mp4", "*.avi", "*.mov"):
        for p in sorted(videos_dir.glob(ext)):
            return str(p)
    return None


def main():
    parser = argparse.ArgumentParser(
        description="Run sport-specific video analysis",
        epilog="Example: python scripts/run_sport_test.py football sports/Football/videos/kick.mp4"
    )
    parser.add_argument("sport", help="Sport ID: football, tennis, basketball, weightlifting, soccer, etc.")
    parser.add_argument("video", nargs="?", help="Path to video file (optional)")
    parser.add_argument("--skip-overlay", action="store_true", help="Skip overlay video generation (faster)")
    parser.add_argument("-q", "--quiet", action="store_true", help="Minimal output")
    args = parser.parse_args()

    sport = (args.sport or "football").lower().strip().replace(" ", "_")
    video_path = args.video

    if not video_path:
        sample = find_sample_video(sport)
        if sample:
            video_path = sample
            if not args.quiet:
                print(f"Using sample video: {video_path}")
        else:
            synthetic_path = ROOT / "output" / "synthetic_test.mp4"
            video_path = create_synthetic_video(synthetic_path)
            if not args.quiet:
                print(f"No sample found. Created synthetic video: {video_path}")

    if not Path(video_path).exists():
        print(f"Video not found: {video_path}")
        sys.exit(1)

    from backend.config import setup_logging
    from backend.pipeline import AnalysisPipeline

    setup_logging()
    pipeline = AnalysisPipeline()
    result = pipeline.run_analysis(
        video_path,
        sport=sport,
        skip_overlay=args.skip_overlay,
    )

    if args.quiet:
        print(f"{result.get('overall_score', 0):.1f}")
        return

    print("\n--- Sport Analysis Complete ---")
    print(f"Sport: {result.get('sport_name_en', result.get('sport', sport))}")
    print(f"Overall score: {result.get('overall_score', 0):.1f}/10")
    print(f"Total frames: {result.get('total_frames', 0)}")
    print(f"Injury risk score: {result.get('injury_risk_score', 0):.0f}/100")
    print(f"Confidence: {result.get('confidence', 1.0):.2f}")
    print(f"Output video: {result.get('output_video_path', 'N/A')}")
    strengths = result.get("strengths", [])
    if strengths:
        print("Strengths:", ", ".join(strengths[:3]))
    errors = result.get("errors", [])
    if errors:
        print("Errors:", ", ".join(errors[:3]))
    possible_injuries = result.get("possible_injuries", [])
    if possible_injuries:
        print("Possible injuries:", ", ".join(possible_injuries[:3]))
    warnings = result.get("injury_risk_warnings", [])
    if warnings:
        print("Injury risk warnings:", ", ".join(warnings[:3]))
    print("Reports:", result.get("report_files", {}))
    print("Internal references:", "stored" if result.get("internal_references") else "N/A")


if __name__ == "__main__":
    main()
