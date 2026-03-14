"""
Tennis movement analyzer.

Based on ITF coaching standards, USTA Player Development.
Evaluates: serve, forehand, backhand, volley, court movement.
"""

from typing import Dict, List, Tuple

from backend.sports.base import MovementDefinition, SportAnalyzer
from backend.sources import get_sources_for_sport


class TennisAnalyzer(SportAnalyzer):
    """
    Tennis analysis module.

    Sources: ITF Coaching, USTA Player Development.
    """

    SPORT_ID = "tennis"
    NAME_EN = "Tennis"

    MOVEMENTS = [
        MovementDefinition("serve", "Serve", "throw", "الإرسال"),
        MovementDefinition("forehand", "Forehand", "swing", "الضربة الأمامية"),
        MovementDefinition("backhand", "Backhand", "swing", "الضربة الخلفية"),
        MovementDefinition("volley", "Volley", "swing", "الضربة الطائرة"),
        MovementDefinition("movement", "Court Movement", "sprint", "التحرك في الملعب"),
    ]

    IDEAL_ANGLES = {
        "elbow_swing": (90, 150),
        "shoulder_swing": (60, 120),
        "hip_rotation": (30, 90),
        "elbow_throw": (90, 140),
    }

    CRITICAL_ERRORS = ["shoulder_imbalance", "limited_rotation", "elbow_alignment"]

    COACHING_TIPS = {
        "shoulder_imbalance": "Rotate shoulders through the stroke.",
        "limited_rotation": "Drive from hips and core; unit turn.",
        "elbow_alignment": "Keep elbow in front; avoid dropping.",
    }

    DEVELOPMENT_PLAN = [
        "Phase 1: Grip and ready position",
        "Phase 2: Groundstrokes - forehand and backhand",
        "Phase 3: Timing and shoulder-hip rotation",
        "Phase 4: Serve and volley",
        "Phase 5: Tactics and court positioning",
    ]

    EXERCISES = [
        {"name": "Band pull-apart", "target": "shoulder", "reason": "Posterior shoulder strength"},
        {"name": "Seated torso twist", "target": "core", "reason": "Rotation for strokes"},
        {"name": "Rotator cuff exercises", "target": "shoulder", "reason": "Injury prevention"},
    ]

    RELEVANT_OBJECTS = {"racket", "tennis_racket", "ball", "sports_ball", "yellow_tennis"}

    @property
    def sport_id(self) -> str:
        return self.SPORT_ID

    @property
    def name_en(self) -> str:
        return self.NAME_EN

    def get_movements(self) -> List[MovementDefinition]:
        return list(self.MOVEMENTS)

    def get_key_joints(self) -> List[str]:
        return ["shoulders", "elbows", "hips", "core"]

    def get_ideal_angles(self) -> Dict[str, Tuple[float, float]]:
        return dict(self.IDEAL_ANGLES)

    def get_critical_errors(self) -> List[str]:
        return list(self.CRITICAL_ERRORS)

    def get_coaching_tips(self) -> Dict[str, str]:
        return dict(self.COACHING_TIPS)

    def get_development_plan(self) -> List[str]:
        return list(self.DEVELOPMENT_PLAN)

    def get_exercises(self) -> List[Dict[str, str]]:
        return list(self.EXERCISES)

    def get_sources(self) -> List[Dict[str, str]]:
        return get_sources_for_sport(self.SPORT_ID)

    def get_relevant_objects(self) -> set:
        return set(self.RELEVANT_OBJECTS)
