"""Tests for VideoOverlay helpers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from backend.video.overlay import _angle_deg


def test_angle_deg_right_angle():
    """90° angle at p2."""
    # Right angle: p1=(0,0), p2=(0,1), p3=(1,1) -> 90°
    p1, p2, p3 = (0.0, 0.0), (0.0, 0.5), (0.5, 0.5)
    angle = _angle_deg(p1, p2, p3, w=100, h=100)
    assert angle is not None
    assert 88 <= angle <= 92


def test_angle_deg_straight():
    """180° straight line."""
    p1, p2, p3 = (0.0, 0.5), (0.5, 0.5), (1.0, 0.5)
    angle = _angle_deg(p1, p2, p3, w=100, h=100)
    assert angle is not None
    assert 175 <= angle <= 185
