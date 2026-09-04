from fastapi import APIRouter, Depends

from app.api.auth import optional_wallet
from app.schemas.dashboard import DashboardSummary
from app.schemas.analysis import NewsItem
from app.services.analysis_store import AnalysisStore
from app.services.search_service import SearchService
from app.services.state import app_state


router = APIRouter(
    tags=["Dashboard"],
)


@router.get(
    "/summary",
    response_model=DashboardSummary,
)
async def dashboard_summary(owner_address: str | None = Depends(optional_wallet)):
    """
    Summarize the current FortiFi state.

    Stateless: reflects the most recent wallet check and risk
    assessment made in this session (spec section 30). The dashboard
    does not maintain its own database state.
    """

    # Connected-wallet balances are refreshed live by the frontend. Do not
    # expose the process-global result of another user's manual address check.
    wallet = None
    risk = app_state.risk

    recent = AnalysisStore().recent(owner_address, limit=1) if owner_address else []
    return DashboardSummary(
        has_wallet=wallet is not None,
        wallet=wallet,
        has_risk=risk is not None,
        risk=risk,
        latest_analysis=recent[0] if recent else None,
    )


@router.get("/news", response_model=list[NewsItem])
async def dashboard_news():
    """Latest market headlines using the same search adapter as claim checks."""
    return await SearchService().dashboard_news()
