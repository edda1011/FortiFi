import asyncio
from decimal import Decimal

from eth_utils import (
    is_checksum_address,
    is_checksum_formatted_address,
    is_hex_address,
    to_checksum_address,
)

from app.config import settings
from app.integrations.base.client import BaseClient, BaseRpcError
from app.schemas.wallet import WalletCheckResponse
from app.services.state import app_state


class InvalidAddressError(ValueError):
    """Raised when a wallet address fails format/checksum validation."""


class WalletUnavailableError(RuntimeError):
    """Raised when Base can't be reached to read balances."""


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

        # Record the latest snapshot so the dashboard can summarize it.
        app_state.set_wallet(response)

        return response

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
