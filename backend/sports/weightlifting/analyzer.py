"""
Weightlifting movement analyzer.

Based on IWF Technical Rules, USA Weightlifting coaching standards.
Evaluates: snatch, clean & jerk, squat, deadlift.
"""

from typing import Dict, List, Tuple

from backend.sports.base import MovementDefinition, SportAnalyzer
from backend.sources import get_sources_for_sport


class WeightliftingAnalyzer(SportAnalyzer):
    """
    Weightlifting / Strength training analysis module.

    Sources: IWF Technical Rules, USA Weightlifting.
    """

    SPORT_ID = "weightlifting"
    NAME_EN = "Weightlifting / Strength"

    MOVEMENTS = [
        MovementDefinition("snatch", "Snatch", "throw", "الخطف"),
        MovementDefinition("clean_jerk", "Clean & Jerk", "throw", "الالتقاط والنتر"),
        MovementDefinition("squat", "Squat", "squat", "القرفصاء"),
        MovementDefinition("deadlift", "Deadlift", "squat", "الرفعة المميتة"),
    ]

    IDEAL_ANGLES = {
        "knee_squat": (70, 110),
        "hip_squat": (60, 100),
        "knee_lunge": (70, 120),
        "hip_hinge": (60, 100),
    }

    CRITICAL_ERRORS = ["knee_valgus", "poor_hip_extension", "shoulder_imbalance"]

    COACHING_TIPS = {
        "knee_valgus": "Push knees out over toes in squat.",
        "poor_hip_extension": "Drive hips through at lockout.",
        "shoulder_imbalance": "Keep barbell path vertical; symmetric pull.",
    }

    DEVELOPMENT_PLAN = [
        "Phase 1: Mobility - bodyweight squat and hinge",
        "Phase 2: Bar path and spinal alignment",
        "Phase 3: Progressive load",
        "Phase 4: Strength program (e.g. 5x5)",
        "Phase 5: Max weights and competition",
    ]

    EXERCISES = [
        {"name": "Wall sit", "target": "knee", "reason": "Knee tracking"},
        {"name": "Hip bridge", "target": "hip", "reason": "Hip drive for squat"},
        {"name": "Plank", "target": "core", "reason": "Core bracing"},
    ]

    RELEVANT_OBJECTS = {"barbell"}

    @property
    def sport_id(self) -> str:
        return self.SPORT_ID

    @property
    def name_en(self) -> str:
        return self.NAME_EN

    def get_movements(self) -> List[MovementDefinition]:
        return list(self.MOVEMENTS)

    def get_key_joints(self) -> List[str]:
        return ["knees", "hips", "shoulders", "core"]

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
