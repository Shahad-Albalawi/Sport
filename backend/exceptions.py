"""Custom exceptions for Sports Movement Analysis API.

Professional error handling with consistent structure.
"""

from typing import Any, Dict, Optional


class SportAnalysisError(Exception):
    """Base exception for sport analysis errors."""

    def __init__(self, message: str, code: str = "ANALYSIS_ERROR", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


class VideoSourceError(SportAnalysisError):
    """Video source invalid or unreachable."""

    def __init__(self, message: str, source: Optional[str] = None):
        super().__init__(message, code="VIDEO_SOURCE_ERROR", details={"source": source})


class AnalysisTimeoutError(SportAnalysisError):
    """Analysis exceeded time limit."""

    def __init__(self, message: str = "Analysis timed out"):
        super().__init__(message, code="TIMEOUT")
