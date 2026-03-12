"""Tests for ReportExporter (PDF, CSV, JSON)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from backend.reports.exporters import ReportExporter
from backend.config import REPORTS_DIR


def test_export_json():
    """JSON export produces valid file and strips name_ar."""
    exporter = ReportExporter()
    data = {
        "sport": "football",
        "sport_name_en": "Football (Soccer)",
        "overall_score": 7.5,
        "movements_analyzed": [
            {"id": "kick", "name_en": "Kick", "name_ar": "ضرب", "score": 8},
        ],
    }
    path = exporter.export_json(data, filename="test_export.json")
    assert path.exists()
    assert path.suffix == ".json"
    import json
    with open(path) as f:
        loaded = json.load(f)
    assert loaded["sport"] == "football"
    assert "name_ar" not in loaded.get("movements_analyzed", [{}])[0]
    path.unlink(missing_ok=True)


def test_export_csv():
    """CSV export produces valid file."""
    exporter = ReportExporter()
    frames = [{"overall_score": 75, "movement": "kick", "errors": ""}]
    summary = {"sport": "football", "overall_score": 7.5}
    path = exporter.export_csv(frames, summary=summary, filename="test_export.csv")
    assert path.exists()
    assert path.suffix == ".csv"
    path.unlink(missing_ok=True)


def test_export_pdf():
    """PDF export produces valid file."""
    exporter = ReportExporter()
    path = exporter.export_pdf(
        sport="football",
        sport_name="Football (Soccer)",
        movements_analyzed=[{"id": "kick", "name_en": "Kick", "score": 8, "frames_count": 10}],
        overall_score=7.5,
        errors=["Knee valgus"],
        coaching_feedback=[{"error": "Knee valgus", "feedback": "Keep knees over toes"}],
        recommendations=[],
        development_plan=["Phase 1: Basics"],
        filename="test_export.pdf",
    )
    assert path.exists()
    assert path.suffix == ".pdf"
    path.unlink(missing_ok=True)
