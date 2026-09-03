from app.schemas.analysis import ConsensusAnalysis
from uuid import uuid4

from app.schemas.analysis import (
    ClaimAnalysisResponse,
    FinalAssessment,
    PortfolioContext,
)
from app.services.analysis_store import AnalysisStore
from app.services.consensus_service import ConsensusService
from app.services.exposure_service import ExposureService
from app.services.gonka_service import GonkaService
from app.services.search_service import SearchService


class ClaimService:
    """
    Main service responsible for processing a financial claim.
    """

    def __init__(self) -> None:
        self.gonka_service = GonkaService()
        self.consensus_service = ConsensusService()
        self.search_service = SearchService()
        self.exposure_service = ExposureService()
        self.store = AnalysisStore()

    async def analyze(
        self,
        claim: str,
    ) -> ClaimAnalysisResponse:

        evidence = await self.search_service.search_evidence(claim)
        evidence_data = [item.model_dump() for item in evidence]

        analyses = await self.gonka_service.analyze_claim(
            claim, evidence_data
        )
        consensus = self.consensus_service.calculate(analyses)
        portfolio_context = self._portfolio_context()
        portfolio_exposure = self.exposure_service.calculate(claim)
        try:
            final = await self.gonka_service.finalize_claim(
                claim,
                consensus,
                evidence_data,
                portfolio_context.model_dump(),
                portfolio_exposure.model_dump() if portfolio_exposure else None,
            )
        except Exception:
            # The independent model consensus remains a useful result when
            # the optional synthesis request is unavailable.
            final = {}
        verdict = final.get("verdict", consensus.verdict)
        if verdict not in {"LIKELY_TRUE", "LIKELY_FALSE", "UNCERTAIN"}:
            verdict = consensus.verdict
        recommendations = final.get("recommendations", [])
        if not isinstance(recommendations, list):
            recommendations = []
        recommendations = [
            {"title": item, "rationale": "", "steps": [item], "automation_eligible": False, "requires_confirmation": True}
            if isinstance(item, str)
            else {**item, "requires_confirmation": True}
            for item in recommendations
            if isinstance(item, (str, dict))
        ]
        result = ClaimAnalysisResponse(
            analysis_id=str(uuid4()), claim=claim, evidence=evidence, consensus=consensus,
            final_assessment=FinalAssessment(
                verdict=verdict,
                analysis=final.get("analysis", consensus.reasoning_summary),
            ),
            portfolio_context=portfolio_context,
            portfolio_exposure=portfolio_exposure,
            recommendations=recommendations,
        )
        self.store.save(result)
        return result

    @staticmethod
    def _portfolio_context() -> PortfolioContext:
        """Build the optional recommendation input without sending an address."""
        from app.services.state import app_state

        wallet = app_state.wallet
        if wallet is None:
            return PortfolioContext()

        eth_allocation = round(wallet.eth_exposure_percent, 2)
        return PortfolioContext(
            wallet_connected=True,
            network=wallet.network,
            total_value=round(wallet.total_value, 2),
            allocations={
                "ETH": eth_allocation,
                "USDC": round(max(0.0, 100 - eth_allocation), 2),
            },
        )
