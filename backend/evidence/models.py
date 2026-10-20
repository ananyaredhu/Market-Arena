"""Shapes for the evidence researcher (Person A). Master Plan 4.6.

A `Finding` is one fact the researcher claims to have read in a source: it only survives if its quote is really in
that source (see verify.py). Findings that map to a model parameter can adjust the population priors; everything
else is kept as cited context (research notes, trend notes) for the Council, the narration and the Experiment Kit.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# kinds that can change a prior or an option, versus context that is only displayed and cited
PARAMETER_KINDS = ("competitor_price", "segment_budget", "free_tool_adoption")
Kind = Literal[
    "competitor_price", "segment_budget", "free_tool_adoption", "market_size", "regulation", "channel", "other"
]
TrendEffect = Literal["budget_down", "budget_up", "price_sensitivity_up", "price_sensitivity_down", "none"]


class Finding(BaseModel):
    model_config = ConfigDict(extra="ignore")

    kind: Kind
    subject: str | None = None  # competitor id (competitor_price), segment id (segment_budget), or None for "all"
    claim: str = Field(max_length=300)  # one plain sentence
    value: float | None = None  # the headline number, in the unit below
    low: float | None = None  # optional range
    high: float | None = None
    unit: str | None = None  # e.g. "per month", "per visit", "share"
    currency: str | None = None
    quote: str  # verbatim text from the source that backs the claim
    url: str  # must be a source the researcher actually opened or was shown


class TrendNote(BaseModel):
    model_config = ConfigDict(extra="ignore")

    note: str = Field(max_length=300)
    quote: str
    url: str
    effect: TrendEffect = "none"
    segments: list[str] | None = None  # None = all segments


class Extraction(BaseModel):
    """What the model returns at the end of a research run (before verification)."""

    model_config = ConfigDict(extra="ignore")

    findings: list[Finding] = Field(default_factory=list)
    trend_notes: list[TrendNote] = Field(default_factory=list)


class Dropped(BaseModel):
    what: str  # the claim or note that was dropped
    url: str | None = None
    reason: str


class Step(BaseModel):
    """One tool call in the research trace, kept so the user can see how the evidence was gathered."""

    n: int
    action: Literal["search", "open", "finish", "world_bank"]
    detail: str
    result: str  # short summary, never the page text


class Economics(BaseModel):
    country: str
    iso: str
    gdp_pc_ppp: float
    year: int
    baseline_iso: str
    baseline_gdp_pc_ppp: float
    budget_scale: float  # multiplier applied to every segment's budget range, bounded
    source_url: str


class EvidenceSnapshot(BaseModel):
    """Everything one research run produced. Saved with the population so a re-run reuses the same evidence."""

    snapshot_id: str
    created_at: str
    pack: str
    geography: str
    status: Literal["ok", "partial", "empty", "failed", "off"]
    fallback_reason: str | None = None  # why the original (no-evidence) plan is used, when it is
    findings: list[Finding] = Field(default_factory=list)  # verified only
    trend_notes: list[TrendNote] = Field(default_factory=list)  # verified only
    dropped: list[Dropped] = Field(default_factory=list)
    economics: Economics | None = None
    trace: list[Step] = Field(default_factory=list)
    stats: dict = Field(default_factory=dict)  # searches, opens, seconds, llm_calls
