from app.config import settings
from app.schemas.risk import RiskLevel


class RiskEngine:
    """
    Deterministic risk calculation. This is plain code - no AI.

    estimated_loss = exposure x scenario_downside

    Risk level is classified from the estimated loss using thresholds
    that live in configuration (spec section 23):

        LOW        <  $500
        MODERATE   $500 - $1,500
        HIGH       $1,500 - $5,000
        CRITICAL   >  $5,000
    """

    def __init__(self) -> None:
        self.low_max = settings.risk_low_max
        self.moderate_max = settings.risk_moderate_max
        self.high_max = settings.risk_high_max

    def estimate_loss(
        self,
        exposure: float,
        scenario_downside: float,
    ) -> float:
        """
        exposure x scenario_downside, rounded to 2 decimals.
        """

        return round(
            exposure * scenario_downside,
            2,
        )

    def classify(
        self,
        estimated_loss: float,
    ) -> RiskLevel:
        """
        Map an estimated loss (USD) to a risk level.
        """

        if estimated_loss < self.low_max:
            return "LOW"

        if estimated_loss < self.moderate_max:
            return "MODERATE"

        if estimated_loss < self.high_max:
            return "HIGH"

        return "CRITICAL"
