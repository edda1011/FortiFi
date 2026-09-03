"""
Unit tests for the risk engine and risk service.

The risk engine is pure deterministic code, so these tests never
touch the network. The risk service's wallet dependency is mocked.
"""

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from app.engines.risk_engine import RiskEngine
from app.schemas.wallet import WalletCheckResponse
from app.services.risk_service import RiskService


# --- RiskEngine.estimate_loss ------------------------------------------

def test_estimate_loss_multiplies_exposure_by_downside():
    engine = RiskEngine()

    assert engine.estimate_loss(10000, 0.20) == 2000.0
    assert engine.estimate_loss(5000, 0.10) == 500.0
    assert engine.estimate_loss(0, 0.50) == 0.0


def test_estimate_loss_rounds_to_two_decimals():
    engine = RiskEngine()

    assert engine.estimate_loss(333.33, 0.333) == pytest.approx(111.0, abs=0.01)


# --- RiskEngine.classify ------------------------------------------------

def test_classify_low():
    engine = RiskEngine()
    assert engine.classify(0) == "LOW"
    assert engine.classify(499.99) == "LOW"


def test_classify_moderate():
    engine = RiskEngine()
    assert engine.classify(500.0) == "MODERATE"
    assert engine.classify(1499.99) == "MODERATE"


def test_classify_high():
    engine = RiskEngine()
    assert engine.classify(1500.0) == "HIGH"
    assert engine.classify(4999.99) == "HIGH"


def test_classify_critical():
    engine = RiskEngine()
    assert engine.classify(5000.0) == "CRITICAL"
    assert engine.classify(100000.0) == "CRITICAL"


# --- RiskService.analyze ------------------------------------------------

def _make_wallet(eth_value=10000.0):
    return WalletCheckResponse(
        address="0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed",
        network="base",
        valid=True,
        eth_balance=2.5,
        eth_price=4000.0,
        eth_value=eth_value,
        usdc_balance=0.0,
        total_value=eth_value,
        eth_exposure_percent=100.0,
    )


def test_risk_service_computes_high_risk():
    service = RiskService()
    service.wallet_service.check = AsyncMock(
        return_value=_make_wallet(eth_value=10000.0)
    )

    result = asyncio.run(
        service.analyze(
            address="0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed",
            scenario_downside=0.20,
        )
    )

    assert result.exposure == 10000.0
    assert result.estimated_loss == 2000.0
    assert result.risk_level == "HIGH"


def test_risk_service_computes_low_risk():
    service = RiskService()
    service.wallet_service.check = AsyncMock(
        return_value=_make_wallet(eth_value=1000.0)
    )

    result = asyncio.run(
        service.analyze(
            address="0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed",
            scenario_downside=0.10,
        )
    )

    assert result.estimated_loss == 100.0
    assert result.risk_level == "LOW"


def test_risk_service_exposure_is_eth_value():
    service = RiskService()
    service.wallet_service.check = AsyncMock(
        return_value=_make_wallet(eth_value=8000.0)
    )

    result = asyncio.run(
        service.analyze(
            address="0x5aAeb6053F3E94C9b9A09f33669435E7Ef1BeAed",
            scenario_downside=0.25,
        )
    )

    assert result.exposure == 8000.0
    assert result.estimated_loss == 2000.0
