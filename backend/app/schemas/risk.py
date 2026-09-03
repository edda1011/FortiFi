from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.wallet import WalletCheckResponse


RiskLevel = Literal[
    "LOW",
    "MODERATE",
    "HIGH",
    "CRITICAL",
]


class RiskAnalyzeRequest(BaseModel):
    """
    A wallet address plus a scenario downside (as a fraction, e.g.
    0.20 for a 20% drop). FortiFi checks the wallet, computes the
    exposure, and estimates the potential loss under the scenario.
    """

    address: str = Field(
        min_length=1,
        max_length=100,
        description=(
            "A public wallet address. No private keys or seed phrases."
        ),
    )

    scenario_downside: float = Field(
        gt=0.0,
        le=1.0,
        description=(
            "The assumed downside move as a fraction, e.g. 0.20 "
            "for a 20% drop."
        ),
    )


class RiskAssessmentResponse(BaseModel):
    """
    Deterministic risk output. This is calculated by code, not AI.
    """

    wallet: WalletCheckResponse

    exposure: float = Field(
        ge=0.0,
        description="The value at risk (ETH value in USD).",
    )

    scenario_downside: float = Field(
        gt=0.0,
        le=1.0,
    )

    estimated_loss: float = Field(
        ge=0.0,
        description="exposure x scenario_downside.",
    )

    risk_level: RiskLevel
