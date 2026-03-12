"""Pydantic schemas for API request/response validation."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class UploadResponse(BaseModel):
    """Response after uploading a video file."""

    path: str
    filename: str


class SportItem(BaseModel):
    """A sport in the sports list (English only)."""

    id: str
    name: str


class SportsListResponse(BaseModel):
    """Response listing supported sports."""

    sports: List[SportItem]


class AnalyzeRequest(BaseModel):
    """Request body for starting analysis."""

    source: Optional[str] = Field(None, description="Path to uploaded video file")
    sport: str = Field(..., min_length=1, description="Sport ID (required)")
    use_camera: bool = Field(False, description="Use webcam as source")


class AnalyzeResponse(BaseModel):
    """Response when analysis is started."""

    job_id: str
    status: str = "started"


class StopResponse(BaseModel):
    """Response when stop is requested."""

    status: str = "stop requested"


class ProgressInfo(BaseModel):
    """Progress update during analysis."""

    frame: int = 0
    total: int = 0
    msg: str = ""


class JobStatusResponse(BaseModel):
    """Job status and result (flexible schema for various states)."""

    model_config = ConfigDict(extra="allow")

    status: str
    result: Optional[Dict[str, Any]] = None
    progress: Optional[Any] = None
    error: Optional[str] = None
