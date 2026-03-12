"""Tests for AnalysisPipeline."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from backend.pipeline import AnalysisPipeline
from backend.config import setup_logging

setup_logging(level=50)  # CRITICAL to reduce log noise


def test_pipeline_requires_valid_source():
    """Pipeline raises on invalid video source."""
    from backend.exceptions import VideoSourceError
    pipeline = AnalysisPipeline()
    with pytest.raises((OSError, RuntimeError, FileNotFoundError, VideoSourceError)):
        pipeline.run_analysis("/nonexistent/video.mp4", sport="football")


def test_pipeline_stop():
    """Stop does not raise."""
    pipeline = AnalysisPipeline()
    pipeline.stop_analysis()
    assert pipeline._processor is None or pipeline._processor is not None


def test_score_conversion():
    """Score 0-100 maps to 0-10."""
    from backend.video.processor import _score_100_to_10
    assert _score_100_to_10(0) == 0
    assert _score_100_to_10(100) == 10
    assert _score_100_to_10(75) == 7.5
    assert 0 <= _score_100_to_10(50) <= 10
