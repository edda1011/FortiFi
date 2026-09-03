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
