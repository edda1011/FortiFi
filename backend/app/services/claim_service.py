from app.schemas.analysis import ConsensusAnalysis
from uuid import uuid4

from app.schemas.analysis import ClaimAnalysisResponse, FinalAssessment
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
        try:
            final = await self.gonka_service.finalize_claim(claim, consensus, evidence_data)
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
        result = ClaimAnalysisResponse(
            analysis_id=str(uuid4()), claim=claim, evidence=evidence, consensus=consensus,
            final_assessment=FinalAssessment(
                verdict=verdict,
                analysis=final.get("analysis", consensus.reasoning_summary),
            ),
            portfolio_exposure=self.exposure_service.calculate(claim),
            recommendations=recommendations,
        )
        self.store.save(result)
        return result
