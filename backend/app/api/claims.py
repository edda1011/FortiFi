from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import optional_wallet, require_wallet

from app.schemas.analysis import (
    ClaimAnalysisRequest,
    ClaimAnalysisResponse,
    DeletedHistorySummary,
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
    owner_address: str | None = Depends(optional_wallet),
):
    try:
        return await claim_service.analyze(
            request.claim,
            owner_address,
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
async def create_analysis_job(
    request: AnalysisJobRequest,
    owner_address: str | None = Depends(optional_wallet),
):
    claim = request.claim.strip()
    if not claim:
        raise HTTPException(status_code=400, detail="Claim cannot be empty.")
    return analysis_job_service.create(
        claim=claim,
        wait_for_all=request.wait_for_all,
        owner_address=owner_address,
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
async def claim_history(
    limit: int = 10,
    owner_address: str = Depends(require_wallet),
):
    """List recent completed analyses."""
    return history_service.list(owner_address, limit)


@router.post(
    "/history-match",
    response_model=HistoryDetail | None,
)
async def recent_claim_match(
    request: ClaimAnalysisRequest,
    owner_address: str = Depends(require_wallet),
):
    """Return an identical analysis saved by this wallet within 24 hours."""
    return history_service.find_recent_claim(owner_address, request.claim)


@router.get("/history-trash", response_model=list[DeletedHistorySummary])
async def claim_history_trash(
    limit: int = 50,
    owner_address: str = Depends(require_wallet),
):
    return history_service.list_trash(owner_address, limit)


@router.delete("/history/{analysis_id}")
async def delete_claim_history(
    analysis_id: str,
    owner_address: str = Depends(require_wallet),
):
    try:
        history_service.delete(analysis_id, owner_address)
        return {"status": "trashed", "retention_days": 30}
    except HistoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/history/{analysis_id}/restore")
async def restore_claim_history(
    analysis_id: str,
    owner_address: str = Depends(require_wallet),
):
    try:
        history_service.restore(analysis_id, owner_address)
        return {"status": "restored"}
    except HistoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/history/{analysis_id}/permanent")
async def permanently_delete_claim_history(
    analysis_id: str,
    owner_address: str = Depends(require_wallet),
):
    try:
        history_service.permanently_delete(analysis_id, owner_address)
        return {"status": "deleted"}
    except HistoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/history/{analysis_id}",
    response_model=HistoryDetail,
)
async def claim_history_detail(
    analysis_id: str,
    owner_address: str = Depends(require_wallet),
):
    try:
        return history_service.get(analysis_id, owner_address)
    except HistoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/history/{analysis_id}/follow-up",
    response_model=FollowUpEntry,
)
async def claim_follow_up(
    analysis_id: str,
    request: FollowUpRequest,
    owner_address: str = Depends(require_wallet),
):
    try:
        question = request.question.strip()
        if not question:
            raise ValueError("Follow-up question cannot be empty.")
        return await history_service.answer_follow_up(
            analysis_id=analysis_id,
            owner_address=owner_address,
            question=question,
        )
    except HistoryNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
