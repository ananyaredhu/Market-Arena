"""Person B routes: Council verdict and Experiment Kit.

Stubs return fixtures when MOCK=1. Replace with the real strategist, advocate, moderator and kit
generation (keep the path and the response shape).
"""
from fastapi import APIRouter

from backend.common.fixtures import load_fixture
from backend.common.mock import mock_enabled, not_built

router = APIRouter(tags=["council and kit (B)"])


@router.post("/runs/{run_id}/council")
def council(run_id: str):
    if mock_enabled():
        return load_fixture("council") | {"run_id": run_id}
    raise not_built("POST /runs/{id}/council")


@router.post("/runs/{run_id}/kit")
def kit(run_id: str):
    if mock_enabled():
        return load_fixture("kit")
    raise not_built("POST /runs/{id}/kit")
