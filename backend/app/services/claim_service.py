from uuid import uuid4

from app.schemas.analysis import (
    ClaimAnalysisResponse,
    EvidenceItem,
    FinalAssessment,
    ModelAnalysis,
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
        owner_address: str | None = None,
    ) -> ClaimAnalysisResponse:

        evidence = await self.search_service.search_evidence(claim)
        evidence_data = [item.model_dump() for item in evidence]

        analyses = await self.gonka_service.analyze_claim(
            claim, evidence_data
        )
        return self.build_result(claim, evidence, analyses, owner_address)

    def build_result(
        self,
        claim: str,
        evidence: list[EvidenceItem],
        analyses: list[ModelAnalysis],
        owner_address: str | None = None,
    ) -> ClaimAnalysisResponse:
        consensus = self.consensus_service.calculate(analyses)
        supporting_models = sum(
            analysis.verdict == consensus.verdict for analysis in analyses
        )
        representative = max(
            (
                analysis
                for analysis in analyses
                if analysis.verdict == consensus.verdict
            ),
            key=lambda analysis: analysis.confidence,
        )
        verdict_statement, next_step = {
            "LIKELY_TRUE": (
                "Evidence leans in favor of this claim.",
                "Treat it as supported, but verify the cited evidence before acting.",
            ),
            "LIKELY_FALSE": (
                "Evidence leans against this claim.",
                "Do not rely on it without stronger, independently verified evidence.",
            ),
            "UNCERTAIN": (
                "The claim remains unverified.",
                "Treat it as a market hypothesis, not a verified trading signal.",
            ),
        }[consensus.verdict]
        local_assessment = (
            f"FortiFi verdict: {verdict_statement} "
            f"{supporting_models} of {len(analyses)} models reached this conclusion. "
            f"The strongest supporting assessment found that "
            f"{representative.reasoning_summary} "
            f"Consensus confidence is {consensus.confidence:.0%}, with "
            f"{consensus.market_impact.lower()} potential market impact. {next_step}"
        )
        portfolio_context = self._portfolio_context()
        detected_assets, asset_detection_sources = self.exposure_service.detect_assets(
            claim, evidence, analyses
        )
        portfolio_exposure = self.exposure_service.calculate(claim, detected_assets)
        missing_context = list(
            dict.fromkeys(
                item
                for analysis in analyses
                for item in analysis.missing_context
            )
        )
        recommendations = [
            {
                "title": f"Verify before acting: {item}",
                "rationale": "The responding models identified this context as missing.",
                "steps": [f"Find an independent source that addresses: {item}"],
                "automation_eligible": False,
                "requires_confirmation": True,
            }
            for item in missing_context[:3]
        ]
        result = ClaimAnalysisResponse(
            analysis_id=str(uuid4()), claim=claim, evidence=evidence, consensus=consensus,
            final_assessment=FinalAssessment(
                verdict=consensus.verdict,
                analysis=local_assessment,
            ),
            portfolio_context=portfolio_context,
            portfolio_exposure=portfolio_exposure,
            detected_assets=detected_assets,
            asset_detection_sources=asset_detection_sources,
            recommendations=recommendations,
        )
        self.store.save(result, owner_address)
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
