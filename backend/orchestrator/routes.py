"""Project orchestration routes and fixture-compatible mock responses."""
from __future__ import annotations

import asyncio
import copy
import json
import math
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from backend.common.contracts import Option, Population, RunResult
from backend.common.fixtures import load_fixture
from backend.common.mock import mock_enabled, not_built
from backend.engine.engine import run_scenario as run_engine
from backend.intake.projects import ProjectCreateRequest, create_persisted_project, get_persisted_project
from backend.orchestrator import storage
from backend.population.generator import PopulationError, generate_population
from backend.population.localise import localised
from backend.population.models import PopulationRequest
from backend.population.packs import PackError, load_pack

router = APIRouter(tags=["intake and runs (C)"])
_ID_ALLOCATION_ATTEMPTS = 8


class ScenarioCreateRequest(BaseModel):
    project_id: str
    seed: int = Field(default=42, ge=0, le=2**32 - 1)
    n_agents: int = Field(default=300, ge=10, le=5000)
    repeats: int = Field(default=30, ge=1, le=500)
    options: list[dict[str, Any]] | None = None
    research: bool = False  # run the web evidence researcher first (needs SEARXNG_URL and a live LLM)
    evidence_snapshot_id: str | None = None  # or reuse a saved evidence snapshot
    price_base_year: int | None = 2024  # the year the pack's budgets are in; budgets move with consumer prices from it

    @field_validator("project_id")
    @classmethod
    def project_id_not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("project_id must not be blank")
        return value


def _build_options(project: dict, pack) -> list[dict[str, Any]]:
    profile = project["profile"]
    if profile.get("price", 0) <= 0:
        raise HTTPException(422, "project needs a positive product price before it can be simulated")
    attributes = pack.attributes
    product_features = profile.get("features", {})
    if set(product_features) != set(attributes):
        raise HTTPException(422, "project product features do not match its industry pack")
    product = {
        "id": "you",
        "label": profile["name"],
        "role": "you",
        "price": profile["price"],
        "features": [product_features[attr] for attr in attributes],
        "novelty": 0.5,
    }
    outside = {"id": pack.outside_id, "label": "Do nothing", "role": "outside"}
    # Competitor archetypes and population priors are pack assumptions, not observed market data.
    return [product, *(copy.deepcopy(pack.competitors)), outside]


def _validate_options(raw_options: list[dict[str, Any]], pack) -> list[dict[str, Any]]:
    if not isinstance(raw_options, list) or not raw_options:
        raise HTTPException(422, "options must be a non-empty list")
    try:
        options = [Option.model_validate(item).model_dump(mode="json") for item in raw_options]
    except Exception as exc:
        raise HTTPException(422, f"invalid scenario option: {exc}") from exc
    ids = [option["id"] for option in options]
    if len(ids) != len(set(ids)):
        raise HTTPException(422, "scenario option ids must be unique")
    by_id = {option["id"]: option for option in options}
    if "you" not in by_id or by_id["you"]["role"] != "you":
        raise HTTPException(422, "scenario options must include product option 'you'")
    if pack.outside_id not in by_id or by_id[pack.outside_id]["role"] != "outside":
        raise HTTPException(422, f"scenario options must include outside option '{pack.outside_id}'")
    expected_roles = {"you": "you", pack.outside_id: "outside"}
    expected_roles.update({item["id"]: "competitor" for item in pack.competitors})
    known = set(expected_roles)
    unknown = set(ids) - known
    if unknown:
        raise HTTPException(422, f"option ids are incompatible with pack '{pack.pack}': {sorted(unknown)}")
    expected_attrs = len(pack.attributes)
    for option in options:
        if option["role"] != expected_roles[option["id"]]:
            expected_role = expected_roles[option["id"]]
            raise HTTPException(
                422,
                f"option '{option['id']}' must have role '{expected_role}' for pack '{pack.pack}'",
            )
        price = option["price"]
        if not math.isfinite(price) or price < 0:
            raise HTTPException(422, f"option '{option['id']}' price must be a finite non-negative number")
        if not math.isfinite(option["novelty"]):
            raise HTTPException(422, f"option '{option['id']}' novelty must be a finite number")
        if option["role"] != "outside" and len(option["features"]) != expected_attrs:
            raise HTTPException(
                422,
                f"option '{option['id']}' needs {expected_attrs} feature values for pack '{pack.pack}'",
            )
        if any(not math.isfinite(value) for value in option["features"]):
            raise HTTPException(422, f"option '{option['id']}' features must be finite numbers")
    return options


@router.post("/projects")
def create_project(body: ProjectCreateRequest | None = None):
    if mock_enabled():
        return {"id": "proj_1", "profile": load_fixture("product_profile_saas"),
                "competitors": load_fixture("competitors_saas")}
    if body is None:
        raise HTTPException(status_code=422, detail="request body is required")
    return create_persisted_project(body)


@router.get("/projects/{project_id}")
def get_project(project_id: str):
    if mock_enabled():
        return {"id": project_id, "profile": load_fixture("product_profile_saas"),
                "competitors": load_fixture("competitors_saas")}
    return get_persisted_project(project_id)


