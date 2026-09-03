from __future__ import annotations

import re

from app.schemas.analysis import PortfolioExposure
from app.services.state import app_state


class ExposureService:
    """Deterministic scenario exposure; it is never calculated by an LLM."""

    def calculate(self, claim: str) -> PortfolioExposure | None:
        wallet = app_state.wallet
        if wallet is None:
            return None

        normalized = claim.upper()
        if "ETH" not in normalized and "ETHEREUM" not in normalized:
            return None

        scenario = self._scenario_change(claim)
        if scenario is None:
            return None

        percentage = wallet.eth_exposure_percent
        impact = round(percentage * scenario / 100, 2)
        magnitude = abs(impact)
        level = "HIGH" if magnitude >= 15 else "MEDIUM" if magnitude >= 5 else "LOW"
        return PortfolioExposure(
            affected_assets=["ETH"],
            portfolio_percentage=percentage,
            scenario_change=scenario,
            estimated_portfolio_impact=impact,
            risk_level=level,
            disclaimer=(
                "Scenario exposure only; this is not a prediction and assumes other "
                "assets remain unchanged."
            ),
        )

    @staticmethod
    def _scenario_change(claim: str) -> float | None:
        match = re.search(r"(?:fall|drop|declin\w*|lose|down|rise|gain|up)[^0-9%]{0,30}(\d{1,3}(?:\.\d+)?)\s*%", claim, re.I)
        if not match:
            match = re.search(r"([+-]\s*\d{1,3}(?:\.\d+)?)\s*%", claim)
        if not match:
            return None
        value = float(match.group(1).replace(" ", ""))
        direction = -1 if re.search(r"(?:fall|drop|declin\w*|lose|down)", claim[:match.start() + 1], re.I) else 1
        return round(value * direction, 2)
