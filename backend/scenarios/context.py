"""Where a scenario's inputs come from (Person A).

`get_context(project_id, run_id)` returns the population, options and run settings that overrides, scenario compare,
the Arena and the Glass-Box work on. A run id that C has stored (`data/runs/<run_id>.json`) loads that run's own
market: its population, options and seed, plus the scenario's repeats and the pack's currency and period. Any other
run id (or none) uses the shared fixtures, so the demo, mock mode and the fixture ids run_42 / run_42_price3 still work.

Overrides stay per PROJECT: a stored run supplies its project id, and that project's saved corrections apply to it.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass

from backend.common.fixtures import load_fixture
from backend.orchestrator import storage
from backend.population.packs import PackError, load_pack

DEFAULT_PROJECT = "proj_1"
DEFAULT_REPEATS = 30


class RunContextError(ValueError):
    """A stored run exists but cannot be used (malformed or unknown pack). Never silently replaced by a fixture."""


@dataclass
class ScenarioContext:
    project_id: str
    population: dict  # Population contract (agents, segments, attributes, ...)
    options: list[dict]  # Option contract list: you, competitors, outside
    seed: int = 42
    repeats: int = 30
    currency: str = "SGD"
    period: str = "month"  # what a price is per ("month" for SaaS, "visit" for cafe)
    run_id: str | None = None  # set when this context was loaded from a stored run (None for the fixture market)

    @property
    def agents(self) -> list[dict]:
        return self.population["agents"]

    @property
    def you_id(self) -> str:
        return next((o["id"] for o in self.options if o.get("role") == "you"), "you")


def _period(pack) -> str:
    return pack.period or (pack.price_unit or "per month").removeprefix("per ").strip() or "month"


def _stored_context(run_id: str) -> ScenarioContext | None:
    try:
        bundle = storage.load_run_bundle(run_id)
    except storage.StoredDataError as e:
        raise RunContextError(str(e)) from e
    if bundle is None:
        return None
    try:
        pack = load_pack(bundle["pack"])
    except PackError as e:
        raise RunContextError(f"run '{run_id}' uses an unknown industry pack: {e}") from e
    repeats = DEFAULT_REPEATS
    if bundle.get("scenario_id"):  # repeats is saved on the scenario, not the run bundle
        try:
            repeats = int((storage.load_scenario(bundle["scenario_id"]) or {}).get("repeats", DEFAULT_REPEATS))
        except (storage.StoredDataError, TypeError, ValueError):
            pass
    return ScenarioContext(
        project_id=bundle["project_id"],
        population=bundle["population"],
        options=bundle["options"],
        seed=int(bundle.get("seed", bundle["run_result"].get("seed", 42))),
        repeats=repeats,
        currency=pack.currency,
        period=_period(pack),
        run_id=run_id,
    )


def get_context(project_id: str = DEFAULT_PROJECT, run_id: str | None = None) -> ScenarioContext:
    """The market for a stored run, else the shared fixture market. Returns fresh copies, safe to edit."""
    if run_id:
        stored = _stored_context(run_id)
        if stored is not None:
            return stored
    return ScenarioContext(
        project_id=project_id,
        population=copy.deepcopy(load_fixture("population_saas")),
        options=copy.deepcopy(load_fixture("options_saas")),
    )
