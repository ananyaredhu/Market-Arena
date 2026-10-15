"""Person B routes: Council verdict and Experiment Kit.

Both routes resolve one run, then read that run's engine result. A failed
lookup or a failed engine call is an error. Fixture JSON is not substituted.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

from backend.common.contracts import CouncilOutput, RunResult
from backend.common.mock import mock_enabled
from backend.council.run_inputs import ResolutionError, resolve_run
from backend.council.service import CouncilComputeError, run_council, run_kit
from backend.kit.generator import KitValidationError
from backend.kit.packs import UnknownPackError

logger = logging.getLogger(__name__)
router = APIRouter(tags=["council and kit (B)"])

# Live delivery is Person C's route and is still a stub outside mock mode.
_UNSUPPORTED = [
    "Telegram delivery, approval and measured click rates are not live. Variant text comes from this kit.",
    "Trend notes are cited context only. They do not change engine shares.",
]


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


def _options_match(left: list, right: list) -> bool:
    def rows(options: list) -> list:
        out = []
        for option in options:
            price = option.get("price")
            features = option.get("features") or []
            out.append((
                option.get("id"),
                option.get("role"),
                None if price is None else round(float(price), 6),
                tuple(round(float(value), 6) for value in features),
            ))
        return out

    return rows(left) == rows(right)


def _annotate(data: dict, resolved, result: Optional[dict] = None) -> dict:
    data["scenario_origin"] = resolved.origin
    data["project_id"] = resolved.project_id
    data["pack"] = resolved.pack
    if resolved.scenario_note:
        data["scenario_note"] = resolved.scenario_note
    if result is not None:
        data["baseline_share"] = result["measured"]["baseline_share"]
    unsupported = list(_UNSUPPORTED)
    if resolved.pack == "cafe":
        unsupported.append("Café priors and kit copy are illustrative assumptions, not fitted demand.")
    elif resolved.origin == "demo":
        unsupported.append("This is the shared SaaS demo, not a run saved on a project.")
    data["unsupported"] = unsupported
    return data


def _payload(result: dict, resolved) -> dict:
    data = result["council"].model_dump()
    data["measured"] = result["measured"]
    return _annotate(data, resolved, result)


def _resolve_body(run_id: str, body: Optional[KitRequest]):
    """A posted council describes an existing run. It is not a new scenario."""
    if body is None or body.council is None or body.population is not None or body.run_result is not None:
        return body
    if body.council.run_id != run_id:
        raise ResolutionError(409, f"kit council.run_id is {body.council.run_id}, not {run_id}")
    return body.model_copy(update={"options": None})


def _same_council(posted: CouncilOutput, fresh: CouncilOutput) -> bool:
    if abs(posted.fragility - fresh.fragility) > 1e-4:
        return False
    posted_reaction = posted.competitor_reaction
    fresh_reaction = fresh.competitor_reaction
    posted_key = None if posted_reaction is None else (posted_reaction.competitor_id, posted_reaction.move)
    fresh_key = None if fresh_reaction is None else (fresh_reaction.competitor_id, fresh_reaction.move)
    return posted_key == fresh_key


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
    resolved = resolve_run(run_id, _resolve_body(run_id, body), live=not mock_enabled())
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
    if body is not None and body.council is not None and not _same_council(body.council, result["council"]):
        raise ResolutionError(409, "kit council does not match the council computed for this run")
    if body is not None and body.pack and body.pack != resolved.pack:
        raise ResolutionError(409, f"kit pack is '{body.pack}', but this run is '{resolved.pack}'")
    if body is not None and body.options is not None and not _options_match(body.options, resolved.options):
        raise ResolutionError(409, "kit options do not match the resolved run")
    kit = run_kit(result["council"], resolved.pack, resolved.options)
    data = kit.model_dump()
    data["run_id"] = run_id
    return _annotate(data, resolved, result)


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
    except CouncilComputeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("council compute failed")
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
    except CouncilComputeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("kit compute failed")
        raise HTTPException(status_code=500, detail=f"kit failed: {exc}") from exc
