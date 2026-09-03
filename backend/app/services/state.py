"""
A tiny in-memory store for the latest wallet snapshot and risk
assessment.

This is a deliberate, temporary stand-in for the SQLite persistence
layer (which is a later milestone). It lets the dashboard summarize
the most recent wallet check and risk assessment without a database,
while keeping the same shape the DB layer will eventually provide.

It is process-local: restarting the backend clears it.
"""

from typing import Optional

from app.schemas.risk import RiskAssessmentResponse
from app.schemas.wallet import WalletCheckResponse


class AppState:
    """
    Holds the most recent wallet snapshot and risk assessment.
    """

    def __init__(self) -> None:
        self._wallet: Optional[WalletCheckResponse] = None
        self._risk: Optional[RiskAssessmentResponse] = None

    def set_wallet(self, wallet: WalletCheckResponse) -> None:
        self._wallet = wallet

    def set_risk(self, risk: RiskAssessmentResponse) -> None:
        self._risk = risk

    @property
    def wallet(self) -> Optional[WalletCheckResponse]:
        return self._wallet

    @property
    def risk(self) -> Optional[RiskAssessmentResponse]:
        return self._risk


# Module-level singleton shared across services.
app_state = AppState()
