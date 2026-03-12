"""Integration tests: full pipeline with synthetic video."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.conftest import _create_test_video


pytestmark = pytest.mark.integration


@pytest.fixture
def test_video(tmp_path):
    """Synthetic 30-frame video (3 sec at 10fps)."""
    return _create_test_video(tmp_path, frames=30)


def test_full_pipeline_analyzes_video(test_video):
    """Full pipeline: video -> analysis -> report. Validates structure."""
    from backend.pipeline import AnalysisPipeline
    from backend.config import setup_logging

    setup_logging(level=50)
    pipeline = AnalysisPipeline()
    result = pipeline.run_analysis(test_video, sport="football", skip_overlay=True)

    assert "sport" in result
    assert "overall_score" in result
    assert "movements_analyzed" in result
    assert "errors" in result
    assert "strengths" in result
    assert 0 <= result["overall_score"] <= 10
    assert isinstance(result["movements_analyzed"], list)
    assert result["total_frames"] >= 1


def test_full_pipeline_with_overlay(test_video, tmp_path):
    """Pipeline with overlay produces output video file."""
    from backend.pipeline import AnalysisPipeline
    from backend.config import setup_logging, OUTPUT_DIR

    setup_logging(level=50)
    pipeline = AnalysisPipeline()
    result = pipeline.run_analysis(
        test_video, sport="football", skip_overlay=False
    )

    assert "output_video_path" in result or "output_filename" in result
    out_path = result.get("output_video_path")
    if out_path and Path(out_path).exists():
        assert Path(out_path).suffix == ".mp4"


def test_pipeline_exports_reports(test_video):
    """Pipeline generates PDF, CSV, JSON reports."""
    from backend.pipeline import AnalysisPipeline
    from backend.config import setup_logging, REPORTS_DIR

    setup_logging(level=50)
    pipeline = AnalysisPipeline()
    result = pipeline.run_analysis(
        test_video,
        sport="football",
        skip_overlay=True,
        export_csv=True,
        export_pdf=True,
        export_json=True,
    )

    files = result.get("report_files", {})
    assert "pdf" in files
    assert "csv" in files
    assert "json" in files
    for fname in files.values():
        assert (REPORTS_DIR / fname).exists()
