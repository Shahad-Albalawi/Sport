"""Shared utilities for safe data access and JSON serialization."""

from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List, Optional

__all__ = ["to_json_safe", "safe_get", "joint_score_to_dict", "rec_to_dict", "strip_arabic_fields"]

import numpy as np


def to_json_safe(obj: Any) -> Any:
    """
    Recursively convert objects to JSON-serializable form.
    Handles: numpy scalars, ndarrays, dataclasses, bool, nested dicts/lists.
    """
    if obj is None:
        return None
    # Numpy scalars (int, float, bool): .item() for NumPy 1.x/2.x compatibility
    if hasattr(obj, "item") and callable(getattr(obj, "item")):
        try:
            return to_json_safe(obj.item())  # 0-d arrays & scalars; multi-elem raises
        except (ValueError, TypeError):
            pass
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, (np.integer, np.int8, np.int16, np.int32, np.int64)):
        return int(obj)
    if isinstance(obj, (np.floating, np.float16, np.float32, np.float64)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    # Native JSON types
    if isinstance(obj, (bool, int, float, str)):
        return obj
    # Lists and tuples
    if isinstance(obj, (list, tuple)):
        return [to_json_safe(x) for x in obj]
    # Dicts
    if isinstance(obj, dict):
        return {str(k): to_json_safe(v) for k, v in obj.items()}
    # Dataclasses
    if is_dataclass(obj) and not isinstance(obj, type):
        return to_json_safe(asdict(obj))
    # Objects with __dict__
    if hasattr(obj, "__dict__"):
        return to_json_safe(vars(obj))
    return str(obj)


def safe_get(obj: Any, key: str, default: Any = None) -> Any:
    """Get value from dict or dataclass (JointScore, CorrectiveExercise, etc.)."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    if hasattr(obj, "__dataclass_fields__"):
        return getattr(obj, key, default)
    return default


def joint_score_to_dict(js: Any) -> Dict[str, Any]:
    """Convert JointScore or dict to plain dict. Use safe_get for access."""
    if js is None:
        return {}
    if isinstance(js, dict):
        return {str(k): to_json_safe(v) for k, v in js.items()}
    if hasattr(js, "__dataclass_fields__"):
        return {str(k): to_json_safe(v) for k, v in asdict(js).items()}
    return {}


def rec_to_dict(rec: Any) -> Dict[str, Any]:
    """Convert CorrectiveExercise or dict to plain dict."""
    return joint_score_to_dict(rec)


def strip_arabic_fields(obj: Any) -> Any:
    """
    Recursively remove name_ar and similar Arabic-only fields from dicts.
    Ensures user-facing exports contain only English (name_en, name).
    """
    if obj is None:
        return None
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in ("name_ar",):
                continue
            out[k] = strip_arabic_fields(v)
        return out
    if isinstance(obj, (list, tuple)):
        return [strip_arabic_fields(x) for x in obj]
    return obj
