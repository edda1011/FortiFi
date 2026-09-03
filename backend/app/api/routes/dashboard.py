from fastapi import APIRouter

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
async def dashboard_summary():
    """
    Summarize the current FortiFi state.

    Stateless: reflects the most recent wallet check and risk
    assessment made in this session (spec section 30). The dashboard
    does not maintain its own database state.
    """

    wallet = app_state.wallet
    risk = app_state.risk

    recent = AnalysisStore().recent(limit=1)
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
