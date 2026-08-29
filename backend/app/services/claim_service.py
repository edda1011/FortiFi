from app.schemas.analysis import ConsensusAnalysis
from app.services.consensus_service import ConsensusService
from app.services.gonka_service import GonkaService


class ClaimService:
    """
    Main service responsible for processing a financial claim.
    """

    def __init__(self) -> None:
        self.gonka_service = GonkaService()
        self.consensus_service = ConsensusService()

    async def analyze(
        self,
        claim: str,
    ) -> ConsensusAnalysis:

        analyses = await self.gonka_service.analyze_claim(
            claim
        )

        return self.consensus_service.calculate(
            analyses
        )