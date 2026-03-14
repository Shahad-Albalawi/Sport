"""
Continuous improvement engine for sport-specific modules.

After processing video batches:
- Tracks recurring errors
- Adjusts Safe Ranges based on observed angles from high-scoring movements
- Adjusts Injury Risk weights based on error frequency
- Adds Coaching Advice for newly discovered errors
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from backend.analysis.biomechanics import DEFAULT_SAFE_RANGES, ERROR_COACHING_MAP, compute_injury_risk_score
from backend.training.data_store import TrainingDataStore

logger = logging.getLogger("sport_analysis.training")

DEFAULT_WEIGHTS = {
    "knee_valgus": 25,
    "knee_angle_unsafe": 25,
    "unstable_landing": 20,
    "poor_hip_extension": 15,
    "ankle_instability": 15,
    "shoulder_imbalance": 10,
    "core_instability": 10,
    "limited_rotation": 8,
    "elbow_alignment": 5,
    "elbow_drop": 5,
}


class ImprovementEngine:
    """
    Analyze training data and apply improvements:
    - Safe ranges (from high-score movement angle percentiles)
    - Injury risk weights (from error frequency)
    - Coaching advice (for new errors)
    """

    def __init__(self, sport_id: str):
        self.sport_id = (sport_id or "unknown").lower().strip()
        self._store = TrainingDataStore(self.sport_id)

    def run_and_apply(self) -> Dict[str, Any]:
        """
        Analyze data, compute updates, apply to store, return report.
        """
        applied: Dict[str, Any] = {
            "safe_ranges_updated": [],
            "weights_updated": False,
            "coaching_additions": [],
        }

        safe_updates = self._compute_safe_range_updates()
        for (movement, joint), (min_d, max_d) in safe_updates.items():
            self._store.update_safe_ranges(movement, joint, min_d, max_d)
            applied["safe_ranges_updated"].append({
                "movement": movement,
                "joint": joint,
                "min": min_d,
                "max": max_d,
            })

        weight_updates = self._compute_weight_updates()
        if weight_updates:
            self._store.update_injury_risk_weights(weight_updates)
            applied["weights_updated"] = True

        new_errors = self._find_unmapped_errors()
        for err_key in new_errors:
            advice, injuries = _default_advice_for_error(err_key)
            self._store.add_coaching_advice(err_key, advice, injuries)
            applied["coaching_additions"].append({"error": err_key, "advice": advice[:80] + "..."})

        return applied

    def _compute_safe_range_updates(self) -> Dict[Tuple[str, str], Tuple[float, float]]:
        """
        For each movement+joint: use 10th–90th percentile of angles from high-scoring frames (>=7/10).
        Only update if we have enough samples and the suggested range is reasonable.
        """
        samples = self._store.get_joint_angle_samples()
        movements = self._store.get_movement_stats()
        if not samples or not movements:
            return {}

        updates: Dict[Tuple[str, str], Tuple[float, float]] = {}

        for joint, angles in samples.items():
            if len(angles) < 20:
                continue
            arr = np.array(angles)
            p10 = float(np.percentile(arr, 10))
            p90 = float(np.percentile(arr, 90))
            margin = (p90 - p10) * 0.1
            min_d = max(0, p10 - margin)
            max_d = min(180, p90 + margin)

            movement = self._infer_movement_for_joint(joint)
            if movement and (min_d < max_d) and (max_d - min_d >= 15):
                existing = self._get_current_safe_range(movement, joint)
                if existing:
                    e_min, e_max = existing
                    if abs(min_d - e_min) > 5 or abs(max_d - e_max) > 5:
                        updates[(movement, joint)] = (min_d, max_d)

        return updates

    def _infer_movement_for_joint(self, joint: str) -> Optional[str]:
        """Map joint to typical movement (for safe range key)."""
        jbase = joint.replace("left_", "").replace("right_", "")
        for mov, ranges in DEFAULT_SAFE_RANGES.items():
            for rj in ranges.keys():
                if jbase in rj or rj in jbase:
                    return mov
        if "knee" in joint:
            return "squat"
        if "elbow" in joint or "shoulder" in joint:
            return "throw"
        if "hip" in joint:
            return "squat"
        return "static"

    def _get_current_safe_range(self, movement: str, joint: str) -> Optional[Tuple[float, float]]:
        """Get current range from overrides or defaults."""
        overrides = self._store.get_safe_ranges_overrides()
        key = f"{movement}__{joint}"
        if key in overrides:
            o = overrides[key]
            return (o["min"], o["max"])
        jbase = joint.replace("left_", "").replace("right_", "")
        if "knee" in jbase and movement in DEFAULT_SAFE_RANGES and "knee" in DEFAULT_SAFE_RANGES[movement]:
            return DEFAULT_SAFE_RANGES[movement]["knee"]
        if "hip" in jbase and movement in DEFAULT_SAFE_RANGES and "hip" in DEFAULT_SAFE_RANGES[movement]:
            return DEFAULT_SAFE_RANGES[movement]["hip"]
        if "elbow" in jbase and movement in DEFAULT_SAFE_RANGES and "elbow" in DEFAULT_SAFE_RANGES[movement]:
            return DEFAULT_SAFE_RANGES[movement]["elbow"]
        return None

    def _compute_weight_updates(self) -> Dict[str, float]:
        """
        Increase weights for frequently occurring errors (top 3).
        """
        error_counts = self._store.get_error_counts()
        if not error_counts:
            return {}

        total = sum(error_counts.values())
        if total < 5:
            return {}

        sorted_errors = sorted(error_counts.items(), key=lambda x: -x[1])[:5]
        weights = dict(DEFAULT_WEIGHTS)
        for i, (err_key, count) in enumerate(sorted_errors):
            if err_key in weights:
                boost = 5 * (3 - i) if i < 3 else 0
                weights[err_key] = min(30, DEFAULT_WEIGHTS.get(err_key, 5) + boost)
        return weights

    def _find_unmapped_errors(self) -> List[str]:
        """Find errors that don't have coaching advice yet."""
        counts = self._store.get_error_counts()
        additions = self._store.get_coaching_advice_additions()
        known = set(ERROR_COACHING_MAP.keys()) | set(additions.keys())
        return [k for k in counts if k not in known and counts[k] >= 2]


def _default_advice_for_error(err_key: str) -> Tuple[str, List[str]]:
    """Generic advice for unknown errors."""
    return (
        "Focus on correct form and gradual improvement. Practice slow, controlled movements. Consider professional coaching for sport-specific feedback.",
        [],
    )
