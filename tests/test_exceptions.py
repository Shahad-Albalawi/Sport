"""Tests for custom exceptions."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from backend.exceptions import (
    SportAnalysisError,
    VideoSourceError,
    AnalysisTimeoutError,
)


def test_sport_analysis_error():
    """SportAnalysisError has message, code, details."""
    err = SportAnalysisError("test", code="TEST", details={"x": 1})
    assert str(err) == "test"
    assert err.code == "TEST"
    assert err.details["x"] == 1


def test_video_source_error():
    """VideoSourceError includes source in details."""
    err = VideoSourceError("Cannot open", source="/path/video.mp4")
    assert "Cannot open" in str(err)
    assert err.code == "VIDEO_SOURCE_ERROR"
    assert err.details.get("source") == "/path/video.mp4"


def test_analysis_timeout_error():
    """AnalysisTimeoutError has TIMEOUT code."""
    err = AnalysisTimeoutError()
    assert err.code == "TIMEOUT"
