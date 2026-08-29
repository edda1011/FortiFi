from fastapi import APIRouter, HTTPException

from app.schemas.analysis import (
    ClaimAnalysisRequest,
    ConsensusAnalysis,
)
from app.services.claim_service import ClaimService


router = APIRouter(
    tags=["Claims"],
)

claim_service = ClaimService()


@router.post(
    "/analyze",
    response_model=ConsensusAnalysis,
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