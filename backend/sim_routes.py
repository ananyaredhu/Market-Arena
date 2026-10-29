"""Person A routes: population, Glass-Box explain, overrides, scenario compare.

Stubs return fixtures when MOCK=1. Replace the body of each route with the real implementation
(keep the path and the response shape, they are frozen contracts).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.common.fixtures import load_fixture
from backend.common.mock import mock_enabled
from backend.evidence.agent import research as research_evidence
from backend.evidence.resources import list_resources
from backend.evidence.store import council_context
from backend.evidence.store import load as load_snapshot
from backend.evidence.store import resources_dir as store_resources_dir
from backend.evidence.store import save as save_snapshot
from backend.glassbox.explain import AgentNotFound, summarize_flips
from backend.glassbox.explain import explain_agent as build_explain
from backend.population.generator import PopulationError
from backend.population.generator import generate_population as build_population
from backend.population.models import PopulationRequest
from backend.population.packs import PackError
from backend.scenarios import context as scenario_context
from backend.scenarios.compare import CompareError, CompareRequest, compare
from backend.scenarios.context import DEFAULT_PROJECT, RunContextError
from backend.scenarios.overrides import (
    OverrideError,
    OverrideRequest,
    add_override,
    audit_trail,
    remove_override,
)
from backend.scenarios.pricing import PriceSuggestRequest, PricingError, suggest_price
from backend.scenarios.state import adjusted_view

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


class ResearchRequest(BaseModel):
    pack: str = "saas"
    geography: str = "SG"
    product: dict | None = None


@router.post("/evidence/research")
def evidence_research(body: ResearchRequest | None = None):
    """Run the bounded web researcher and save the verified snapshot. Always answers 200 with a snapshot: when
    nothing could be found its `status` and `fallback_reason` say why and the original priors apply."""
    body = body or ResearchRequest()
    if mock_enabled():
        return load_fixture("trend_notes")
    snap = research_evidence(body.pack, body.geography, body.product)
    try:
        save_snapshot(snap)
    except OSError:
        pass
    return snap.model_dump(mode="json")


@router.get("/resources")
def resources_library(pack: str | None = None, geography: str | None = None, topic: str | None = None,
                      q: str | None = None):
    """The Resources library: surveys, news and competitor pages the researcher read, with verified quotes and urls.
    Reference only: nothing here ever changes a simulation prior. Filters: pack, geography, topic, q (text)."""
    items = list_resources(store_resources_dir(), pack, geography, topic, q)
    topics: dict[str, int] = {}
    for r in items:
        topics[r.topic] = topics.get(r.topic, 0) + 1
    return {"reference_only": True, "count": len(items), "topics": topics,
            "items": [r.model_dump() for r in items]}


@router.get("/evidence/{snapshot_id}")
def evidence_snapshot(snapshot_id: str, view: str = "full"):
    """A saved snapshot. `?view=council` returns it as research_notes and trend_notes for the Council."""
    try:
        snap = load_snapshot(snapshot_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=f"no evidence snapshot '{snapshot_id}'") from e
    return council_context(snap) if view == "council" else snap.model_dump(mode="json")


def get_context(project_id: str = DEFAULT_PROJECT, run_id: str | None = None):
    """The market for a run (C's stored run, else the shared fixtures); an unusable stored run is a 422."""
    try:
        return scenario_context.get_context(project_id, run_id)
    except RunContextError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


def _run_inputs(run_id: str, project_id: str = DEFAULT_PROJECT) -> tuple[dict, dict, list[dict]]:
    """(run_result, population, options) for a run, with the project's saved human overrides applied."""
    return adjusted_view(get_context(project_id, run_id), run_id)


@router.get("/runs/{run_id}/adjusted")
def adjusted_run(run_id: str, project_id: str = DEFAULT_PROJECT):
    """The run as it stands with the project's saved overrides applied (the Arena should show this one)."""
    run, _, _ = _run_inputs(run_id, project_id)
    return run


@router.get("/runs/{run_id}/agents/{agent_id}")
def explain_agent(run_id: str, agent_id: str, project_id: str = DEFAULT_PROJECT):
    """Glass-Box for one customer: drivers, flips and a verified plain-language reason (AgentExplain)."""
    run_result, population, options = _run_inputs(run_id, project_id)
    try:
        return build_explain(run_result, population, options, agent_id)
    except AgentNotFound as e:
        if mock_enabled():  # keep the UI alive in mock mode for ids the fixture does not contain
            return load_fixture("agent_explain") | {"agent_id": agent_id}
        raise HTTPException(status_code=404, detail=f"no agent '{agent_id}' in run '{run_id}'") from e


@router.get("/runs/{run_id}/flip-summary")
def flip_summary_route(run_id: str, project_id: str = DEFAULT_PROJECT):
    """Founder-level "what would flip the market": share of each segment that flips under a standard lever."""
    _, population, options = _run_inputs(run_id, project_id)
    return {"run_id": run_id, "rows": summarize_flips(population, options)}


# ---------------------------------------------------------------- overrides
@router.post("/overrides")
def add_override_route(body: OverrideRequest | None = None):
    """Lock a choice, edit a customer's parameter, tune a segment or exclude a customer.
    The override is trial-run first; if the engine refuses it, nothing is saved (422).
    Returns the saved override, the adjusted run (with prev_choice, so the Arena can animate) and a summary."""
    if body is None:
        if mock_enabled():  # bare POST in mock mode keeps the generic route checks working
            return {"status": "ok", "override": {}}
        raise HTTPException(status_code=422, detail="request body required")
    ctx = get_context(body.project_id, body.run_id)
    try:
        record, run = add_override(ctx, body)
    except OverrideError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return {"override": record, "run": run, "moved": sum(c["prev_choice"] != c["choice"] for c in run["choices"]),
            "audit": audit_trail(ctx)["summary"]}


@router.get("/overrides")
def list_overrides(project_id: str = DEFAULT_PROJECT, run_id: str | None = None):
    """The audit trail: what is machine-generated and which human adjustments sit on top."""
    return audit_trail(get_context(project_id, run_id))


@router.delete("/overrides/{override_id}")
def undo_override(override_id: str, project_id: str = DEFAULT_PROJECT, run_id: str | None = None):
    ctx = get_context(project_id, run_id)
    try:
        run = remove_override(ctx, override_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=f"no override '{override_id}'") from e
    except OverrideError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    return {"removed": override_id, "run": run, "audit": audit_trail(ctx)["summary"]}


# ---------------------------------------------------------------- price suggestion
@router.post("/pricing/suggest")
def pricing_suggest(body: PriceSuggestRequest | None = None):
    """Run the market at a series of prices and suggest where to start: the price with the best revenue index (or
    profit index when `cost` is given), the band of prices within 5% of it, and the full curve. Body (all optional):
    {project_id, run_id, cost, min_price, max_price, steps, seed, repeats}. Real prices from the Resources library
    are returned as reference only."""
    req = body or PriceSuggestRequest()
    try:
        return suggest_price(get_context(req.project_id, req.run_id), req)
    except PricingError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


# ---------------------------------------------------------------- scenario compare
@router.post("/scenarios/compare")
def compare_scenarios(body: CompareRequest | None = None):
    """Run the market twice (same customers, same seed) and change your strategy in B.
    Body (all optional): {changes: {option_id: {price, features, novelty}}, label_a, label_b, seed, repeats}.
    With no body, B cuts your price to 3."""
    req = body or CompareRequest()
    try:
        return compare(get_context(req.project_id, req.run_id), req)
    except CompareError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
