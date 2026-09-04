from datetime import datetime

from pydantic import BaseModel, Field


class WalletCheckRequest(BaseModel):
    address: str = Field(
        min_length=1,
        max_length=100,
        description="A public wallet address. No private keys or seed phrases.",
    )


class WalletCheckResponse(BaseModel):
    address: str

    network: str = "base"

    valid: bool

    eth_balance: float = Field(
        ge=0.0,
    )

    eth_price: float = Field(
        ge=0.0,
    )

    eth_value: float = Field(
        ge=0.0,
    )

    usdc_balance: float = Field(
        ge=0.0,
    )

    total_value: float = Field(
        ge=0.0,
    )

    eth_exposure_percent: float = Field(
        ge=0.0,
        le=100.0,
    )


class WalletSnapshotResponse(BaseModel):
    """
    A single persisted wallet snapshot, as returned by the retrieval
    endpoints. Mirrors the fields stored in the wallet_snapshots table.
    """

    id: int

    address: str

    network: str

    eth_balance: float

    eth_price: float

    eth_value: float

    usdc_balance: float

    total_value: float

    eth_exposure_percent: float

    created_at: datetime


class WalletHistoryResponse(BaseModel):
    """
    A list of past snapshots for an address, most recent first.
    """

    address: str

    snapshots: list[WalletSnapshotResponse]


class WalletExposureResponse(BaseModel):
    """
    The current ETH exposure for an address, derived from the latest
    saved snapshot. This is the input the (not-yet-built) Risk Engine
    consumes (spec section 23: exposure = ETH value).
    """

    address: str

    eth_value: float

    total_value: float

    eth_exposure_percent: float

    as_of: datetime
