"""Where a scenario's inputs come from (Person A).

`get_context(project_id)` returns the population, options and run settings that overrides and scenario compare
work on. TODAY these come from the shared fixtures, so the demo is consistent end to end. When Person C's run
storage exists, change ONLY this function to load the project's real population, options and seed.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass

from backend.common.fixtures import load_fixture

DEFAULT_PROJECT = "proj_1"


@dataclass
class ScenarioContext:
    project_id: str
    population: dict  # Population contract (agents, segments, attributes, ...)
    options: list[dict]  # Option contract list: you, competitors, outside
    seed: int = 42
    repeats: int = 30
    currency: str = "SGD"
    period: str = "month"  # what a price is per ("month" for SaaS, "visit" for cafe)

    @property
    def agents(self) -> list[dict]:
        return self.population["agents"]

    @property
    def you_id(self) -> str:
        return next((o["id"] for o in self.options if o.get("role") == "you"), "you")


def get_context(project_id: str = DEFAULT_PROJECT) -> ScenarioContext:
    """Swap point for C's storage. Returns fresh copies, so callers may edit them freely."""
    return ScenarioContext(
        project_id=project_id,
        population=copy.deepcopy(load_fixture("population_saas")),
        options=copy.deepcopy(load_fixture("options_saas")),
    )
