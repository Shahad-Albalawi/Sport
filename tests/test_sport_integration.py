"""
Per-sport integration tests: validate pipeline and models for each sport.

Runs full analysis with synthetic video for every sport profile to ensure:
- Pipeline completes without errors
- Sport-specific evaluation runs correctly
- Output structure is valid
- Reports export successfully
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.analysis.sport_profiles import SPORT_PROFILES, get_sport_profile
from tests.conftest import _create_test_video

# All sports with full profiles (exclude 'unknown' - fallback only)
SPORTS_TO_TEST = [k for k in SPORT_PROFILES.keys() if k != "unknown"]

pytestmark = pytest.mark.integration


@pytest.fixture
def short_test_video(tmp_path):
    """Minimal 15-frame video for fast per-sport testing."""
    return _create_test_video(tmp_path, frames=15)


# --- Pipeline integration: each sport with video ---


@pytest.mark.parametrize("sport", SPORTS_TO_TEST)
def test_pipeline_per_sport(short_test_video, sport):
    """Full pipeline runs successfully for each sport with synthetic video."""
    from backend.pipeline import AnalysisPipeline
    from backend.config import setup_logging

    setup_logging(level=50)
    pipeline = AnalysisPipeline()
    result = pipeline.run_analysis(short_test_video, sport=sport, skip_overlay=True)

    assert "sport" in result
    assert "overall_score" in result
    assert "movements_analyzed" in result
    assert "errors" in result
    assert "strengths" in result
    assert "total_frames" in result
    assert 0 <= result["overall_score"] <= 10
    assert isinstance(result["movements_analyzed"], list)
    assert isinstance(result["errors"], list)
    assert isinstance(result["strengths"], list)
    assert result["total_frames"] >= 1
    # Sport should be resolved (may differ from input if auto-detected)
    assert result.get("sport") or result.get("sport_name_en")


@pytest.mark.parametrize("sport", SPORTS_TO_TEST)
def test_pipeline_exports_per_sport(short_test_video, sport):
    """Each sport exports CSV, PDF, JSON without errors."""
    from backend.pipeline import AnalysisPipeline
    from backend.config import setup_logging, REPORTS_DIR

    setup_logging(level=50)
    pipeline = AnalysisPipeline()
    result = pipeline.run_analysis(
        short_test_video,
        sport=sport,
        skip_overlay=True,
        export_csv=True,
        export_pdf=True,
        export_json=True,
    )

    files = result.get("report_files", {})
    assert "csv" in files
    assert "pdf" in files
    assert "json" in files
    for fpath in files.values():
        full_path = REPORTS_DIR / fpath
        assert full_path.exists(), f"Sport '{sport}': Report not found: {full_path}"


# --- Sport profile / model unit checks per sport ---


@pytest.mark.parametrize("sport", SPORTS_TO_TEST)
def test_sport_profile_loads(sport):
    """Sport profile loads and has required keys."""
    profile = get_sport_profile(sport)
    assert "name_en" in profile
    assert "technical_movements" in profile
    assert "key_joints" in profile
    assert "critical_errors" in profile
    assert "coaching_tips" in profile
    assert isinstance(profile["technical_movements"], list)
    assert isinstance(profile["critical_errors"], list)


@pytest.mark.parametrize("sport", SPORTS_TO_TEST)
def test_evaluator_with_sport_profile(sport):
    """MovementEvaluator works with each sport profile (empty landmarks)."""
    from backend.analysis.evaluator import MovementEvaluator

    evaluator = MovementEvaluator()
    ev = evaluator.evaluate_frame({}, frame_idx=0, sport=sport, movement="static")
    assert ev is not None
    assert hasattr(ev, "overall_score")
    score = ev.overall_score  # 0-100 scale internally
    assert 0 <= score <= 100


@pytest.mark.parametrize("sport", SPORTS_TO_TEST)
def test_recommendation_engine_per_sport(sport):
    """RecommendationEngine returns exercises for each sport."""
    from backend.analysis.evaluator import RecommendationEngine

    engine = RecommendationEngine()
    recs = engine.get_recommendations(errors=["knee_valgus"], joint_scores=[], sport=sport)
    assert isinstance(recs, list)
    # May be empty for some sports, but should not crash
    for r in recs:
        assert hasattr(r, "name") or (isinstance(r, dict) and ("name" in r or "target_joint" in r))


@pytest.mark.parametrize("sport", SPORTS_TO_TEST)
def test_sport_inferencer_consistency(sport):
    """Sport inferencer can map movements to this sport or unknown."""
    from backend.models.sport_inferencer import infer_sport

    # Use a generic movement from this sport's profile
    profile = get_sport_profile(sport)
    movements = profile.get("technical_movements", [])
    generic = movements[0].get("generic", "static") if movements else "static"
    inferred_sport, conf = infer_sport(generic, [])
    # Should return a valid sport id (may or may not match - depends on movement+objects)
    assert inferred_sport in SPORT_PROFILES or inferred_sport == "unknown"
    assert 0 <= conf <= 1.0
