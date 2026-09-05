from typing import Optional

from pydantic import BaseModel

from app.schemas.risk import RiskAssessmentResponse
from app.schemas.analysis import ClaimAnalysisResponse, HedgeExecution
from app.schemas.wallet import WalletCheckResponse


class DashboardSummary(BaseModel):
    """
    A stateless summary of the current FortiFi state.

    Wallet balances and risk calculations remain frontend session state;
    persisted claim and completed hedge information can be summarized here.
    """

    has_wallet: bool

    wallet: Optional[WalletCheckResponse] = None

    has_risk: bool

    risk: Optional[RiskAssessmentResponse] = None

    latest_analysis: Optional[ClaimAnalysisResponse] = None

    latest_hedge_execution: Optional[HedgeExecution] = None
