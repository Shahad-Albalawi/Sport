"""
Sport-specific analysis modules.

Each sport has its own independent module with:
- Sport-specific movement evaluation
- Sport-specific skills and techniques
- Official sources (FIFA, ITF, FIBA, etc.)

Unified output structure for mobile/web integration.
"""

from backend.sports.base import (
    SportAnalyzer,
    MovementDefinition,
    MovementEvaluationResult,
    SportAnalysisOutput,
)
from backend.sports.registry import get_analyzer, get_registered_sports

# Aliases for backward compatibility
get_sport_analyzer = get_analyzer
list_registered_sports = get_registered_sports

__all__ = [
    "SportAnalyzer",
    "MovementDefinition",
    "MovementEvaluationResult",
    "SportAnalysisOutput",
    "get_analyzer",
    "get_sport_analyzer",
    "get_registered_sports",
    "list_registered_sports",
]
