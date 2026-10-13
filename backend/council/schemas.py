"""Person B schema helpers — re-export frozen shared contracts.

Do not fork field names. Optional extras (limitations, engine_source, tracking_plan,
price_board_test) are allowed because contracts use ``extra="allow"``. Propose any
new shared fields via contracts/CHANGELOG.md with team approval.
"""
from __future__ import annotations

from typing import List

from pydantic import Field

from backend.common.contracts import (
    Choice,
    CompetitorReaction,
    Contract,
    CouncilOutput,
    Experiment,
    KitAssets,
    KitOutput,
    OfflineKit,
    Risk,
    RunResult,
    Totals,
    TrendContext,
)

# Alias kept for older Person B call sites
KitOffline = OfflineKit


class TrackingPlan(Contract):
    """PROPOSED optional kit field — not yet in frozen KitAssets."""

    metrics: List[str] = Field(min_length=1)
    decision_rule: str


__all__ = [
    "Choice",
    "CompetitorReaction",
    "CouncilOutput",
    "Experiment",
    "KitAssets",
    "KitOffline",
    "KitOutput",
    "Risk",
    "RunResult",
    "Totals",
    "TrackingPlan",
    "TrendContext",
]
