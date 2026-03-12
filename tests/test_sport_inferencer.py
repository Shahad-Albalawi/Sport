"""Tests for sport inferencer."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.models.sport_inferencer import infer_sport


def test_kick_ball_football():
    sport, conf = infer_sport("kick", ["ball"])
    assert sport == "football"
    assert conf >= 0.8


def test_swing_racket_tennis():
    sport, conf = infer_sport("swing", ["tennis_racket"])
    assert sport == "tennis"
    assert conf >= 0.8


def test_squat_weightlifting():
    sport, conf = infer_sport("squat", [])
    assert sport == "weightlifting"
    assert conf >= 0.5


def test_unknown_movement():
    sport, conf = infer_sport("unknown", [])
    assert sport == "unknown"
    assert conf == 0.0


def test_punch_boxing():
    sport, conf = infer_sport("punch", [])
    assert sport == "boxing"
    assert conf >= 0.5
