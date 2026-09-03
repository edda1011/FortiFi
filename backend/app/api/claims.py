from fastapi import APIRouter, HTTPException

from app.schemas.analysis import (
    ClaimAnalysisRequest,
    ClaimAnalysisResponse,
    FollowUpEntry,
    FollowUpRequest,
    HistoryDetail,
    HistorySummary,
)
from app.schemas.analysis_job import AnalysisJobRequest, AnalysisJobResponse
from app.services.analysis_job_service import (
    AnalysisJobNotFoundError,
    AnalysisJobService,
)
from app.services.claim_service import ClaimService
from app.services.history_service import HistoryNotFoundError, HistoryService


router = APIRouter(
    tags=["Claims"],
)

claim_service = ClaimService()
history_service = HistoryService()
analysis_job_service = AnalysisJobService()


@router.post(
    "/analyze",
    response_model=ClaimAnalysisResponse,
)
async def analyze_claim(
    request: ClaimAnalysisRequest,
):
    try:
        return await claim_service.analyze(
            request.claim
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@router.post(
    "/analysis-jobs",
    response_model=AnalysisJobResponse,
    status_code=202,
)
async def create_analysis_job(request: AnalysisJobRequest):
    claim = request.claim.strip()
    if not claim:
        raise HTTPException(status_code=400, detail="Claim cannot be empty.")
    return analysis_job_service.create(
        claim=claim,
        wait_for_all=request.wait_for_all,
    )


@router.get(
    "/analysis-jobs/{job_id}",
    response_model=AnalysisJobResponse,
)
async def get_analysis_job(job_id: str):
    try:
        return analysis_job_service.get(job_id)
    except AnalysisJobNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/history",
    response_model=list[HistorySummary],
)
async def claim_history(limit: int = 10):
    """List recent completed analyses."""
    return history_service.list(limit)


@router.get(
    "/history/{analysis_id}",
    response_model=HistoryDetail,
)
async def claim_history_detail(analysis_id: str):
    try:
        return history_service.get(analysis_id)
    except HistoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/history/{analysis_id}/follow-up",
    response_model=FollowUpEntry,
)
async def claim_follow_up(analysis_id: str, request: FollowUpRequest):
    try:
        question = request.question.strip()
        if not question:
            raise ValueError("Follow-up question cannot be empty.")
        return await history_service.answer_follow_up(
            analysis_id=analysis_id,
            question=question,
        )
    except HistoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
