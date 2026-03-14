"""
Base classes for sport-specific analysis modules.

Every sport implements SportAnalyzer with:
- Movement definitions (skills/techniques)
- Ideal angles and criteria
- Error detection and coaching tips
- Official sources
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class MovementDefinition:
    """Defines a skill/movement that can be evaluated."""

    id: str
    name_en: str
    generic: str  # Maps to: kick, jump, sprint, punch, swing, throw, squat, lunge, rotation, static
    name_ar: str = ""


@dataclass
class MovementEvaluationResult:
    """Result of evaluating one movement (detailed for mobile/app)."""

    movement_id: str
    movement_name: str
    score: float
    strengths: List[str]
    errors: List[str]
    improvement_advice: str
    joint_angles: Optional[Dict[str, float]] = None
    skill_metrics: Optional[Dict[str, float]] = None


@dataclass
class SportAnalysisOutput:
    """Unified output structure for API/mobile integration."""

    sport_id: str
    sport_name: str
    overall_score: float
    movements: List[Dict[str, Any]]
    strengths: List[str]
    errors: List[str]
    feedback: List[Dict[str, str]]
    recommendations: List[Dict[str, Any]]
    development_plan: List[str]
    sources: List[Dict[str, str]]


class SportAnalyzer(ABC):
    """
    Base class for sport-specific analysis.

    Each sport implements:
    - sport_id, name_en
    - get_movements()
    - get_profile() for backward compatibility with evaluator
    - get_sources()
    """

    @property
    @abstractmethod
    def sport_id(self) -> str:
        """Unique sport identifier (e.g. 'football', 'tennis')."""
        pass

    @property
    @abstractmethod
    def name_en(self) -> str:
        """Display name in English."""
        pass

    @abstractmethod
    def get_movements(self) -> List[MovementDefinition]:
        """Return list of evaluable skills/movements."""
        pass

    def get_profile(self) -> Dict[str, Any]:
        """
        Return full profile dict compatible with backend.analysis.sport_profiles.
        Used by MovementEvaluator and RecommendationEngine.
        """
        movements = self.get_movements()
        tech_movements = [
            {
                "id": m.id,
                "name_en": m.name_en,
                "name_ar": m.name_ar or m.name_en,
                "generic": m.generic,
            }
            for m in movements
        ]
        return {
            "name": self.name_en,
            "name_en": self.name_en,
            "technical_movements": tech_movements,
            "key_joints": self.get_key_joints(),
            "ideal_angles": self.get_ideal_angles(),
            "critical_errors": self.get_critical_errors(),
            "coaching_tips": self.get_coaching_tips(),
            "development_plan": self.get_development_plan(),
            "exercises": self.get_exercises(),
        }

    @abstractmethod
    def get_key_joints(self) -> List[str]:
        """Joints most important for this sport."""
        pass

    @abstractmethod
    def get_ideal_angles(self) -> Dict[str, Tuple[float, float]]:
        """Ideal angle ranges (min, max) degrees by key."""
        pass

    @abstractmethod
    def get_critical_errors(self) -> List[str]:
        """Sport-specific errors to detect."""
        pass

    @abstractmethod
    def get_coaching_tips(self) -> Dict[str, str]:
        """Error -> coaching tip mapping."""
        pass

    def get_development_plan(self) -> List[str]:
        """Phased development plan."""
        return []

    def get_exercises(self) -> List[Dict[str, str]]:
        """Recommended corrective exercises."""
        return []

    def get_sources(self) -> List[Dict[str, str]]:
        """Official sources (FIFA, ITF, etc.)."""
        return []

    def get_relevant_objects(self) -> set:
        """Object labels relevant for this sport (ball, racket, etc.)."""
        return set()
