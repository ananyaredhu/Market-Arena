"""Council route smoke tests (Person B). Requires FastAPI + httpx."""
from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi import FastAPI
from fastapi.testclient import TestClient

from council_routes import router


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_council_fixture_endpoint(client):
    response = client.post("/runs/run_saas_fixture/council?fixture=saas")
    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == "run_saas_fixture"
    assert body["confidence"] in ("low", "medium", "high")
    assert 0.0 <= body["fragility"] <= 1.0


def test_kit_fixture_endpoint(client):
    response = client.post("/runs/run_saas_fixture/kit?fixture=saas")
    assert response.status_code == 200
    body = response.json()
    assert 3 <= len(body["hypotheses"]) <= 5
    assert body["assets"]["landing_copy"]
