"""Person C routes: projects, scenarios, runs and the SSE stream.

Stubs return fixtures when MOCK=1. The real version stores projects/scenarios/runs (SQLite or
JSON), calls run_scenario in a background task and streams progress and frames.
"""
import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from backend.common.fixtures import load_fixture
from backend.common.mock import mock_enabled, not_built

router = APIRouter(tags=["intake and runs (C)"])


@router.post("/projects")
def create_project(body: dict | None = None):
    if mock_enabled():
        return {"id": "proj_1", "profile": load_fixture("product_profile_saas"),
                "competitors": load_fixture("competitors_saas")}
    raise not_built("POST /projects")


@router.get("/projects/{project_id}")
def get_project(project_id: str):
    if mock_enabled():
        return {"id": project_id, "profile": load_fixture("product_profile_saas"),
                "competitors": load_fixture("competitors_saas")}
    raise not_built("GET /projects/{id}")


@router.post("/scenarios")
def create_scenario(body: dict | None = None):
    if mock_enabled():
        return {"id": "scn_1", "options": load_fixture("options_saas")}
    raise not_built("POST /scenarios")


@router.post("/scenarios/{scenario_id}/run")
def run_scenario_route(scenario_id: str):
    if mock_enabled():
        return {"run_id": load_fixture("run_result")["run_id"], "status": "done"}
    raise not_built("POST /scenarios/{id}/run")


@router.get("/runs/{run_id}")
def get_run(run_id: str):
    if mock_enabled():
        return load_fixture("run_result_price3" if run_id.endswith("price3") else "run_result")
    raise not_built("GET /runs/{id}")


@router.get("/runs/{run_id}/stream")
async def stream_run(run_id: str):
    if not mock_enabled():
        raise not_built("GET /runs/{id}/stream")

    async def events():
        for pct in (25, 50, 75, 100):
            yield f"event: progress\ndata: {json.dumps({'run_id': run_id, 'percent': pct})}\n\n"
            await asyncio.sleep(0.05)
        yield f"event: result\ndata: {json.dumps(load_fixture('run_result'))}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
