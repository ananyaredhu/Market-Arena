"""Typed shapes for packs and segment priors (Person A).

These are internal to the population generator, not shared contracts. The generator's OUTPUT is the shared
`Population` contract (backend/common/contracts.py). The same `SegmentSpec` is used for the pack template priors
and for what the LLM proposes, so a failed LLM answer can be swapped for the template without conversion.
"""
from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator


def _ordered(r: tuple[float, float]) -> tuple[float, float]:
    if r[0] > r[1]:
        raise ValueError(f"range low {r[0]} is above high {r[1]}")
    return r


Range = Annotated[tuple[float, float], AfterValidator(_ordered)]


class SegmentPriors(BaseModel):
    """Uniform sampling ranges for one segment. Same layout as `priors:` in packs/*.yaml."""

    model_config = ConfigDict(extra="ignore")

    budget: Range
    alpha: Range
    w: dict[str, Range]  # attribute -> weight range
    switch: Range
    risk: Range
    outside_utility: Range
    tau: Range
    brand: dict[str, Range] = Field(default_factory=dict)  # option id -> affinity range (missing = 0)
    incumbent: dict[str, float]  # option id -> probability weight

    @model_validator(mode="after")
    def _checks(self) -> SegmentPriors:
        if self.tau[0] <= 0:
            raise ValueError("tau must be > 0")
        if self.budget[0] < 0:
            raise ValueError("budget cannot be negative")
        if not self.incumbent or any(v < 0 for v in self.incumbent.values()) or sum(self.incumbent.values()) <= 0:
            raise ValueError("incumbent needs non-negative weights with a positive sum")
        return self


class SegmentSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: str
    share: float = Field(gt=0, le=1)
    hostile: bool = False
    evidence: str = "illustrative_assumption"  # mapped to the contract tag when the Population is built
    priors: SegmentPriors


class PackSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    pack: str
    label: str = ""
    currency: str = "SGD"
    attributes: list[str]
    outside_id: str = "outside"
    min_outside_share: float = 0.10
    max_avg_budget: float | None = None  # optional hard cap; otherwise derived from the template (see validators)
    segments: list[SegmentSpec]
    competitors: list[dict] = Field(default_factory=list)  # full option specs (id, label, price, features, ...)
    demo_product: dict | None = None  # the pack's illustrative "you" option, used for sanity runs

    @model_validator(mode="after")
    def _checks(self) -> PackSpec:
        total = sum(s.share for s in self.segments)
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"segment shares sum to {total:.3f}, expected 1.0")
        attrs = set(self.attributes)
        for s in self.segments:
            if set(s.priors.w) != attrs:
                raise ValueError(
                    f"segment '{s.id}' weights {sorted(s.priors.w)} do not match attributes {sorted(attrs)}"
                )
        return self


class PriorsProposal(BaseModel):
    """What the LLM must return: the segments (with ranges and shares) for this product and market."""

    model_config = ConfigDict(extra="ignore")

    segments: list[SegmentSpec]


class PopulationRequest(BaseModel):
    """Body of POST /population/generate. Every field is optional so an empty body works."""

    pack: str = "saas"
    n_agents: int = Field(default=300, ge=10, le=5000)
    seed: int = 42
    geography: str = "SG"
    product: dict | None = None  # ProductProfile-like dict from intake; used only to brief the LLM
