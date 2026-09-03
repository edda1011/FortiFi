from typing import Optional

from pydantic import BaseModel

from app.schemas.risk import RiskAssessmentResponse
from app.schemas.analysis import ClaimAnalysisResponse
from app.schemas.wallet import WalletCheckResponse


class DashboardSummary(BaseModel):
    """
    A stateless summary of the current FortiFi state.

    The dashboard does not maintain its own database state - it
    reflects the most recent wallet check and risk assessment made
    in this session (spec section 30).
    """

    has_wallet: bool

    wallet: Optional[WalletCheckResponse] = None

    has_risk: bool

    risk: Optional[RiskAssessmentResponse] = None

    latest_analysis: Optional[ClaimAnalysisResponse] = None
