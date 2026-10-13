"""Council and Kit routes (owner: Person B). Mounted by Person C's main.py.

Until Person C's run storage exists, the caller sends the inputs in the body.
With ``fixture=<pack>`` (or ``MOCK=1`` and no body) the local mock fixtures
in backend/council/fixtures are used instead.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Body, HTTPException, Query
from pydantic import BaseModel

from council.schemas import CouncilOutput, KitOutput, RunResult
from council.service import run_council, run_kit
from kit.generator import KitValidationError
from kit.packs import UnknownPackError

router = APIRouter(tags=["council"])
FIXTURES = Path(__file__).resolve().parent / "council" / "fixtures"


class CouncilRequest(BaseModel):
    run_result: RunResult
    population: dict
    options: List[dict]
    pack: str


class KitRequest(BaseModel):
    council: CouncilOutput
    options: List[dict]
    pack: str


def _fixture(name: str, pack: str):
    path = FIXTURES / f"{name}_{pack}.json"
    if not path.exists():
        raise HTTPException(404, f"no fixture {path.name}")
    return json.loads(path.read_text())


def _use_fixture(body, fixture: Optional[str]) -> Optional[str]:
    if fixture:
        return fixture
    if body is None and os.environ.get("MOCK") == "1":
        return "saas"
    if body is None:
        raise HTTPException(422, "request body required (or pass ?fixture=saas|cafe)")
    return None


@router.post("/runs/{run_id}/council", response_model=CouncilOutput)
def council(run_id: str, body: Optional[CouncilRequest] = Body(None), fixture: Optional[str] = Query(None)):
    pack = _use_fixture(body, fixture)
    if pack:
        body = CouncilRequest(
            run_result=_fixture("run_result", pack), population=_fixture("population", pack),
            options=_fixture("options", pack), pack=pack,
        )
    elif body.run_result.run_id != run_id:
        raise HTTPException(400, f"run_id in path ({run_id}) does not match body ({body.run_result.run_id})")
    try:
        return run_council(body.run_result, body.population, body.options, body.pack)["council"]
    except UnknownPackError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/runs/{run_id}/kit", response_model=KitOutput)
def kit(run_id: str, body: Optional[KitRequest] = Body(None), fixture: Optional[str] = Query(None)):
    pack = _use_fixture(body, fixture)
    if pack:
        body = KitRequest(council=_fixture("council", pack), options=_fixture("options", pack), pack=pack)
    elif body.council.run_id != run_id:
        raise HTTPException(400, f"run_id in path ({run_id}) does not match council ({body.council.run_id})")
    try:
        return run_kit(body.council, body.pack, body.options)
    except (UnknownPackError, KitValidationError) as exc:
        raise HTTPException(400, str(exc)) from exc
