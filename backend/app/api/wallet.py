from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.auth import require_wallet
from app.database.database import get_session
from app.database.repositories.wallet_repository import WalletRepository
from app.schemas.wallet import (
    WalletCheckRequest,
    WalletCheckResponse,
    WalletExposureResponse,
    WalletHistoryResponse,
    WalletSnapshotResponse,
)
from app.services.wallet_service import (
    InvalidAddressError,
    NoSnapshotError,
    WalletService,
    WalletUnavailableError,
    get_current_exposure,
)


router = APIRouter(
    tags=["Wallet"],
)

wallet_service = WalletService()


def _snapshot_to_response(row) -> WalletSnapshotResponse:
    """Map an ORM WalletSnapshot row to its API response schema."""

    return WalletSnapshotResponse(
        id=row.id,
        address=row.wallet_address,
        network=row.network,
        eth_balance=row.eth_balance,
        eth_price=row.eth_price,
        eth_value=row.eth_value,
        usdc_balance=row.usdc_balance,
        total_value=row.total_value,
        eth_exposure_percent=row.eth_exposure_percent,
        created_at=row.created_at,
    )


@router.get(
    "/connected",
    response_model=WalletCheckResponse,
)
async def get_connected_wallet(
    owner_address: str = Depends(require_wallet),
):
    """Read the signed-in wallet's live balances without saving a snapshot."""
    try:
        return await wallet_service.check(owner_address, record_snapshot=False)
    except WalletUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


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


@router.get(
    "/{address}/latest",
    response_model=WalletSnapshotResponse,
)
async def get_wallet_latest(
    address: str,
):
    """
    Return the most recent saved snapshot for an address, or 404 if
    none exists yet. Plain read from the repository — no RPC calls,
    should respond fast even if Base RPC is down.
    """

    try:
        checksum_address = WalletService._validate_address(address)

    except InvalidAddressError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    with get_session() as db:
        repository = WalletRepository(db)
        snapshot = repository.get_latest(checksum_address)

    if snapshot is None:
        raise HTTPException(
            status_code=404,
            detail=f"No saved snapshot exists for {checksum_address} yet.",
        )

    return _snapshot_to_response(snapshot)


@router.get(
    "/{address}/history",
    response_model=WalletHistoryResponse,
)
async def get_wallet_history(
    address: str,
    limit: int = Query(default=20, ge=1, le=100),
):
    """
    Return past snapshots for an address, most recent first.
    Plain read from the repository — no RPC calls.
    """

    try:
        checksum_address = WalletService._validate_address(address)

    except InvalidAddressError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    with get_session() as db:
        repository = WalletRepository(db)
        snapshots = repository.list_by_address(checksum_address, limit=limit)

    return WalletHistoryResponse(
        address=checksum_address,
        snapshots=[_snapshot_to_response(s) for s in snapshots],
    )


@router.get(
    "/{address}/exposure",
    response_model=WalletExposureResponse,
)
async def get_wallet_exposure(
    address: str,
):
    """
    Return the current ETH exposure for an address, derived from the
    latest saved snapshot. This is the input the Risk Engine consumes
    (spec section 23: exposure = ETH value).
    """

    try:
        checksum_address = WalletService._validate_address(address)

    except InvalidAddressError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    try:
        return get_current_exposure(checksum_address)

    except NoSnapshotError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc
