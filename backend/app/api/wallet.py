from fastapi import APIRouter, HTTPException

from app.schemas.wallet import WalletCheckRequest, WalletCheckResponse
from app.services.wallet_service import (
    InvalidAddressError,
    WalletService,
    WalletUnavailableError,
)


router = APIRouter(
    tags=["Wallet"],
)

wallet_service = WalletService()


@router.post(
    "/check",
    response_model=WalletCheckResponse,
)
async def check_wallet(
    request: WalletCheckRequest,
):
    try:
        return await wallet_service.check(request.address)

    except InvalidAddressError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except WalletUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc
