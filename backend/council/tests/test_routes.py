"""Council route smoke tests (Person B) against the mounted FastAPI app."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.common.contracts import CouncilOutput, KitOutput
from backend.main import app


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("MOCK", "1")
    monkeypatch.setenv("COUNCIL_ENGINE", "mock")
    return TestClient(app)


def test_council_endpoint_computes_or_falls_back(client):
    response = client.post("/runs/run_42/council")
    assert response.status_code == 200
    body = CouncilOutput.model_validate(response.json())
    assert body.run_id == "run_42"
    assert body.confidence in ("low", "medium", "high")
    assert 0.0 <= body.fragility <= 1.0
    assert body.verdict


def test_kit_endpoint_computes_or_falls_back(client):
    response = client.post("/runs/run_42/kit")
    assert response.status_code == 200
    body = KitOutput.model_validate(response.json())
    assert body.hypotheses
    assert body.assets.landing_copy
