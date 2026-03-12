"""Tests for MovementRecognizer."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.models.movement_recognizer import MovementRecognizer, MOVEMENT_TYPES


def test_empty_landmarks_returns_unknown():
    """Empty landmarks -> unknown movement."""
    rec = MovementRecognizer()
    movement, conf = rec.recognize({})
    assert movement == "unknown"
    assert conf >= 0


def test_standing_pose():
    """Standing-like landmarks produce static/general or low-confidence."""
    rec = MovementRecognizer()
    landmarks = {
        "left_hip": (0.4, 0.6, 0),
        "left_knee": (0.4, 0.75, 0),
        "left_ankle": (0.4, 0.9, 0),
        "right_hip": (0.5, 0.6, 0),
        "right_knee": (0.5, 0.75, 0),
        "right_ankle": (0.5, 0.9, 0),
        "left_shoulder": (0.35, 0.35, 0),
        "right_shoulder": (0.45, 0.35, 0),
    }
    movement, conf = rec.recognize(landmarks)
    assert movement in MOVEMENT_TYPES + ["unknown", "static"]
    assert 0 <= conf <= 1


def test_movement_types_defined():
    """All expected movement types exist."""
    expected = {"kick", "jump", "sprint", "punch", "swing", "throw", "squat", "lunge", "rotation"}
    assert set(MOVEMENT_TYPES) >= expected
