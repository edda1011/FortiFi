from uuid import uuid4

from app.schemas.analysis import (
    ClaimAnalysisResponse,
    EvidenceItem,
    FinalAssessment,
    ModelAnalysis,
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
        return self.build_result(claim, evidence, analyses)

    def build_result(
        self,
        claim: str,
        evidence: list[EvidenceItem],
        analyses: list[ModelAnalysis],
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
        missing_context = list(
            dict.fromkeys(
                item
                for analysis in analyses
                for item in analysis.missing_context
            )
        )
        recommendations = [
            f"Verify before acting: {item}"
            for item in missing_context[:3]
        ]
        result = ClaimAnalysisResponse(
            analysis_id=str(uuid4()), claim=claim, evidence=evidence, consensus=consensus,
            final_assessment=FinalAssessment(
                verdict=consensus.verdict,
                analysis=local_assessment,
            ),
            portfolio_exposure=self.exposure_service.calculate(claim),
            recommendations=recommendations,
        )
        self.store.save(result)
        return result
