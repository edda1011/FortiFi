from fastapi import APIRouter, Header, HTTPException

from app.schemas.auth import NonceRequest, NonceResponse, SessionResponse, VerifyRequest
from app.services.auth_service import AuthError, auth_service


router = APIRouter()


def optional_wallet(authorization: str | None = Header(default=None)) -> str | None:
    if authorization is None:
        return None
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Connect and sign in with your Base wallet.")
    address = auth_service.address_for_token(authorization.removeprefix("Bearer "))
    if address is None:
        raise HTTPException(status_code=401, detail="Your wallet session expired. Connect and sign in again.")
    return address


def require_wallet(authorization: str | None = Header(default=None)) -> str:
    address = optional_wallet(authorization)
    if address is None:
        raise HTTPException(status_code=401, detail="Connect and sign in with your Base wallet.")
    return address


@router.post("/nonce", response_model=NonceResponse)
def nonce(request: NonceRequest):
    try:
        address, message = auth_service.issue_nonce(request.address)
        return NonceResponse(address=address, message=message)
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/verify", response_model=SessionResponse)
def verify(request: VerifyRequest):
    try:
        token = auth_service.verify(request.address, request.signature)
        return SessionResponse(address=auth_service.normalize(request.address), token=token)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
