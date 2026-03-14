"""
Basketball movement analyzer.

Based on FIBA Coaching Manual, Journal of Athletic Training.
Evaluates: shooting, passing, dribbling, layup, rebound, defense, footwork, jump shot.
"""

from typing import Dict, List, Tuple

from backend.sports.base import MovementDefinition, SportAnalyzer
from backend.sources import get_sources_for_sport


class BasketballAnalyzer(SportAnalyzer):
    """
    Basketball analysis module.

    Sources: FIBA Coaching Manual, Jump Landing Mechanics.
    """

    SPORT_ID = "basketball"
    NAME_EN = "Basketball"

    MOVEMENTS = [
        MovementDefinition("shooting", "Shooting", "throw", "التصويب"),
        MovementDefinition("passing", "Passing", "throw", "التمرير"),
        MovementDefinition("dribbling", "Dribbling", "sprint", "المراوغة"),
        MovementDefinition("layup", "Layup", "jump", "الرمية السهلة"),
        MovementDefinition("rebound", "Rebound", "jump", "الارتداد"),
        MovementDefinition("defense", "Defense", "lunge", "الدفاع"),
        MovementDefinition("footwork", "Footwork", "lunge", "حركة الأقدام"),
        MovementDefinition("jump_shot", "Jump Shot", "jump", "التصويب بالقفز"),
    ]

    IDEAL_ANGLES = {
        "knee_jump": (140, 170),
        "elbow_shoot": (80, 100),
        "knee_landing": (140, 170),
        "knee_lunge": (70, 120),
    }

    CRITICAL_ERRORS = ["knee_valgus", "unstable_landing", "shoulder_imbalance"]

    COACHING_TIPS = {
        "knee_valgus": "Land with knees over toes; avoid inward collapse.",
        "unstable_landing": "Practice soft landings with bent knees.",
        "shoulder_imbalance": "Keep shooting elbow aligned; follow through.",
    }

    DEVELOPMENT_PLAN = [
        "Phase 1: Ball handling and warm-up",
        "Phase 2: Shooting form - arm and hand positioning",
        "Phase 3: Jump and safe landing mechanics",
        "Phase 4: Dribbling and agility",
        "Phase 5: Team play and competition",
    ]

    EXERCISES = [
        {"name": "Squat jump", "target": "knee", "reason": "Jump power and landing"},
        {"name": "Single-leg stance", "target": "ankle", "reason": "Agility stability"},
        {"name": "Wall sit", "target": "knee", "reason": "Knee protection on landing"},
    ]

    RELEVANT_OBJECTS = {"ball", "sports_ball", "orange_basketball"}

    @property
    def sport_id(self) -> str:
        return self.SPORT_ID

    @property
    def name_en(self) -> str:
        return self.NAME_EN

    def get_movements(self) -> List[MovementDefinition]:
        return list(self.MOVEMENTS)

    def get_key_joints(self) -> List[str]:
        return ["knees", "ankles", "shoulders", "elbows"]

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
