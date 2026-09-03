from typing import Literal

from pydantic import BaseModel, Field, field_validator


Verdict = Literal[
    "LIKELY_TRUE",
    "LIKELY_FALSE",
    "UNCERTAIN",
]

MarketImpact = Literal[
    "LOW",
    "MEDIUM",
    "HIGH",
]


class ModelAnalysis(BaseModel):
    model: str

    credibility_score: float = Field(
        ge=0.0,
        le=1.0,
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    verdict: Verdict

    market_impact: MarketImpact

    reasoning_summary: str

    supporting_evidence: list[str] = Field(
        default_factory=list
    )

    contradicting_evidence: list[str] = Field(
        default_factory=list
    )

    missing_context: list[str] = Field(
        default_factory=list
    )


class ConsensusAnalysis(BaseModel):
    credibility_score: float = Field(
        ge=0.0,
        le=1.0,
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    verdict: Verdict

    market_impact: MarketImpact

    disagreement: float = Field(
        ge=0.0,
        le=1.0,
    )

    reasoning_summary: str

    model_results: list[ModelAnalysis]


class EvidenceItem(BaseModel):
    """A source retained with an analysis so its conclusion is auditable."""

    title: str
    url: str
    source: str
    excerpt: str
    published_at: str | None = None


class PortfolioExposure(BaseModel):
    affected_assets: list[str]
    portfolio_percentage: float = Field(ge=0.0, le=100.0)
    scenario_change: float
    estimated_portfolio_impact: float
    risk_level: MarketImpact
    disclaimer: str


class PortfolioContext(BaseModel):
    """Minimal, address-free wallet context available to recommendations."""

    wallet_connected: bool = False
    network: str | None = None
    total_value: float | None = None
    allocations: dict[str, float] = Field(default_factory=dict)


class FinalAssessment(BaseModel):
    verdict: Verdict
    analysis: str


class Recommendation(BaseModel):
    """A proposed next step. Execution is deliberately outside this API."""

    title: str
    rationale: str = ""
    steps: list[str] = Field(default_factory=list)
    automation_eligible: bool = False
    requires_confirmation: bool = True


class ClaimAnalysisResponse(BaseModel):
    """The complete evidence → consensus → risk contract for the UI."""

    analysis_id: str
    claim: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    consensus: ConsensusAnalysis
    final_assessment: FinalAssessment
    portfolio_context: PortfolioContext = Field(default_factory=PortfolioContext)
    portfolio_exposure: PortfolioExposure | None = None
    recommendations: list[Recommendation] = Field(default_factory=list)

    @field_validator("recommendations", mode="before")
    @classmethod
    def normalize_legacy_recommendations(cls, value):
        # Lets analyses saved by the earlier prototype remain readable.
        if not isinstance(value, list):
            return []
        return [
            {"title": item, "steps": [item]}
            if isinstance(item, str)
            else item
            for item in value
        ]


class NewsItem(BaseModel):
    title: str
    url: str
    source: str
    excerpt: str
    published_at: str | None = None
    is_live: bool = True


class ClaimAnalysisRequest(BaseModel):
    claim: str = Field(
        min_length=1,
        max_length=10000,
    )


class HistorySummary(BaseModel):
    analysis_id: str
    claim: str
    verdict: Verdict
    credibility_score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    created_at: str


class FollowUpRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class FollowUpEntry(BaseModel):
    follow_up_id: str
    question: str
    answer: str
    created_at: str


class HistoryDetail(BaseModel):
    analysis: ClaimAnalysisResponse
    created_at: str
    follow_ups: list[FollowUpEntry] = Field(default_factory=list)
