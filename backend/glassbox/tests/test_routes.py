import pytest
from fastapi.testclient import TestClient

from backend.common.contracts import AgentExplain
from backend.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "mock")


@pytest.mark.parametrize("mock", ["1", "0"])
def test_explain_route_is_real_in_both_modes(monkeypatch, mock):
    monkeypatch.setenv("MOCK", mock)
    r = client.get("/runs/run_42/agents/a055")
    assert r.status_code == 200
    e = AgentExplain.model_validate(r.json())
    assert e.agent_id == "a055" and e.narration_source == "template"
    assert e.top_drivers and e.flip is not None
    assert e.narration.startswith("Chose ChainApp over StudyFlow")  # computed, not the old canned fixture text


def test_unknown_agent_falls_back_in_mock_mode_but_is_404_otherwise(monkeypatch):
    monkeypatch.setenv("MOCK", "1")
    assert client.get("/runs/run_42/agents/nobody").json()["agent_id"] == "nobody"
    monkeypatch.setenv("MOCK", "0")
    assert client.get("/runs/run_42/agents/nobody").status_code == 404


def test_price_cut_run_uses_the_cut_price(monkeypatch):
    monkeypatch.setenv("MOCK", "0")
    base = client.get("/runs/run_42/agents/a055").json()["flip"]
    cut = client.get("/runs/run_42_price3/agents/a055").json()["flip"]
    assert base != cut  # same customer, different price, different flip


def test_flip_summary_route(monkeypatch):
    monkeypatch.setenv("MOCK", "0")
    r = client.get("/runs/run_42/flip-summary")
    assert r.status_code == 200
    body = r.json()
    assert body["run_id"] == "run_42" and body["rows"]
    assert all("text" in row and 0 <= row["pct"] <= 1 for row in body["rows"])
