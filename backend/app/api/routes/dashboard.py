from fastapi import APIRouter, Depends

from app.api.auth import optional_wallet
from app.schemas.dashboard import DashboardSummary
from app.schemas.analysis import NewsItem
from app.services.analysis_store import AnalysisStore
from app.services.search_service import SearchService


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

    Returns persisted claim and completed hedge information. Wallet balances
    and risk calculations remain frontend page-session state.
    """

    # Wallet balances and scenario calculations are page-session state in the
    # frontend. A full refresh intentionally starts risk assessment empty.
    wallet = None

    store = AnalysisStore()
    recent = store.recent(owner_address, limit=50) if owner_address else []
    latest_hedge = next(
        (execution for analysis in recent if (execution := store.get_hedge_execution(analysis.analysis_id, owner_address))),
        None,
    )
    return DashboardSummary(
        has_wallet=wallet is not None,
        wallet=wallet,
        has_risk=False,
        risk=None,
        latest_analysis=recent[0] if recent else None,
        latest_hedge_execution=latest_hedge,
    )


@router.get("/news", response_model=list[NewsItem])
async def dashboard_news():
    """Latest market headlines using the same search adapter as claim checks."""
    return await SearchService().dashboard_news()
