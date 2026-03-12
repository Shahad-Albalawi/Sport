"""Entry point: run API server or CLI analysis."""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))


def main():
    parser = argparse.ArgumentParser(description="Sports Movement Analysis")
    parser.add_argument("--serve", action="store_true", help="Run REST API server")
    parser.add_argument("--analyze", metavar="VIDEO", help="Analyze video file (path)")
    parser.add_argument("--sport", default="football", help="Sport for analysis (default: football)")
    parser.add_argument("--camera", action="store_true", help="Analyze from camera (not supported)")
    parser.add_argument("--host", default="0.0.0.0", help="API host")
    parser.add_argument("--port", type=int, default=8000, help="API port")
    args = parser.parse_args()

    if args.serve:
        from backend.api.server import run_server
        run_server(host=args.host, port=args.port)
        return

    if args.analyze:
        from backend.config import setup_logging
        from backend.pipeline import AnalysisPipeline

        setup_logging()
        pipeline = AnalysisPipeline()
        result = pipeline.run_analysis(args.analyze, sport=args.sport)
        print("Analysis complete.")
        print(f"Sport: {result.get('sport')}")
        print(f"Score: {result.get('overall_score')}")
        print(f"Output: {result.get('output_video_path')}")
        print("Reports saved to reports/")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
