import pytest
from fastapi.testclient import TestClient

from backend.common.contracts import AgentExplain
from backend.common.fixtures import load_fixture
from backend.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "mock")


def customers_who_chose(option_id: str) -> list[str]:
    """Pick test customers from the data instead of hard-coding one customer's (random) outcome."""
    return [c["agent_id"] for c in load_fixture("run_result")["choices"] if c["choice"] == option_id]


@pytest.mark.parametrize("mock", ["1", "0"])
def test_explain_route_is_real_in_both_modes(monkeypatch, mock):
    monkeypatch.setenv("MOCK", mock)
    aid = customers_who_chose("chain_app")[0]
    r = client.get(f"/runs/run_42/agents/{aid}")
    assert r.status_code == 200
    e = AgentExplain.model_validate(r.json())
    assert e.agent_id == aid and e.narration_source == "template"
    assert e.top_drivers and e.flip is not None
    assert e.narration.startswith("Chose ChainApp over")  # computed, not the old canned fixture text


def test_unknown_agent_falls_back_in_mock_mode_but_is_404_otherwise(monkeypatch):
    monkeypatch.setenv("MOCK", "1")
    assert client.get("/runs/run_42/agents/nobody").json()["agent_id"] == "nobody"
    monkeypatch.setenv("MOCK", "0")
    assert client.get("/runs/run_42/agents/nobody").status_code == 404


def test_price_cut_run_uses_the_cut_price(monkeypatch):
    monkeypatch.setenv("MOCK", "0")
    differing = 0
    for aid in customers_who_chose("free_tool")[:15]:  # customers who are not your buyers, so flips are computed
        base = client.get(f"/runs/run_42/agents/{aid}").json()["flip"]
        cut = client.get(f"/runs/run_42_price3/agents/{aid}").json()["flip"]
        differing += base != cut
    assert differing > 0  # at least some customers' flips change when your price changes


def test_flip_summary_route(monkeypatch):
    monkeypatch.setenv("MOCK", "0")
    r = client.get("/runs/run_42/flip-summary")
    assert r.status_code == 200
    body = r.json()
    assert body["run_id"] == "run_42" and body["rows"]
    assert all("text" in row and 0 <= row["pct"] <= 1 for row in body["rows"])
