from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.analysis import ClaimAnalysisResponse


JobStatus = Literal["queued", "running", "completed", "failed"]
ModelStatus = Literal["pending", "analyzing", "completed", "failed", "timed_out", "cancelled"]


class AnalysisJobRequest(BaseModel):
    claim: str = Field(min_length=1, max_length=10000)
    wait_for_all: bool = False


class ModelProgress(BaseModel):
    model: str
    status: ModelStatus = "pending"
    error: str | None = None


class AnalysisJobResponse(BaseModel):
    job_id: str
    status: JobStatus
    phase: str
    wait_for_all: bool
    models: list[ModelProgress]
    result: ClaimAnalysisResponse | None = None
    error: str | None = None
