"""
Football (Soccer) movement analyzer.

Based on FIFA guidelines, biomechanics research, and coaching standards.
Evaluates: shooting, passing, dribbling, sprinting, cutting, juggling, jumping header.
"""

from typing import Any, Dict, List, Tuple

from backend.sports.base import MovementDefinition, SportAnalyzer
from backend.sources import get_sources_for_sport


class FootballAnalyzer(SportAnalyzer):
    """
    Football/Soccer analysis module.

    Sources: FIFA Football Medicine Manual, British Journal of Sports Medicine.
    """

    SPORT_ID = "football"
    NAME_EN = "Football (Soccer)"

    MOVEMENTS = [
        MovementDefinition("ball_striking", "Ball Striking", "kick", "ضرب الكرة"),
        MovementDefinition("dribbling", "Dribbling", "sprint", "المراوغة"),
        MovementDefinition("passing", "Passing", "kick", "التمرير"),
        MovementDefinition("shooting", "Shooting", "kick", "التصويب"),
        MovementDefinition("sprinting", "Sprinting", "sprint", "الجري السريع"),
        MovementDefinition("cutting", "Cutting", "lunge", "تغيير الاتجاه"),
        MovementDefinition("juggling", "Juggling", "kick", "السيطرة الهوائية"),
        MovementDefinition("jump_header", "Jumping Header", "jump", "ضربة الرأس بالقفز"),
    ]

    IDEAL_ANGLES = {
        "knee_kick": (140, 180),
        "knee_sprint": (155, 175),
        "hip_kick": (80, 120),
        "knee_jump": (140, 170),
        "hip_lunge": (80, 120),
    }

    CRITICAL_ERRORS = ["knee_valgus", "poor_hip_extension", "ankle_instability"]

    COACHING_TIPS = {
        "knee_valgus": "Keep knees aligned over toes during striking and landing.",
        "poor_hip_extension": "Drive through the hip for power in kicks and sprints.",
        "ankle_instability": "Strengthen ankles with single-leg balance drills.",
    }

    DEVELOPMENT_PLAN = [
        "Phase 1: Ball control and warm-up basics",
        "Phase 2: Passing accuracy at various distances",
        "Phase 3: Shooting - focus on hip and knee angles",
        "Phase 4: Agility and speed training",
        "Phase 5: Tactics and team play",
    ]

    EXERCISES = [
        {"name": "Clam shells", "target": "hip", "reason": "Glute strength for kick control"},
        {"name": "Single-leg balance", "target": "ankle", "reason": "Plant foot stability"},
        {"name": "Hip flexor stretch", "target": "hip", "reason": "Range of motion for kicking"},
    ]

    RELEVANT_OBJECTS = {
        "ball", "sports_ball", "orange_basketball", "yellow_tennis",
        "white_ball", "green_ball",
    }

    @property
    def sport_id(self) -> str:
        return self.SPORT_ID

    @property
    def name_en(self) -> str:
        return self.NAME_EN

    def get_movements(self) -> List[MovementDefinition]:
        return list(self.MOVEMENTS)

    def get_key_joints(self) -> List[str]:
        return ["left_knee", "right_knee", "left_hip", "right_hip", "ankles"]

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
