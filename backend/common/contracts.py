"""Frozen data contracts shared by all three modules.

Source of truth for the JSON schemas in /contracts (regenerate with `make schemas`).
Rules: never rename or remove a field. Add new fields as OPTIONAL only, note them in
contracts/CHANGELOG.md, and update the fixtures in the same commit. Extra keys are allowed
so a consumer never breaks when a producer adds an optional field.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Contract(BaseModel):
    model_config = ConfigDict(extra="allow")


Evidence = Literal["evidence", "user_supplied", "llm_assumption"]


# ---------------------------------------------------------------- shared v2 pieces
class Source(Contract):
    url: str
    quote: str  # verbatim text that was verified to appear in the fetched page
    retrieved_at: str


class ResearchNote(Contract):
    topic: str  # e.g. competitor_pricing, regulation, channels, seasonality
    note: str
    source_url: str
    quote: str


class TrendNote(Contract):
    note: str
    source_url: str
    quote: str
    effect: str | None = None  # e.g. "budget -5%"; bounded to about +/-10%


# ---------------------------------------------------------------- options and population
class Option(Contract):
    id: str
    label: str
    role: Literal["you", "competitor", "outside"]
    price: float = 0.0
    features: list[float] = Field(default_factory=list)
    novelty: float = 0.0


class Segment(Contract):
    id: str
    name: str
    share: float
    evidence: Evidence = "llm_assumption"
    sources: list[Source] | None = None  # v2 optional


class Agent(Contract):
    id: str
    segment: str
    budget: float
    alpha: float  # price sensitivity per currency unit, roughly 0.05 to 0.3
    w: list[float]  # weight per pack attribute
    brand: dict[str, float]  # affinity per option id (missing id = 0)
    switch: float
    risk: float
    incumbent: str  # option id the agent uses today (may be the outside option id)
    outside_utility: float
    tau: float  # choice randomness, > 0


class Population(Contract):
    population_id: str
    seed: int
    pack: str
    attributes: list[str]
    segments: list[Segment]
    agents: list[Agent]
    geography: str = "SG"  # v2 optional, ISO country code
    evidence_snapshot_id: str | None = None  # v2 optional
    # optional: how it was made, e.g. {"source": "llm" | "template", "fallback_reason": ...}
    generation: dict | None = None


# ---------------------------------------------------------------- engine output
class Totals(Contract):
    count: int
    share: float
    p10: float
    p50: float
    p90: float


class Choice(Contract):
    agent_id: str
    segment: str
    choice: str
    prev_choice: str | None = None
    runner_up: str | None = None
    gap: float | None = None  # U(choice) - U(runner_up); can be negative (stochastic draw)
    components: dict[str, float]  # brand, feature, price, switch, risk (for the chosen option)
    p_choice: float | None = None  # optional: model probability of the chosen option (engine.py)
    locked: bool | None = None  # optional: True if a human override pinned this choice (engine.py)


class RunResult(Contract):
    run_id: str
    seed: int
    option_ids: list[str]
    totals: dict[str, Totals]
    choices: list[Choice]


# ---------------------------------------------------------------- glass-box
class Driver(Contract):
    term: str
    delta: float


class FeatureBoost(Contract):
    attr: str
    amount: float


class Flip(Contract):
    price_drop: float | None = None  # None = no price cut alone can flip this agent
    feature_boost: FeatureBoost | None = None
    note: str | None = None


class AgentExplain(Contract):
    agent_id: str
    segment: str
    choice: str
    runner_up: str | None = None
    top_drivers: list[Driver]
    narration: str
    flip: Flip | None = None


# ---------------------------------------------------------------- council and kit
class Risk(Contract):
    title: str
    evidence: str
    metric: str


class CompetitorReaction(Contract):
    competitor_id: str
    move: str
    effect_on_share: float


class Experiment(Contract):
    title: str
    hypothesis: str
    pass_threshold: str
    kind: Literal["landing", "survey", "interview", "offline", "telegram"]


class TrendContext(Contract):
    trend: str
    source_url: str
    used_in: str  # e.g. "risks[1]"


class CouncilOutput(Contract):
    run_id: str
    verdict: str
    confidence: Literal["low", "medium", "high"]
    fragility: float
    who_buys: list[str]
    who_rejects: list[str]
    risks: list[Risk]
    competitor_reaction: CompetitorReaction | None = None
    experiments: list[Experiment]
    trend_context: list[TrendContext] | None = None  # v2 optional


class OfflineKit(Contract):
    flyer: str
    checklist: list[str]


class KitAssets(Contract):
    landing_copy: str
    survey: list[str]
    interview_script: list[str]
    ad_variants: list[str]
    offline: OfflineKit | None = None
    telegram_variants: list[str]


class KitOutput(Contract):
    hypotheses: list[str]
    assets: KitAssets


# ---------------------------------------------------------------- intake
class ProductProfile(Contract):
    name: str
    description: str
    pack: str  # saas | cafe
    price: float
    currency: str = "SGD"
    target_customers: list[str] = Field(default_factory=list)
    features: dict[str, float] = Field(default_factory=dict)  # attribute -> 0..1
    geography: str = "SG"  # v2 optional, extracted by intake
    missing_assumptions: list[str] = Field(default_factory=list)


# name -> model, used by the schema exporter and the fixture tests
CONTRACTS: dict[str, type[Contract]] = {
    "Option": Option,
    "Population": Population,
    "RunResult": RunResult,
    "AgentExplain": AgentExplain,
    "CouncilOutput": CouncilOutput,
    "KitOutput": KitOutput,
    "ProductProfile": ProductProfile,
    "ResearchNote": ResearchNote,
    "TrendNote": TrendNote,
}
