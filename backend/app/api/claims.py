from fastapi import APIRouter, HTTPException

from app.schemas.analysis import (
    ClaimAnalysisRequest,
    ClaimAnalysisResponse,
)
from app.services.analysis_store import AnalysisStore
from app.services.claim_service import ClaimService


router = APIRouter(
    tags=["Claims"],
)

claim_service = ClaimService()


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


@router.get(
    "/history",
    response_model=list[ClaimAnalysisResponse],
)
async def claim_history(limit: int = 10):
    """Recent completed analyses, including the evidence package used."""
    return AnalysisStore().recent(limit=max(1, min(limit, 50)))
