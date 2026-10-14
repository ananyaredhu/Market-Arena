"""Person B routes: Council verdict and Experiment Kit.

Mock mode may answer the shared demo run ids. It does not stamp an arbitrary
run id onto fixture JSON. Live mode never substitutes ``fixtures/council.json``
or ``fixtures/kit.json`` for a failed computation.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

from backend.common.contracts import CouncilOutput, RunResult
from backend.common.fixtures import load_fixture
from backend.common.mock import mock_enabled
from backend.council.run_inputs import ResolutionError, resolve_run
from backend.council.service import run_council, run_kit
from backend.kit.generator import KitValidationError
from backend.kit.packs import UnknownPackError

logger = logging.getLogger(__name__)
router = APIRouter(tags=["council and kit (B)"])

_DEMO_LIMIT = (
    "Shared demo scenario. Canonical choices were checked against engine.py. "
    "This run is not stored against a project, and it is not a forecast of real demand."
)


class CouncilRequest(BaseModel):
    run_result: Optional[RunResult] = None
    population: Optional[dict] = None
    options: Optional[List[dict]] = None
    pack: str = "saas"
    project_id: Optional[str] = None
    seed: Optional[int] = None
    trend_notes: Optional[List[dict]] = None
    research_notes: Optional[List[dict]] = None


class KitRequest(BaseModel):
    council: Optional[CouncilOutput] = None
    options: Optional[List[dict]] = None
    pack: Optional[str] = None
    project_id: Optional[str] = None
    population: Optional[dict] = None
    run_result: Optional[RunResult] = None
    seed: Optional[int] = None
    trend_notes: Optional[List[dict]] = None
    research_notes: Optional[List[dict]] = None


def _payload(result: dict, resolved) -> dict:
    council = result["council"]
    data = council.model_dump()
    data["measured"] = result["measured"]
    data["scenario_origin"] = resolved.origin
    data["project_id"] = resolved.project_id
    if resolved.origin == "demo":
        data["limitations"] = list(data.get("limitations") or []) + [_DEMO_LIMIT]
    return data


def _compute_council(run_id: str, body: Optional[CouncilRequest]) -> dict:
    resolved = resolve_run(run_id, body, live=not mock_enabled())
    result = run_council(
        resolved.run_result,
        resolved.population,
        resolved.options,
        resolved.pack,
        trend_notes=resolved.trend_notes,
        research_notes=resolved.research_notes,
    )
    payload = _payload(result, resolved)
    if payload.get("run_id") != run_id:
        raise ResolutionError(409, "council run_id does not match the requested run")
    return payload


def _compute_kit(run_id: str, body: Optional[KitRequest]) -> dict:
    if body is not None and body.council is not None:
        if body.council.run_id != run_id:
            raise ResolutionError(409, f"kit council.run_id is {body.council.run_id}, not {run_id}")
        if body.options is not None:
            pack = body.pack or "saas"
            options = body.options
            project_id = body.project_id
            origin = "request"
        else:
            resolved = resolve_run(run_id, body, live=not mock_enabled())
            pack = body.pack or resolved.pack
            options = resolved.options
            project_id = resolved.project_id
            origin = resolved.origin
        kit = run_kit(body.council, pack, options)
    else:
        resolved = resolve_run(run_id, body, live=not mock_enabled())
        result = run_council(
            resolved.run_result,
            resolved.population,
            resolved.options,
            resolved.pack,
            trend_notes=resolved.trend_notes,
            research_notes=resolved.research_notes,
        )
        if result["council"].run_id != run_id:
            raise ResolutionError(409, "council run_id does not match the requested run")
        kit = run_kit(result["council"], resolved.pack, resolved.options)
        project_id = resolved.project_id
        origin = resolved.origin
    data = kit.model_dump()
    data["run_id"] = run_id
    data["scenario_origin"] = origin
    data["project_id"] = project_id
    return data


@router.post("/runs/{run_id}/council")
def council(run_id: str, body: Optional[CouncilRequest] = Body(None)):
    try:
        return _compute_council(run_id, body)
    except ResolutionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except HTTPException:
        raise
    except (UnknownPackError, KitValidationError) as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("council compute failed")
        if mock_enabled() and body is None:
            logger.warning("mock mode is returning the council fixture after a compute failure")
            return load_fixture("council") | {"run_id": run_id, "scenario_origin": "fixture_fallback"}
        raise HTTPException(status_code=500, detail=f"council failed: {exc}") from exc


@router.post("/runs/{run_id}/kit")
def kit(run_id: str, body: Optional[KitRequest] = Body(None)):
    try:
        return _compute_kit(run_id, body)
    except ResolutionError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except HTTPException:
        raise
    except (UnknownPackError, KitValidationError) as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("kit compute failed")
        if mock_enabled() and body is None:
            logger.warning("mock mode is returning the kit fixture after a compute failure")
            return load_fixture("kit") | {"run_id": run_id, "scenario_origin": "fixture_fallback"}
        raise HTTPException(status_code=500, detail=f"kit failed: {exc}") from exc
