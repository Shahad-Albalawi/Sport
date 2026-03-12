"""Tests for PoseEstimator."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.models.pose_estimator import LANDMARK_NAMES, POSE_CONNECTIONS


def test_landmark_names_count():
    """MediaPipe pose has 33 landmarks."""
    assert len(LANDMARK_NAMES) == 33


def test_landmark_names_expected():
    """Key landmarks for sports analysis exist."""
    required = {"nose", "left_shoulder", "right_shoulder", "left_hip", "right_hip",
                "left_knee", "right_knee", "left_ankle", "right_ankle",
                "left_elbow", "right_elbow", "left_wrist", "right_wrist"}
    assert required.issubset(set(LANDMARK_NAMES))


def test_pose_connections_valid_indices():
    """All connection indices are within landmark range."""
    for i, j in POSE_CONNECTIONS:
        assert 0 <= i < 33
        assert 0 <= j < 33


def test_pose_estimator_process_frame_integration():
    """PoseEstimator processes frame and returns (result, landmarks_dict)."""
    try:
        from backend.models.pose_estimator import PoseEstimator
    except RuntimeError:
        pytest.skip("MediaPipe not available")
        return

    est = PoseEstimator()
    try:
        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        frame[:] = 128  # Gray
        result, landmarks = est.process_frame(frame)
        assert isinstance(landmarks, dict)
        assert all(isinstance(v, (tuple, list)) and len(v) >= 2 for v in landmarks.values())
        est.close()
    finally:
        est.close()
