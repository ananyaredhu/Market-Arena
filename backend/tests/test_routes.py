"""Every frozen route answers in mock mode with contract-valid data."""
import pytest
from fastapi.testclient import TestClient

from backend.common.contracts import AgentExplain, CouncilOutput, KitOutput, Population, RunResult
from backend.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_on(monkeypatch):
    monkeypatch.setenv("MOCK", "1")


def test_health():
    assert client.get("/health").json() == {"status": "ok", "mock": True}


@pytest.mark.parametrize(
    "method,path,model",
    [
        ("post", "/population/generate", Population),
        ("get", "/runs/run_42/agents/a055", AgentExplain),
        ("post", "/runs/run_42/council", CouncilOutput),
        ("post", "/runs/run_42/kit", KitOutput),
        ("get", "/runs/run_42", RunResult),
    ],
)
def test_contract_routes(method, path, model):
    r = getattr(client, method)(path)
    assert r.status_code == 200
    model.model_validate(r.json())


@pytest.mark.parametrize(
    "method,path",
    [
        ("post", "/overrides"),
        ("post", "/scenarios/compare"),
        ("post", "/projects"),
        ("get", "/projects/proj_1"),
        ("post", "/scenarios"),
        ("post", "/scenarios/scn_1/run"),
        ("post", "/telegram/campaigns"),
        ("post", "/telegram/campaigns/cmp_1/send"),
        ("get", "/telegram/campaigns/cmp_1/results"),
        ("post", "/telegram/webhook/secret"),
    ],
)
def test_other_routes_answer(method, path):
    assert getattr(client, method)(path).status_code == 200


def test_stream_emits_progress_then_result():
    with client.stream("GET", "/runs/run_42/stream") as r:
        text = "".join(r.iter_text())
    assert "event: progress" in text and "event: result" in text


def test_unimplemented_route_is_501_when_mock_off(monkeypatch):
    monkeypatch.setenv("MOCK", "0")
    assert client.post("/runs/run_42/council").status_code == 501
