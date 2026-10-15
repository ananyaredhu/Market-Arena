"""Person A routes: population, Glass-Box explain, overrides, scenario compare.

Stubs return fixtures when MOCK=1. Replace the body of each route with the real implementation
(keep the path and the response shape, they are frozen contracts).
"""
from __future__ import annotations

import copy

from fastapi import APIRouter, HTTPException

from backend.common.fixtures import load_fixture
from backend.common.mock import mock_enabled, not_built
from backend.glassbox.explain import AgentNotFound, summarize_flips
from backend.glassbox.explain import explain_agent as build_explain
from backend.population.generator import PopulationError
from backend.population.generator import generate_population as build_population
from backend.population.models import PopulationRequest
from backend.population.packs import PackError

router = APIRouter(tags=["simulation (A)"])


@router.post("/population/generate")
def generate_population(body: PopulationRequest | None = None):
    """Body (all optional): {pack, n_agents, seed, geography, product}. Returns a Population."""
    if mock_enabled():
        return load_fixture("population_saas")
    try:
        return build_population(body or PopulationRequest())
    except PackError as e:
        raise HTTPException(status_code=404, detail=str(e).splitlines()[0]) from e
    except PopulationError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


def _run_inputs(run_id: str) -> tuple[dict, dict, list[dict]]:
    """(run_result, population, options) for a run. Until C's run storage exists these come from the shared
    fixtures, like the Council route does; swap this one function when runs are stored."""
    options = copy.deepcopy(load_fixture("options_saas"))
    if run_id.endswith("price3"):  # the fixture run where "you" cut the price to 3
        options[0]["price"] = 3.0
        return load_fixture("run_result_price3"), load_fixture("population_saas"), options
    return load_fixture("run_result"), load_fixture("population_saas"), options


@router.get("/runs/{run_id}/agents/{agent_id}")
def explain_agent(run_id: str, agent_id: str):
    """Glass-Box for one customer: drivers, flips and a verified plain-language reason (AgentExplain)."""
    run_result, population, options = _run_inputs(run_id)
    try:
        return build_explain(run_result, population, options, agent_id)
    except AgentNotFound as e:
        if mock_enabled():  # keep the UI alive in mock mode for ids the fixture does not contain
            return load_fixture("agent_explain") | {"agent_id": agent_id}
        raise HTTPException(status_code=404, detail=f"no agent '{agent_id}' in run '{run_id}'") from e


@router.get("/runs/{run_id}/flip-summary")
def flip_summary_route(run_id: str):
    """Founder-level "what would flip the market": share of each segment that flips under a standard lever."""
    _, population, options = _run_inputs(run_id)
    return {"run_id": run_id, "rows": summarize_flips(population, options)}


@router.post("/overrides")
def apply_override(body: dict | None = None):
    if mock_enabled():
        return {"status": "ok", "override": body or {}}
    raise not_built("POST /overrides")


@router.post("/scenarios/compare")
def compare_scenarios(body: dict | None = None):
    if mock_enabled():
        return {"a": load_fixture("run_result"), "b": load_fixture("run_result_price3")}
    raise not_built("POST /scenarios/compare")
