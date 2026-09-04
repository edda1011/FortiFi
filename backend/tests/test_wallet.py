"""
Unit tests for the wallet feature.

These never touch the real network - Base RPC calls are mocked so
the suite stays fast and doesn't depend on an external endpoint.
"""

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import pytest

from app.integrations.base.client import BaseRpcError
from app.services.wallet_service import (
    InvalidAddressError,
    WalletService,
    WalletUnavailableError,
)


# --- Address validation -------------------------------------------------

@pytest.mark.parametrize(
    "address",
    [
        "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed",  # correct checksum
        "0xde709f2102306220921060314715629080e2fb77",  # all lowercase
        "0x27B1FDB04752BBC536007A920D24ACB045561C26",  # all uppercase
    ],
)
def test_validate_address_accepts_valid_addresses(address):
    result = WalletService._validate_address(address)
    assert result.startswith("0x")
    assert len(result) == 42


def test_validate_address_rejects_bad_checksum():
    # Same address as above with one character's case flipped.
    bad_checksum = "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAeD"

    with pytest.raises(InvalidAddressError):
        WalletService._validate_address(bad_checksum)


def test_validate_address_rejects_malformed_input():
    with pytest.raises(InvalidAddressError):
        WalletService._validate_address("not-an-address")

    with pytest.raises(InvalidAddressError):
        WalletService._validate_address("0x1234")  # too short


# --- WalletService.check() ----------------------------------------------

def test_check_computes_portfolio_snapshot():
    service = WalletService()
    service.client.get_eth_balance = AsyncMock(return_value=Decimal("2.41"))
    service.client.get_erc20_balance = AsyncMock(return_value=Decimal("1250"))

    result = asyncio.run(
        service.check("0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed")
    )

    assert result.valid is True
    assert result.eth_balance == 2.41
    assert result.usdc_balance == 1250.0
    assert result.eth_value == pytest.approx(2.41 * result.eth_price)
    assert result.total_value == pytest.approx(
        result.eth_value + result.usdc_balance
    )
    assert 0.0 <= result.eth_exposure_percent <= 100.0


def test_check_handles_zero_balance_wallet():
    service = WalletService()
    service.client.get_eth_balance = AsyncMock(return_value=Decimal("0"))
    service.client.get_erc20_balance = AsyncMock(return_value=Decimal("0"))

    result = asyncio.run(
        service.check("0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed")
    )

    assert result.total_value == 0.0
    assert result.eth_exposure_percent == 0.0


def test_live_connected_check_does_not_save_snapshot():
    service = WalletService()
    service.client.get_eth_balance = AsyncMock(return_value=Decimal("1"))
    service.client.get_erc20_balance = AsyncMock(return_value=Decimal("5"))
    service._persist_snapshot = Mock()

    asyncio.run(
        service.check(
            "0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed",
            record_snapshot=False,
        )
    )

    service._persist_snapshot.assert_not_called()


def test_check_raises_invalid_address_before_calling_rpc():
    service = WalletService()
    service.client.get_eth_balance = AsyncMock()
    service.client.get_erc20_balance = AsyncMock()

    with pytest.raises(InvalidAddressError):
        asyncio.run(service.check("not-an-address"))

    service.client.get_eth_balance.assert_not_called()
    service.client.get_erc20_balance.assert_not_called()


def test_check_surfaces_rpc_failure_as_wallet_unavailable():
    service = WalletService()
    service.client.get_eth_balance = AsyncMock(
        side_effect=BaseRpcError("Base RPC timed out")
    )
    service.client.get_erc20_balance = AsyncMock(return_value=Decimal("0"))

    with pytest.raises(WalletUnavailableError):
        asyncio.run(
            service.check("0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed")
        )
