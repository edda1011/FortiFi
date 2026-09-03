from fastapi import APIRouter

from app.schemas.dashboard import DashboardSummary
from app.services.state import app_state


router = APIRouter(
    tags=["Dashboard"],
)


@router.get(
    "/summary",
    response_model=DashboardSummary,
)
async def dashboard_summary():
    """
    Summarize the current FortiFi state.

    Stateless: reflects the most recent wallet check and risk
    assessment made in this session (spec section 30). The dashboard
    does not maintain its own database state.
    """

    wallet = app_state.wallet
    risk = app_state.risk

    return DashboardSummary(
        has_wallet=wallet is not None,
        wallet=wallet,
        has_risk=risk is not None,
        risk=risk,
    )
