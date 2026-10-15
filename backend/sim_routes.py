"""Person A routes: population, Glass-Box explain, overrides, scenario compare.

Stubs return fixtures when MOCK=1. Replace the body of each route with the real implementation
(keep the path and the response shape, they are frozen contracts).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.common.fixtures import load_fixture
from backend.common.mock import mock_enabled, not_built
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


@router.get("/runs/{run_id}/agents/{agent_id}")
def explain_agent(run_id: str, agent_id: str):
    if mock_enabled():
        return load_fixture("agent_explain") | {"agent_id": agent_id}
    raise not_built("GET /runs/{id}/agents/{agent_id}")


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
