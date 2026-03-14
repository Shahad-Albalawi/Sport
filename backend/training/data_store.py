"""
Training data store for sport-specific modules.

Stores collected features, scores, errors per video and movement.
Data is kept per sport — no mixing between sports.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.config import TRAINING_DATA_DIR

logger = logging.getLogger("sport_analysis.training")


def get_sport_training_dir(sport_id: str) -> Path:
    """Get training data directory for a sport."""
    sport_id = (sport_id or "unknown").lower().strip()
    path = TRAINING_DATA_DIR / sport_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_sport_training_data(sport_id: str) -> Dict[str, Any]:
    """
    Load aggregated training data for a sport.
    Returns dict with videos, movements, error_counts, safe_ranges_overrides, etc.
    """
    path = get_sport_training_dir(sport_id) / "training_data.json"
    if not path.exists():
        return _empty_training_data(sport_id)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load training data for %s: %s", sport_id, e)
        return _empty_training_data(sport_id)


def _empty_training_data(sport_id: str) -> Dict[str, Any]:
    return {
        "sport_id": sport_id,
        "version": 1,
        "created_at": None,
        "updated_at": None,
        "videos_processed": 0,
        "videos": [],
        "movements": {},
        "error_counts": {},
        "joint_angle_samples": {},
        "safe_ranges_overrides": {},
        "injury_risk_weights_overrides": {},
        "coaching_advice_additions": {},
    }


class TrainingDataStore:
    """
    Store and retrieve sport-specific training data.
    Ensures data isolation — no cross-sport contamination.
    """

    def __init__(self, sport_id: str):
        self.sport_id = (sport_id or "unknown").lower().strip()
        self._dir = get_sport_training_dir(self.sport_id)
        self._data = load_sport_training_data(self.sport_id)

    def add_video_result(
        self,
        video_path: str,
        total_frames: int,
        movement_summaries: List[Dict[str, Any]],
        frame_samples: List[Dict[str, Any]],
        error_list: List[str],
    ) -> None:
        """Append results from one video to training data."""
        videos = self._data.setdefault("videos", [])
        videos.append({
            "path": str(video_path),
            "processed_at": datetime.now().isoformat(),
            "total_frames": total_frames,
            "movement_count": len(movement_summaries),
            "error_count": len(error_list),
        })
        self._data["videos_processed"] = len(videos)

        movements = self._data.setdefault("movements", {})
        for m in movement_summaries:
            mov_id = m.get("id", m.get("movement_id", "unknown"))
            if mov_id not in movements:
                movements[mov_id] = {"scores": [], "injury_risks": [], "frames": 0, "errors": []}
            movements[mov_id]["scores"].append(m.get("score", m.get("avg_score", 0)))
            movements[mov_id]["injury_risks"].append(m.get("injury_risk_score", 0))
            movements[mov_id]["frames"] += m.get("frames_count", 0)
            movements[mov_id]["errors"].extend(m.get("errors", []) or [])

        error_counts = self._data.setdefault("error_counts", {})
        for err in error_list:
            err_key = err.lower().replace(" ", "_").split("(")[0].strip("_")
            if not err_key:
                continue
            error_counts[err_key] = error_counts.get(err_key, 0) + 1

        joint_samples = self._data.setdefault("joint_angle_samples", {})
        for samp in frame_samples[:100]:
            for joint, angle in samp.get("angles", {}).items():
                if joint not in joint_samples:
                    joint_samples[joint] = []
                joint_samples[joint].append(angle)
                if len(joint_samples[joint]) > 500:
                    joint_samples[joint] = joint_samples[joint][-500:]

        self._data["updated_at"] = datetime.now().isoformat()
        if not self._data.get("created_at"):
            self._data["created_at"] = self._data["updated_at"]
        self.save()

    def get_error_counts(self) -> Dict[str, int]:
        """Return error -> count for this sport."""
        return dict(self._data.get("error_counts", {}))

    def get_movement_stats(self) -> Dict[str, Dict[str, Any]]:
        """Return movement -> {scores, injury_risks, frames, errors}."""
        return dict(self._data.get("movements", {}))

    def get_joint_angle_samples(self) -> Dict[str, List[float]]:
        """Return joint -> list of observed angles."""
        return dict(self._data.get("joint_angle_samples", {}))

    def update_safe_ranges(self, movement: str, joint: str, min_deg: float, max_deg: float) -> None:
        """Store an override for safe range (from improvement engine)."""
        overrides = self._data.setdefault("safe_ranges_overrides", {})
        key = f"{movement}__{joint}"
        overrides[key] = {"min": min_deg, "max": max_deg}
        self._data["updated_at"] = datetime.now().isoformat()
        self.save()

    def update_injury_risk_weights(self, weights: Dict[str, float]) -> None:
        """Store injury risk weight overrides."""
        self._data["injury_risk_weights_overrides"] = dict(weights)
        self._data["updated_at"] = datetime.now().isoformat()
        self.save()

    def add_coaching_advice(self, error_key: str, advice: str, injuries: List[str]) -> None:
        """Add or update coaching advice for an error."""
        additions = self._data.setdefault("coaching_advice_additions", {})
        additions[error_key] = {"advice": advice, "injuries": injuries}
        self._data["updated_at"] = datetime.now().isoformat()
        self.save()

    def get_safe_ranges_overrides(self) -> Dict[str, Dict[str, float]]:
        """Return movement__joint -> {min, max} overrides."""
        return dict(self._data.get("safe_ranges_overrides", {}))

    def get_injury_risk_weights_overrides(self) -> Dict[str, float]:
        """Return error -> weight overrides."""
        return dict(self._data.get("injury_risk_weights_overrides", {}))

    def get_coaching_advice_additions(self) -> Dict[str, Dict[str, Any]]:
        """Return error_key -> {advice, injuries} additions."""
        return dict(self._data.get("coaching_advice_additions", {}))

    def save(self) -> None:
        """Persist training data to disk."""
        path = self._dir / "training_data.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
        logger.debug("Saved training data for %s to %s", self.sport_id, path)

    @property
    def data(self) -> Dict[str, Any]:
        return self._data
