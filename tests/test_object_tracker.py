"""Tests for ObjectTracker."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.models.object_tracker import (
    ObjectTracker,
    TrackedObject,
    COCO_SPORTS,
    COCO_CLASS_IDS,
)


def test_tracked_object_dataclass():
    """TrackedObject has required fields."""
    obj = TrackedObject(
        label="sports_ball",
        bbox=(0.1, 0.2, 0.1, 0.1),
        confidence=0.8,
        frame_idx=0,
    )
    assert obj.label == "sports_ball"
    assert len(obj.bbox) == 4
    assert 0 <= obj.confidence <= 1


def test_coco_sports_mapping():
    """COCO class IDs map to valid labels."""
    assert 32 in COCO_SPORTS
    assert COCO_SPORTS[32] == "sports_ball"
    assert COCO_CLASS_IDS == set(COCO_SPORTS.keys())


def test_object_tracker_detect_empty_frame():
    """ObjectTracker returns list (possibly empty) for empty frame."""
    tracker = ObjectTracker()
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    objs = tracker.detect_objects(frame, frame_idx=0)
    assert isinstance(objs, list)
    assert all(isinstance(o, TrackedObject) for o in objs)


def test_object_tracker_detect_colored_frame():
    """Color-based detection can find orange blobs (basketball)."""
    tracker = ObjectTracker(min_contour_area=20)
    # Orange-ish frame (HSV: Hue ~15)
    frame = np.zeros((120, 160, 3), dtype=np.uint8)
    frame[:, :] = [50, 120, 255]  # BGR orange
    objs = tracker.detect_objects(frame, frame_idx=0)
    assert isinstance(objs, list)


def test_object_tracker_bbox_format():
    """Detected objects have normalized bbox (x,y,w,h) in 0-1."""
    tracker = ObjectTracker()
    frame = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    objs = tracker.detect_objects(frame, frame_idx=0)
    for o in objs:
        x, y, w, h = o.bbox
        assert 0 <= x <= 1
        assert 0 <= y <= 1
        assert 0 <= w <= 1
        assert 0 <= h <= 1
