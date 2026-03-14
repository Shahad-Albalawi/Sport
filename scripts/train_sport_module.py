"""
Train, test, and continuously improve sport-specific modules.

Usage:
  python scripts/train_sport_module.py SPORT [VIDEO_PATHS...] [OPTIONS]

  SPORT: football, basketball, weightlifting, tennis, etc.
  VIDEO_PATHS: paths to sport-specific videos. If omitted, uses videos from
               sports/{SportName}/videos/

  Options:
    --apply-improvements   Apply safe range and weight updates after analysis
    --skip-overlay        Skip overlay video (faster)
    --export-reports      Export training report (PDF, CSV, JSON)
    --quiet               Minimal output

Examples:
  python scripts/train_sport_module.py football
  python scripts/train_sport_module.py football sports/Football/videos/*.mp4
  python scripts/train_sport_module.py basketball --apply-improvements --export-reports

Run from project root. Data is stored per sport in training_data/{sport}/.
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def find_sport_videos(sport_id: str) -> list:
    """Find videos in sports/{SportName}/videos/."""
    from backend.sport_registry import get_sport_folder, get_sport_videos_dir

    videos_dir = get_sport_videos_dir(sport_id)
    out = []
    for ext in ("*.mp4", "*.avi", "*.mov", "*.mkv"):
        for p in sorted(videos_dir.glob(ext)):
            out.append(str(p))
    return out


def main():
    parser = argparse.ArgumentParser(
        description="Train and improve sport-specific modules using real-world videos",
        epilog="Data stored in training_data/{sport}/. No cross-sport data mixing.",
    )
    parser.add_argument("sport", help="Sport ID: football, basketball, weightlifting, tennis, etc.")
    parser.add_argument("videos", nargs="*", help="Video file paths (optional; uses sport videos/ if empty)")
    parser.add_argument("--apply-improvements", action="store_true",
                        help="Apply safe range and weight updates after batch")
    parser.add_argument("--skip-overlay", action="store_true", help="Skip overlay video (faster)")
    parser.add_argument("--export-reports", action="store_true",
                        help="Export training report (PDF, CSV, JSON)")
    parser.add_argument("-q", "--quiet", action="store_true", help="Minimal output")
    args = parser.parse_args()

    sport = (args.sport or "football").lower().strip().replace(" ", "_")

    video_paths = list(args.videos)
    if not video_paths:
        video_paths = find_sport_videos(sport)
    if not video_paths:
        if not args.quiet:
            print(f"No videos found for {sport}. Add videos to sports/{sport.title()}/videos/ or pass paths.")
        sys.exit(1)

    from backend.config import setup_logging
    from backend.training import SportBatchProcessor, ImprovementEngine, TrainingReportExporter

    setup_logging()
    processor = SportBatchProcessor(
        sport,
        skip_overlay=args.skip_overlay,
        on_progress=lambda i, n, msg: print(f"  [{i+1}/{n}] {msg}") if not args.quiet else None,
    )

    if not args.quiet:
        print(f"Training {sport} module on {len(video_paths)} video(s)...")
        print("  (Sport-specific only — no data from other sports)")

    try:
        result = processor.process_batch(
            video_paths,
            run_improvement=args.apply_improvements,
        )
    except Exception as e:
        print(f"Training failed: {e}")
        sys.exit(1)

    if not args.quiet:
        print("\n--- Sport Module Training Complete ---")
        print(f"Sport: {sport}")
        print(f"Videos processed: {result.get('videos_processed', 0)}")
        stats = result.get("movement_stats", {})
        if stats:
            print(f"Movements detected: {list(stats.keys())}")
        err_counts = result.get("error_counts", {})
        if err_counts:
            top = sorted(err_counts.items(), key=lambda x: -x[1])[:5]
            print("Top errors:", ", ".join(f"{k}({v})" for k, v in top))
        if args.apply_improvements:
            impr = result.get("improvements_applied", {})
            if impr and impr.get("safe_ranges_updated"):
                print("Safe ranges updated:", len(impr["safe_ranges_updated"]))
            if impr and impr.get("weights_updated"):
                print("Injury risk weights updated")

    if args.export_reports:
        exporter = TrainingReportExporter(sport)
        report_files = exporter.export_all(
            batch_summary=result,
            improvements=result.get("improvements_applied"),
        )
        if not args.quiet:
            print("Reports:", report_files)

    if args.quiet:
        print(result.get("videos_processed", 0))


if __name__ == "__main__":
    main()
