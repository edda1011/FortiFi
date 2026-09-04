import asyncio
import logging
from datetime import datetime
from decimal import Decimal

from eth_utils import (
    is_checksum_address,
    is_checksum_formatted_address,
    is_hex_address,
    to_checksum_address,
)

from app.config import settings
from app.database.database import get_session
from app.database.repositories.wallet_repository import WalletRepository
from app.integrations.base.client import BaseClient, BaseRpcError
from app.schemas.wallet import WalletCheckResponse, WalletExposureResponse
from app.services.state import app_state


logger = logging.getLogger(__name__)


class InvalidAddressError(ValueError):
    """Raised when a wallet address fails format/checksum validation."""


class WalletUnavailableError(RuntimeError):
    """Raised when Base can't be reached to read balances."""


class NoSnapshotError(LookupError):
    """Raised when no saved snapshot exists for an address yet."""


class WalletService:
    """
    Reads a public wallet's ETH + USDC balances from Base and turns
    them into a portfolio snapshot.

    This service is read-only end to end: it only calls public RPC
    "read" methods. It never sees, stores, or requests a private key
    or a seed phrase, and it never builds or signs a transaction.
    """

    def __init__(self) -> None:
        self.client = BaseClient(
            rpc_url=settings.base_rpc_url,
        )

    async def check(
        self,
        address: str,
        record_snapshot: bool = True,
    ) -> WalletCheckResponse:

        checksum_address = self._validate_address(address)

        eth_balance, usdc_balance = await self._read_balances(
            checksum_address
        )

        eth_price = Decimal(str(settings.eth_usd_price))

        eth_value = eth_balance * eth_price
        total_value = eth_value + usdc_balance

        eth_exposure_percent = (
            float(eth_value / total_value * 100)
            if total_value > 0
            else 0.0
        )

        response = WalletCheckResponse(
            address=checksum_address,
            network="base",
            valid=True,
            eth_balance=float(eth_balance),
            eth_price=float(eth_price),
            eth_value=float(eth_value),
            usdc_balance=float(usdc_balance),
            total_value=float(total_value),
            eth_exposure_percent=round(eth_exposure_percent, 2),
        )

        if record_snapshot:
            # Manual public-address checks are kept as saved snapshots.
            app_state.set_wallet(response)
            try:
                self._persist_snapshot(response)
            except Exception:
                logger.exception(
                    "Failed to persist wallet snapshot for %s; "
                    "returning the read result anyway.",
                    checksum_address,
                )

        return response

    def _persist_snapshot(
        self,
        response: WalletCheckResponse,
    ) -> None:
        """
        Save a computed snapshot via the repository. Pure data write,
        no RPC calls here. Kept separate so `check()` stays readable
        and the persistence path is easy to test in isolation.
        """

        with get_session() as db:
            repository = WalletRepository(db)
            repository.save_snapshot(response)

    async def _read_balances(
        self,
        address: str,
    ) -> tuple[Decimal, Decimal]:

        try:
            eth_balance, usdc_balance = await asyncio.gather(
                self.client.get_eth_balance(address),
                self.client.get_erc20_balance(
                    token_address=settings.usdc_contract_address,
                    holder_address=address,
                    decimals=settings.usdc_decimals,
                ),
            )

        except BaseRpcError as exc:
            raise WalletUnavailableError(
                f"Unable to read balances from Base right now: {exc}"
            ) from exc

        return eth_balance, usdc_balance

    @staticmethod
    def _validate_address(address: str) -> str:
        """
        Full EIP-55 validation: correct hex format, and if the address
        is mixed-case, the checksum must be correct. All-lowercase or
        all-uppercase addresses are accepted without a checksum, per
        the EIP-55 spec.
        """

        address = address.strip()

        if not is_hex_address(address):
            raise InvalidAddressError(
                "That doesn't look like a valid wallet address. "
                "Expected a 0x-prefixed, 40-character hex address."
            )

        # Mixed-case addresses are checksum-formatted (EIP-55) and
        # must match the checksum exactly - this is what catches a
        # typo'd or corrupted address before we ever query a balance.
        # All-lowercase / all-uppercase addresses are accepted as
        # unchecksummed input, per the EIP-55 spec, and normalized
        # below.
        if is_checksum_formatted_address(address) and not is_checksum_address(
            address
        ):
            raise InvalidAddressError(
                "This address has an invalid EIP-55 checksum. "
                "Double-check it was copied correctly."
            )

        return to_checksum_address(address)


def get_current_exposure(
    address: str,
) -> WalletExposureResponse:
    """
    Return exposure from the latest saved snapshot for this address.

    Does NOT trigger a new RPC read — if you want fresh data, call
    /api/wallet/check first. Raises NoSnapshotError if no snapshot
    exists yet.

    This is the input the (not-yet-built) Risk Engine consumes
    (spec section 23: exposure = ETH value).
    """

    checksum_address = WalletService._validate_address(address)

    with get_session() as db:
        repository = WalletRepository(db)
        snapshot = repository.get_latest(checksum_address)

    if snapshot is None:
        raise NoSnapshotError(
            f"No saved snapshot exists for {checksum_address} yet. "
            "Check the wallet first to create one."
        )

    return WalletExposureResponse(
        address=snapshot.wallet_address,
        eth_value=snapshot.eth_value,
        total_value=snapshot.total_value,
        eth_exposure_percent=snapshot.eth_exposure_percent,
        as_of=snapshot.created_at,
    )
