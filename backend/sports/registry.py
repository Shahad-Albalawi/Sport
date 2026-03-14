"""
Sport registry: discover and load sport analyzer modules.

Provides a single entry point to get sport analyzers. Supports both:
- New modular sports (backend/sports/{sport}/)
- Legacy sport_profiles (fallback for backward compatibility)
"""

import logging
from typing import Dict, List, Optional

from backend.sports.base import SportAnalyzer
from backend.sports.schema import SportOutput, MovementEvaluation

logger = logging.getLogger("sport_analysis.registry")

# Registry: sport_id -> SportAnalyzer class or instance
_registry: Dict[str, SportAnalyzer] = {}
_initialized = False


# Sports with dedicated analyzer modules (extend as new modules are added)
IMPLEMENTED_SPORT_MODULES = [
    ("football", "backend.sports.football.analyzer", "FootballAnalyzer"),
    ("tennis", "backend.sports.tennis.analyzer", "TennisAnalyzer"),
    ("basketball", "backend.sports.basketball.analyzer", "BasketballAnalyzer"),
    ("weightlifting", "backend.sports.weightlifting.analyzer", "WeightliftingAnalyzer"),
    ("soccer", "backend.sports.football.analyzer", "FootballAnalyzer"),  # Alias
]


def _discover_sports() -> Dict[str, SportAnalyzer]:
    """Import and register sport analyzers. Only loads modules that exist."""
    sports: Dict[str, SportAnalyzer] = {}
    for sport_id, module_path, class_name in IMPLEMENTED_SPORT_MODULES:
        if sport_id == "soccer" and "football" in sports:
            sports["soccer"] = sports["football"]
            continue
        try:
            mod = __import__(module_path, fromlist=[class_name])
            cls = getattr(mod, class_name, None)
            if cls and issubclass(cls, SportAnalyzer):
                sports[sport_id] = cls()
                logger.debug("Registered sport: %s", sport_id)
        except ImportError as e:
            logger.debug("Sport %s not available: %s", sport_id, e)
    return sports


def _ensure_initialized():
    """Lazy-init the registry."""
    global _registry, _initialized
    if not _initialized:
        _registry = _discover_sports()
        _initialized = True


def get_analyzer(sport_id: str) -> Optional[SportAnalyzer]:
    """Get analyzer for sport. Returns None if sport uses legacy profiles."""
    _ensure_initialized()
    key = (sport_id or "").lower().strip().replace(" ", "_")
    return _registry.get(key)


def get_registered_sports() -> List[str]:
    """List sport IDs that have dedicated analyzer modules."""
    _ensure_initialized()
    return list(_registry.keys())


def has_modular_analyzer(sport_id: str) -> bool:
    """Check if sport has a dedicated module (vs legacy profile)."""
    return get_analyzer(sport_id) is not None


def normalize_to_unified_output(
    raw: dict,
    sport_id: str,
) -> SportOutput:
    """
    Convert pipeline raw output to unified SportOutput schema.
    Ensures consistent structure for mobile/web integration.
    """
    movements = []
    for m in raw.get("movements_analyzed", []) or []:
        movements.append(MovementEvaluation(
            movement_name=m.get("name_en") or m.get("name") or m.get("id", ""),
            performance_score=m.get("score", 0),
            strengths=m.get("strengths", []) or [],
            detected_errors=m.get("weaknesses", []) or [],
            improvement_advice=m.get("improvement_note", "") or "",
            frames_count=m.get("frames_count", 0),
            feedback=m.get("feedback", ""),
        ))
    return SportOutput(
        sport_id=sport_id,
        sport_name=raw.get("sport_name_en") or raw.get("sport", sport_id),
        overall_score=raw.get("overall_score", 0),
        total_frames=raw.get("total_frames", 0),
        movements=movements,
        strengths=raw.get("strengths", []) or [],
        detected_errors=raw.get("errors", []) or [],
        coaching_feedback=raw.get("coaching_feedback", []) or [],
        recommendations=raw.get("recommendations", []) or [],
        development_plan=raw.get("development_plan", []) or [],
        object_tracking=raw.get("object_tracking", []) or [],
        report_files=raw.get("report_files", {}),
        output_video_path=raw.get("output_video_path"),
    )
