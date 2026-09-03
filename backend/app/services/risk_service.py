from app.engines.risk_engine import RiskEngine
from app.schemas.risk import RiskAssessmentResponse
from app.schemas.wallet import WalletCheckResponse
from app.services.state import app_state
from app.services.wallet_service import WalletService


class RiskService:
    """
    Orchestrates the deterministic risk assessment.

    wallet address
        -> wallet snapshot (ETH exposure)
        -> exposure x scenario_downside
        -> estimated loss + risk level

    This service only combines the wallet snapshot with a scenario.
    It never calls the AI.
    """

    def __init__(self) -> None:
        self.wallet_service = WalletService()
        self.risk_engine = RiskEngine()

    async def analyze(
        self,
        address: str,
        scenario_downside: float,
    ) -> RiskAssessmentResponse:

        wallet = await self.wallet_service.check(address)

        # Exposure is the ETH value - the part of the portfolio that
        # moves with ETH's price.
        exposure = wallet.eth_value

        estimated_loss = self.risk_engine.estimate_loss(
            exposure=exposure,
            scenario_downside=scenario_downside,
        )

        risk_level = self.risk_engine.classify(
            estimated_loss
        )

        response = RiskAssessmentResponse(
            wallet=wallet,
            exposure=round(exposure, 2),
            scenario_downside=scenario_downside,
            estimated_loss=estimated_loss,
            risk_level=risk_level,
        )

        # Record the latest assessment so the dashboard can summarize it.
        app_state.set_risk(response)

        return response
