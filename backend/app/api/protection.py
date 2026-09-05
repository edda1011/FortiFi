from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import require_wallet
from app.schemas.protection import (
    ProtectionPrepareRequest,
    ProtectionPrepareResponse,
    ProtectionRecordRequest,
    ProtectionRecordResponse,
)
from app.services.protection_service import ProtectionError, ProtectionService
from app.services.sui_service import SuiNotConfiguredError, SuiSubmissionError


router = APIRouter()
service = ProtectionService()


@router.get("/{analysis_id}/{record_type}", response_model=ProtectionRecordResponse | None)
def status(analysis_id: str, record_type: str, owner: str = Depends(require_wallet)):
    return service.status(analysis_id, owner, record_type)


@router.post("/prepare", response_model=ProtectionPrepareResponse)
def prepare(request: ProtectionPrepareRequest, owner: str = Depends(require_wallet)):
    try:
        canonical, report_hash, message = service.prepare(
            request.analysis_id, owner, request.record_type
        )
        return ProtectionPrepareResponse(
            canonical_report=canonical, report_hash=report_hash, message=message
        )
    except ProtectionError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/record", response_model=ProtectionRecordResponse)
def record(request: ProtectionRecordRequest, owner: str = Depends(require_wallet)):
    try:
        report_hash, digest, object_id = service.record(
            request.analysis_id, owner, request.signature, request.record_type
        )
        return ProtectionRecordResponse(
            record_type=request.record_type,
            report_hash=report_hash,
            sui_digest=digest,
            sui_object_id=object_id,
            explorer_url=f"https://suiscan.xyz/testnet/tx/{digest}",
            anchored_at=service.status(request.analysis_id, owner, request.record_type).anchored_at,
        )
    except ProtectionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SuiNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except SuiSubmissionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
