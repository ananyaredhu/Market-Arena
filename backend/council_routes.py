"""Person B routes: Council verdict and Experiment Kit.

Paths and response shapes are frozen. Bodies compute via Person B modules when
shared fixtures (or supplied inputs) are available. With MOCK=1, any compute
failure falls back to fixtures/council.json and fixtures/kit.json so the
frontend keeps working.
"""
from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

from backend.common.contracts import CouncilOutput, KitOutput, RunResult
from backend.common.fixtures import load_fixture
from backend.common.mock import mock_enabled, not_built
from backend.council.service import run_council, run_kit
from backend.kit.generator import KitValidationError
from backend.kit.packs import UnknownPackError

logger = logging.getLogger(__name__)
router = APIRouter(tags=["council and kit (B)"])


class CouncilRequest(BaseModel):
    run_result: RunResult
    population: dict
    options: List[dict]
    pack: str = "saas"


class KitRequest(BaseModel):
    council: CouncilOutput
    options: List[dict]
    pack: str = "saas"


def _shared_inputs(pack: str = "saas") -> tuple[dict, list, dict]:
    """Load population / options / run_result from the shared /fixtures tree."""
    if pack == "saas":
        population = load_fixture("population_saas")
        options = load_fixture("options_saas")
        run_result = load_fixture("run_result")
    else:
        # Café shared fixtures are not in /fixtures yet; use Person B local ones.
        import json
        from pathlib import Path

        root = Path(__file__).resolve().parent / "council" / "fixtures"
        population = json.loads((root / f"population_{pack}.json").read_text())
        options = json.loads((root / f"options_{pack}.json").read_text())
        run_result = json.loads((root / f"run_result_{pack}.json").read_text())
    return population, options, run_result


def _compute_council(run_id: str, body: Optional[CouncilRequest] = None) -> CouncilOutput:
    if body is None:
        population, options, run_result = _shared_inputs("saas")
        pack = "saas"
    else:
        population, options, run_result, pack = (
            body.population,
            body.options,
            body.run_result.model_dump(),
            body.pack,
        )
    result = run_council(run_result, population, options, pack)
    council = result["council"]
    data = council.model_dump() if hasattr(council, "model_dump") else dict(council)
    data["run_id"] = run_id
    return CouncilOutput.model_validate(data)


def _compute_kit(run_id: str, body: Optional[KitRequest] = None) -> KitOutput:
    if body is None:
        council = _compute_council(run_id)
        _, options, _ = _shared_inputs("saas")
        pack = "saas"
    else:
        council, options, pack = body.council, body.options, body.pack
    return run_kit(council, pack, options)


@router.post("/runs/{run_id}/council")
def council(run_id: str, body: Optional[CouncilRequest] = Body(None)):
    try:
        return _compute_council(run_id, body)
    except Exception as exc:  # noqa: BLE001 — fall back in mock; surface otherwise
        logger.exception("council compute failed")
        if mock_enabled():
            return load_fixture("council") | {"run_id": run_id}
        if isinstance(exc, (UnknownPackError, KitValidationError)):
            raise HTTPException(400, str(exc)) from exc
        raise not_built("POST /runs/{id}/council")


@router.post("/runs/{run_id}/kit")
def kit(run_id: str, body: Optional[KitRequest] = Body(None)):
    try:
        return _compute_kit(run_id, body)
    except Exception as exc:  # noqa: BLE001
        logger.exception("kit compute failed")
        if mock_enabled():
            return load_fixture("kit")
        if isinstance(exc, (UnknownPackError, KitValidationError)):
            raise HTTPException(400, str(exc)) from exc
        raise not_built("POST /runs/{id}/kit")
