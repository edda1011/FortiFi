from __future__ import annotations

import re
from urllib.parse import unquote_plus

from app.schemas.analysis import EvidenceItem, ModelAnalysis, PortfolioExposure
from app.services.state import app_state


class ExposureService:
    """Deterministic scenario exposure; it is never calculated by an LLM."""

    ETH_PATTERN = re.compile(
        r"(?<![A-Za-z0-9])(?:ETH|Ethereum|Ether|WETH)(?![A-Za-z0-9])",
        re.IGNORECASE,
    )

    def detect_assets(
        self,
        claim: str,
        evidence: list[EvidenceItem],
        analyses: list[ModelAnalysis],
    ) -> tuple[list[str], list[str]]:
        """Detect hedgeable assets locally without another inference request."""
        sources: list[str] = []
        if self._mentions_eth(unquote_plus(claim)):
            sources.append("claim_input")

        evidence_text = " ".join(
            f"{item.title} {item.excerpt}" for item in evidence
        )
        if self._mentions_eth(evidence_text):
            sources.append("article_content")

        analysis_text = " ".join(
            " ".join(
                [
                    item.reasoning_summary,
                    *item.supporting_evidence,
                    *item.contradicting_evidence,
                    *item.missing_context,
                ]
            )
            for item in analyses
        )
        if self._mentions_eth(analysis_text):
            sources.append("ai_consensus")

        return (["ETH"] if sources else []), sources

    def calculate(
        self, claim: str, detected_assets: list[str] | None = None
    ) -> PortfolioExposure | None:
        wallet = app_state.wallet
        if wallet is None:
            return None

        if detected_assets is None:
            detected_assets = ["ETH"] if self._mentions_eth(claim) else []
        if "ETH" not in detected_assets:
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

    @classmethod
    def _mentions_eth(cls, value: str) -> bool:
        return bool(cls.ETH_PATTERN.search(value))

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
