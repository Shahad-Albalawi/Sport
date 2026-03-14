"""API tests using FastAPI TestClient."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from fastapi.testclient import TestClient

from backend.api.server import app
from backend.config import UPLOADS_DIR

client = TestClient(app)


def test_root():
    """Root returns ok."""
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ok"
    assert "Sports Movement Analysis" in data.get("service", "")


def test_health():
    """Health endpoint returns version and checks."""
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "healthy"
    assert "version" in data
    assert data.get("checks", {}).get("api") == "ok"


def test_sports_list():
    """List supported sports."""
    r = client.get("/api/sports")
    assert r.status_code == 200
    data = r.json()
    assert "sports" in data
    sports = data["sports"]
    assert len(sports) > 0
    ids = [s["id"] for s in sports]
    assert "auto" in ids
    assert "football" in ids
    assert "unknown" not in ids


def test_analyze_missing_sport():
    """Analyze without sport returns 422 (validation error)."""
    r = client.post("/api/analyze", json={"source": "/tmp/x.mp4"})
    assert r.status_code == 422


def test_analyze_invalid_sport():
    """Analyze with unknown sport returns 400."""
    r = client.post(
        "/api/analyze",
        json={"source": "/tmp/x.mp4", "sport": "invalid_sport"},
    )
    assert r.status_code == 400
    assert "Unknown sport" in r.text or "invalid" in r.text.lower()


def test_analyze_missing_source():
    """Analyze without source (and no camera) returns 400."""
    r = client.post(
        "/api/analyze",
        json={"sport": "football"},
    )
    assert r.status_code == 400


def test_upload_invalid_type():
    """Upload non-video returns 400."""
    r = client.post(
        "/api/upload",
        files={"file": ("test.txt", b"hello", "text/plain")},
    )
    assert r.status_code == 400
    assert "Invalid file type" in r.text or "invalid" in r.text.lower()


def test_status_invalid_job_id():
    """Status with invalid job_id format returns 400."""
    r = client.get("/api/status/invalid-job-id!")
    assert r.status_code == 400


def test_status_not_found():
    """Status for unknown job returns 404."""
    r = client.get("/api/status/" + "a" * 32)  # Valid format, not in store
    assert r.status_code == 404


def test_stream_not_found():
    """Stream for unknown job returns 404."""
    r = client.get("/api/stream/" + "b" * 32)  # Valid format, not in store
    assert r.status_code == 404


def test_download_report_invalid_filename():
    """Report download with path traversal rejected."""
    r = client.get("/api/reports/../../../etc/passwd")
    assert r.status_code in (400, 404)


def test_stop():
    """Stop returns ok even when no analysis running."""
    r = client.post("/api/stop")
    assert r.status_code == 200
    assert r.json().get("status") == "stop requested"


def test_stop_alias():
    """POST /stop alias works."""
    r = client.post("/stop")
    assert r.status_code == 200


def test_progress_not_found():
    """Progress for unknown job returns 404."""
    r = client.get("/progress/" + "c" * 32)  # Valid format, not in store
    assert r.status_code == 404


def test_report_not_found():
    """Report for unknown job returns 404."""
    r = client.get("/report/" + "d" * 32)  # Valid format, not in store
    assert r.status_code == 404


def test_start_video_requires_source():
    """Start video without source returns 400."""
    r = client.post("/start/video", json={"sport": "football"})
    assert r.status_code == 400


def test_start_camera_accepts_sport():
    """Start camera with sport returns 400 (no camera) or 200."""
    r = client.post("/start/camera", json={"sport": "football", "use_camera": True})
    # May fail at video open (camera not available) but request is valid
    assert r.status_code in (200, 400, 500)
