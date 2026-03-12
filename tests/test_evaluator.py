"""Tests for movement evaluator."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.analysis.evaluator import MovementEvaluator, MovementEvaluation


def test_empty_landmarks():
    ev = MovementEvaluator()
    result = ev.evaluate_frame({}, frame_idx=0)
    assert result.overall_score == 0.0
    assert result.is_correct is False
    assert len(result.errors) >= 1


def test_with_landmarks():
    """Minimal landmarks - standing posture (ideal angles)."""
    ev = MovementEvaluator()
    # Simplified landmarks (x, y normalized 0-1)
    landmarks = {
        "left_hip": (0.4, 0.6, 0),
        "left_knee": (0.4, 0.75, 0),
        "left_ankle": (0.4, 0.9, 0),
        "right_hip": (0.5, 0.6, 0),
        "right_knee": (0.5, 0.75, 0),
        "right_ankle": (0.5, 0.9, 0),
        "left_shoulder": (0.35, 0.35, 0),
        "right_shoulder": (0.45, 0.35, 0),
        "nose": (0.4, 0.2, 0),
    }
    result = ev.evaluate_frame(landmarks, frame_idx=0)
    assert isinstance(result, MovementEvaluation)
    assert 0 <= result.overall_score <= 100
    assert isinstance(result.joint_scores, list)
    assert isinstance(result.errors, list)
