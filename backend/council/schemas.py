"""Pydantic models for the Council and Kit contracts.

Shapes follow MARKET_ARENA_Team_Work_Split.md section 4.2. Fields marked
PROPOSED are optional additions that need team approval before they are
promoted to /contracts.
"""
from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

Confidence = Literal["low", "medium", "high"]
ExperimentKind = Literal["landing", "survey", "interview", "offline", "telegram"]


def _non_empty(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("must be a non-empty string")
    return value


# ---------------------------------------------------------------- RunResult (input, owned by A/C)


class TotalsEntry(BaseModel):
    model_config = ConfigDict(extra="allow")
    count: Optional[int] = None
    share: float
    p10: Optional[float] = None
    p50: Optional[float] = None
    p90: Optional[float] = None


class ChoiceEntry(BaseModel):
    model_config = ConfigDict(extra="allow")
    agent_id: str
    segment: Optional[str] = None
    choice: str
    prev_choice: Optional[str] = None
    runner_up: Optional[str] = None
    gap: Optional[float] = None
    components: Dict[str, float] = Field(default_factory=dict)


class RunResult(BaseModel):
    """Read-only view of the engine output. Extra fields are preserved."""

    model_config = ConfigDict(extra="allow")
    run_id: str
    seed: int
    option_ids: List[str]
    totals: Dict[str, TotalsEntry]
    choices: List[ChoiceEntry] = Field(default_factory=list)


# ---------------------------------------------------------------- CouncilOutput (owned by B)


class Risk(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    evidence: str
    metric: str

    @field_validator("title", "evidence", "metric")
    @classmethod
    def _check(cls, v: str) -> str:
        return _non_empty(v)


class CompetitorReaction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    competitor_id: str
    move: str
    effect_on_share: float


class Experiment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    hypothesis: str
    pass_threshold: str
    kind: ExperimentKind

    @field_validator("title", "hypothesis", "pass_threshold")
    @classmethod
    def _check(cls, v: str) -> str:
        return _non_empty(v)


class CouncilOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str
    verdict: str
    confidence: Confidence
    fragility: float = Field(ge=0.0, le=1.0)
    who_buys: List[str]
    who_rejects: List[str]
    risks: List[Risk] = Field(max_length=3)
    # Nullable when no competitor exists or no move reduces our share.
    competitor_reaction: Optional[CompetitorReaction]
    experiments: List[Experiment] = Field(max_length=3)
    # PROPOSED optional fields
    limitations: List[str] = Field(default_factory=list)
    engine_source: Optional[str] = None

    @field_validator("verdict")
    @classmethod
    def _check(cls, v: str) -> str:
        return _non_empty(v)


# ---------------------------------------------------------------- KitOutput (owned by B)


class TrackingPlan(BaseModel):
    """PROPOSED optional field: metrics to record and the decision rule."""

    model_config = ConfigDict(extra="forbid")
    metrics: List[str] = Field(min_length=1)
    decision_rule: str


class KitOffline(BaseModel):
    model_config = ConfigDict(extra="forbid")
    flyer: str
    checklist: List[str]
    # PROPOSED optional field
    price_board_test: List[str] = Field(default_factory=list)


class KitAssets(BaseModel):
    model_config = ConfigDict(extra="forbid")
    landing_copy: str
    survey: List[str]
    interview_script: List[str]
    ad_variants: List[str]
    offline: KitOffline
    telegram_variants: List[str]
    # PROPOSED optional field
    tracking_plan: Optional[TrackingPlan] = None


class KitOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hypotheses: List[str]
    assets: KitAssets


def json_schemas() -> Dict[str, dict]:
    """JSON Schemas proposed for promotion to /contracts."""
    return {
        "council_output.schema.json": CouncilOutput.model_json_schema(),
        "kit_output.schema.json": KitOutput.model_json_schema(),
    }
