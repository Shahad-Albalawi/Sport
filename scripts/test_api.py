"""
Test the full API flow: analyze video -> poll status -> verify result.
Run with server already running: python app.py
Usage: python scripts/test_api.py [video_path]
"""

import sys
import time
import requests
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "http://127.0.0.1:8000"


def create_test_video(path: Path, num_frames: int = 30):
    """Create minimal test video."""
    import cv2
    import numpy as np

    path.parent.mkdir(parents=True, exist_ok=True)
    out = cv2.VideoWriter(
        str(path), cv2.VideoWriter_fourcc(*"mp4v"), 15, (640, 480)
    )
    for i in range(num_frames):
        frame = np.ones((480, 640, 3), dtype=np.uint8) * (50 + (i % 80))
        cv2.putText(frame, f"Frame {i}", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        out.write(frame)
    out.release()
    print(f"Created: {path}")
    return path


def main():
    video_path = sys.argv[1] if len(sys.argv) > 1 else None
    if not video_path:
        test_path = ROOT / "output" / "test_api.mp4"
        create_test_video(test_path, 30)
        video_path = str(test_path)
    elif not Path(video_path).exists():
        print(f"Error: file not found: {video_path}")
        sys.exit(1)

    print("1. Testing API root...")
    r = requests.get(f"{API}/", timeout=5)
    assert r.status_code == 200, r.text
    print("   OK")

    print("2. Starting analysis...")
    r = requests.post(
        f"{API}/api/analyze",
        json={"source": video_path, "sport": "football"},
        params={"export_csv": True, "export_pdf": True, "export_json": True},
        timeout=10,
    )
    assert r.status_code == 200, f"{r.status_code} {r.text}"
    job_id = r.json()["job_id"]
    print(f"   job_id={job_id}")

    print("3. Polling status...")
    for _ in range(120):
        r = requests.get(f"{API}/api/status/{job_id}", timeout=5)
        assert r.status_code == 200, r.text
        data = r.json()
        if data.get("progress"):
            p = data["progress"]
            print(f"   progress: frame {p.get('frame')}/{p.get('total')}")
        if data["status"] == "completed":
            result = data.get("result", {})
            print("\n4. Result:")
            print(f"   sport: {result.get('sport')}")
            print(f"   score: {result.get('overall_score')}")
            print(f"   frames: {result.get('total_frames')}")
            print(f"   output: {result.get('output_filename')}")
            print(f"   reports: {result.get('report_files')}")
            assert result.get("sport") is not None
            assert "report_files" in result
            print("\n--- All checks passed ---")
            return
        if data["status"] == "error":
            print(f"   ERROR: {data.get('error')}")
            sys.exit(1)
        time.sleep(1)

    print("Timeout waiting for completion")
    sys.exit(1)


if __name__ == "__main__":
    main()
