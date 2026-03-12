"""Tests for backend.utils."""

import numpy as np
import pytest
from dataclasses import dataclass

# Add project root to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.utils import to_json_safe, safe_get, joint_score_to_dict, strip_arabic_fields


def test_to_json_safe_numpy():
    """Numpy types convert to Python native."""
    assert to_json_safe(np.int32(42)) == 42
    assert to_json_safe(np.float64(3.14)) == 3.14
    assert to_json_safe(np.bool_(True)) == 1
    assert to_json_safe(np.array([1, 2, 3])) == [1, 2, 3]


def test_to_json_safe_native():
    """Native types pass through."""
    assert to_json_safe(42) == 42
    assert to_json_safe(3.14) == 3.14
    assert to_json_safe(True) is True
    assert to_json_safe("hello") == "hello"
    assert to_json_safe(None) is None


def test_to_json_safe_dict():
    """Nested dicts convert recursively."""
    d = {"a": np.float32(1.0), "b": [np.int64(2)]}
    assert to_json_safe(d) == {"a": 1.0, "b": [2]}


@dataclass
class Sample:
    x: int
    y: str


def test_to_json_safe_dataclass():
    """Dataclasses convert to dict."""
    s = Sample(x=1, y="hi")
    assert to_json_safe(s) == {"x": 1, "y": "hi"}


def test_safe_get_dict():
    assert safe_get({"a": 1}, "a") == 1
    assert safe_get({"a": 1}, "b", 0) == 0


def test_safe_get_dataclass():
    s = Sample(x=1, y="hi")
    assert safe_get(s, "x") == 1
    assert safe_get(s, "z", "default") == "default"


def test_joint_score_to_dict():
    js = {"name": "knee", "score": 80.0}
    assert joint_score_to_dict(js) == js
    assert joint_score_to_dict(None) == {}


def test_strip_arabic_fields():
    """Ensure name_ar and Arabic-only fields are removed from exports."""
    d = {"name_en": "Football", "name_ar": "كرة القدم", "score": 8}
    out = strip_arabic_fields(d)
    assert "name_en" in out
    assert "name_ar" not in out
    assert out["score"] == 8
    nested = {"movements": [{"id": "kick", "name_ar": "ضرب", "name_en": "Kick"}]}
    out2 = strip_arabic_fields(nested)
    assert out2["movements"][0].get("name_en") == "Kick"
    assert "name_ar" not in out2["movements"][0]
