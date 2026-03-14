"""
Unified output schema for all sports.

Ensures consistent structure for mobile and web integration.
Based on: technique quality, body alignment, joint angles, balance, coordination.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class MovementSkillResult:
    """Evaluation result for a single skill/movement."""

    movement_id: str
    movement_name: str
    score: float  # 0-10
    frames_count: int
    strengths: List[str]
    errors: List[str]
    improvement_advice: str
    joint_scores: Optional[Dict[str, float]] = None
    skill_metrics: Optional[Dict[str, float]] = None  # balance, coordination, etc.


@dataclass
class MovementEvaluation:
    """Unified movement result for API/mobile."""

    movement_name: str
    performance_score: float
    strengths: List[str]
    detected_errors: List[str]
    improvement_advice: str
    frames_count: int = 0
    feedback: str = ""


@dataclass
class SportOutput:
    """Unified sport analysis output for API/mobile integration."""

    sport_id: str
    sport_name: str
    overall_score: float
    total_frames: int
    movements: List[MovementEvaluation]
    strengths: List[str]
    detected_errors: List[str]
    coaching_feedback: List[Dict[str, str]]
    recommendations: List[Dict[str, Any]]
    development_plan: List[str]
    object_tracking: List[Dict] = field(default_factory=list)
    report_files: Dict[str, str] = field(default_factory=dict)
    output_video_path: Optional[str] = None


@dataclass
class SportAnalysisOutput:
    """
    Unified analysis output for all sports.

    Used by API, reports, and mobile app.
    """

    sport_id: str
    sport_name: str
    overall_score: float  # 0-10
    movements_analyzed: List[Dict[str, Any]]  # List of MovementSkillResult-like dicts
    strengths: List[str]
    errors: List[str]
    coaching_feedback: List[Dict[str, str]]
    recommendations: List[Dict[str, Any]]
    development_plan: List[str]
    total_frames: int
    sources: List[Dict[str, str]] = field(default_factory=list)
    # Optional extras
    object_tracking: List[Dict] = field(default_factory=list)
    frame_evaluations: List[Dict] = field(default_factory=list)

    def to_api_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict for API response."""
        return {
            "sport": self.sport_id,
            "sport_name": self.sport_name,
            "sport_name_en": self.sport_name,
            "overall_score": round(self.overall_score, 1),
            "movements_analyzed": self.movements_analyzed,
            "strengths": self.strengths,
            "errors": self.errors,
            "coaching_feedback": self.coaching_feedback,
            "recommendations": self.recommendations,
            "development_plan": self.development_plan,
            "total_frames": self.total_frames,
            "object_tracking": self.object_tracking,
            "frame_evaluations": self.frame_evaluations,
        }
