"""The market as it stands NOW: the project's machine-generated population plus its saved human overrides.

`adjusted_view(ctx, run_id)` returns (run_result, population, options) with overrides applied. The Arena, the
Glass-Box explain route and the adjusted-run route all use it, so every screen shows the same adjusted market.

For a stored run (ctx.run_id set) the market is the run's own, and the result carries that run id. For the fixtures,
the run id "run_42_price3" is the scenario where your price is cut to 3; any other id is the base scenario.
"""
from __future__ import annotations

import copy

from backend.engine.engine import run_scenario
from backend.scenarios.context import ScenarioContext
from backend.scenarios.overrides import OverrideStore, apply_overrides, get_store

PRICE_CUT_FIXTURE = 3.0


def adjusted_view(
    ctx: ScenarioContext, run_id: str, store: OverrideStore | None = None
) -> tuple[dict, dict, list[dict]]:
    overrides = (store or get_store()).list(ctx.project_id)
    applied = apply_overrides(ctx, overrides)
    population = {**ctx.population, "agents": applied.agents}

    base = run_scenario(applied.agents, ctx.options, ctx.seed, ctx.repeats, locks=applied.locks)
    run, options = base, ctx.options
    if ctx.run_id:
        run["run_id"] = ctx.run_id
    elif run_id.endswith("price3"):
        options = copy.deepcopy(ctx.options)
        next(o for o in options if o["id"] == ctx.you_id)["price"] = PRICE_CUT_FIXTURE
        run = run_scenario(applied.agents, options, ctx.seed, ctx.repeats, locks=applied.locks, prev=base)
        run["run_id"] = run_id
    run["overrides_applied"] = len(overrides)
    return run, population, options