@router.post("/scenarios")
def create_scenario(body: ScenarioCreateRequest | None = None):
    if mock_enabled():
        return {"id": "scn_1", "project_id": "proj_1", "pack": "saas",
                "seed": load_fixture("run_result")["seed"], "options": load_fixture("options_saas")}
    if body is None:
        raise HTTPException(422, "request body is required")
    project = get_persisted_project(body.project_id)
    try:
        pack = load_pack(project["profile"]["pack"])
    except (KeyError, PackError) as exc:
        raise HTTPException(422, f"project has an unsupported industry pack: {exc}") from exc
    profile = project["profile"]
    geography = profile.get("geography") or "SG"
    # The founder's currency is kept; the pack's own money assumptions (rival prices) are put into it (localise.py).
    market, _ = localised(pack, profile.get("currency"), geography)
    options = _validate_options(body.options if body.options is not None else _build_options(project, market), pack)
    pop_request = PopulationRequest(
        pack=pack.pack,
        n_agents=body.n_agents,
        seed=body.seed,
        geography=geography,
        currency=profile.get("currency"),
        product=profile,
        research=body.research,
        evidence_snapshot_id=body.evidence_snapshot_id,
        price_base_year=body.price_base_year,
    )
    try:
        population = Population.model_validate(generate_population(pop_request)).model_dump(mode="json")
    except PackError as exc:
        raise HTTPException(422, str(exc)) from exc
    except PopulationError as exc:
        raise HTTPException(422, f"population could not be generated: {exc}") from exc
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, f"invalid population configuration: {exc}") from exc
    scenario = {
        "project_id": project["id"],
        "pack": pack.pack,
        "seed": body.seed,
        "n_agents": body.n_agents,
        "repeats": body.repeats,
        "options": options,
        "population": population,
        "assumptions": {
            "population": population.get("generation", {
                "source": "pack_template",
                "evidence": "illustrative_assumption",
            }),
            "competitors": "industry pack archetypes; illustrative assumptions, not observed market data",
        },
    }
    for _ in range(_ID_ALLOCATION_ATTEMPTS):
        scenario_id = storage.new_scenario_id()
        scenario["id"] = scenario_id
        try:
            storage.save_scenario(scenario)
            break
        except storage.RecordCollisionError:
            continue
    else:
        raise HTTPException(503, "could not allocate a unique scenario id; retry the request")
    return {"id": scenario_id, "project_id": project["id"], "pack": pack.pack,
            "seed": body.seed, "options": options, "assumptions": scenario["assumptions"]}


@router.post("/scenarios/{scenario_id}/run")
def run_scenario_route(scenario_id: str):
    if mock_enabled():
        return {"run_id": load_fixture("run_result")["run_id"], "project_id": "proj_1",
                "scenario_id": scenario_id, "status": "done"}
    try:
        scenario = storage.load_scenario(scenario_id)
    except storage.StoredDataError as exc:
        raise HTTPException(422, str(exc)) from exc
    if scenario is None:
        raise HTTPException(404, f"scenario '{scenario_id}' was not found")
    project = get_persisted_project(scenario["project_id"])
    if project["profile"]["pack"] != scenario["pack"]:
        raise HTTPException(422, "stored scenario pack no longer matches its project")
    try:
        raw_result = run_engine(
            scenario["population"]["agents"], scenario["options"],
            seed=scenario["seed"], repeats=scenario["repeats"],
        )
        result = None
        for _ in range(_ID_ALLOCATION_ATTEMPTS):
            run_id = storage.new_run_id()
            candidate = RunResult.model_validate({**raw_result, "run_id": run_id}).model_dump(mode="json")
            bundle = {
                # Required by Person B's run_inputs.load_bundle/_from_bundle interface.
                "run_id": run_id,
                "project_id": project["id"],
                "pack": scenario["pack"],
                "population": scenario["population"],
                "options": scenario["options"],
                "run_result": candidate,
                # Orchestration metadata is additive; Council/Kit ignore it.
                "scenario_id": scenario_id,
                "seed": scenario["seed"],
                "status": "done",
                "assumptions": scenario["assumptions"],
            }
            try:
                storage.save_run_bundle(bundle)
                result = candidate
                break
            except storage.RecordCollisionError:
                continue
        if result is None:
            raise HTTPException(503, "could not allocate a unique run id; retry the request")
    except HTTPException:
        raise
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(422, f"scenario could not be evaluated: {exc}") from exc
    except Exception as exc:  # engine failures are surfaced; never replaced by a fixture
        raise HTTPException(502, f"simulation engine failed: {exc}") from exc
    return {"run_id": run_id, "scenario_id": scenario_id, "project_id": project["id"], "status": "done"}


@router.get("/runs/{run_id}")
def get_run(run_id: str):
    if mock_enabled():
        return load_fixture("run_result_price3" if run_id.endswith("price3") else "run_result")
    try:
        bundle = storage.load_run_bundle(run_id)
    except storage.StoredDataError as exc:
        raise HTTPException(422, str(exc)) from exc
    if bundle is None:
        raise HTTPException(404, f"run '{run_id}' was not found")
    return bundle["run_result"]


@router.get("/runs/{run_id}/stream")
async def stream_run(run_id: str):
    if not mock_enabled():
        # Runs execute synchronously; no live progress stream exists to report truthfully.
        raise not_built("GET /runs/{id}/stream (real-time streaming is deferred for synchronous runs)")

    async def events():
        for pct in (25, 50, 75, 100):
            yield f"event: progress\ndata: {json.dumps({'run_id': run_id, 'percent': pct})}\n\n"
            await asyncio.sleep(0.05)
        yield f"event: result\ndata: {json.dumps(load_fixture('run_result'))}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
