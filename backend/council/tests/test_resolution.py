"""Run binding, engine checks, and live versus mock behaviour for Council and Kit."""
from __future__ import annotations

import copy

import pytest
from fastapi.testclient import TestClient

from backend.common.contracts import CouncilOutput, KitOutput
from backend.common.fixtures import load_fixture
from backend.council.engine_adapter import FrozenSignatureAdapter, MockEngineAdapter
from backend.council.run_inputs import save_bundle
from backend.council.service import run_council
from backend.council.wording import wording_from_env
from backend.intake.projects import ProjectCreateRequest, create_persisted_project
from backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKET_ARENA_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("COUNCIL_ENGINE", "engine")
    return tmp_path


def test_missing_run_is_404_and_not_a_fixture(client, isolated, monkeypatch):
    monkeypatch.setenv("MOCK", "0")
    response = client.post("/runs/run_missing/council")
    assert response.status_code == 404
    assert response.json()["detail"]
    assert "run_missing" in response.json()["detail"]


def test_live_demo_is_computed_not_the_canned_council(client, isolated, monkeypatch):
    monkeypatch.setenv("MOCK", "0")
    response = client.post("/runs/run_42/council")
    assert response.status_code == 200
    body = response.json()
    CouncilOutput.model_validate(body)
    canned = load_fixture("council")
    assert body["scenario_origin"] == "demo"
    assert body["run_id"] == "run_42"
    assert body["verdict"] != canned["verdict"]
    assert body["measured"]["baseline_share"] == load_fixture("run_result")["totals"]["you"]["share"]
    assert body["engine_source"] == "engine"
    assert "fixture_fallback" not in body["scenario_origin"]


def test_run_id_mismatch_rejected(client, isolated, monkeypatch):
    monkeypatch.setenv("MOCK", "0")
    payload = {
        "population": load_fixture("population_saas"),
        "options": load_fixture("options_saas"),
        "run_result": load_fixture("run_result"),
    }
    response = client.post("/runs/run_other/council", json=payload)
    assert response.status_code == 409
    assert "run_42" in response.json()["detail"]


def test_altered_share_rejected(client, isolated, monkeypatch):
    monkeypatch.setenv("MOCK", "0")
    result = copy.deepcopy(load_fixture("run_result"))
    result["totals"]["you"]["share"] = 0.99
    response = client.post("/runs/run_42/council", json={
        "population": load_fixture("population_saas"),
        "options": load_fixture("options_saas"),
        "run_result": result,
    })
    assert response.status_code == 409
    assert "does not match" in response.json()["detail"]


def test_wrong_project_cannot_read_another_projects_run(client, isolated, monkeypatch):
    monkeypatch.setenv("MOCK", "0")
    monkeypatch.setenv("COUNCIL_ENGINE", "mock")
    population = load_fixture("population_saas")
    options = load_fixture("options_saas")
    result = load_fixture("run_result")
    save_bundle({
        "run_id": "run_42",
        "project_id": "proj_owner",
        "pack": "saas",
        "population": population,
        "options": options,
        "run_result": result,
        "trend_notes": [],
        "research_notes": [],
    })
    owner = client.post("/runs/run_42/council", json={"project_id": "proj_owner"})
    assert owner.status_code == 404  # live mode requires the project file

    data = isolated
    created = create_persisted_project(ProjectCreateRequest(
        idea="StudyFlow is a planner for university students at $9", pack="saas", geography="SG",
    ))
    other = create_persisted_project(ProjectCreateRequest(
        idea="A cafe for office workers near the station", pack="cafe", geography="SG",
    ))
    assert created["id"] != other["id"]
    # Re-bind the stored run to the real owner id.
    save_bundle({
        "run_id": "run_42",
        "project_id": created["id"],
        "pack": "saas",
        "population": population,
        "options": options,
        "run_result": result,
        "trend_notes": [],
        "research_notes": [],
    })
    ok = client.post("/runs/run_42/council", json={"project_id": created["id"]})
    assert ok.status_code == 200
    assert ok.json()["project_id"] == created["id"]
    assert ok.json()["scenario_origin"] == "stored"
    blocked = client.post("/runs/run_42/council", json={"project_id": other["id"]})
    assert blocked.status_code == 409
    assert created["id"] in blocked.json()["detail"]
    assert data.is_dir()


def test_mock_mode_does_not_serve_fixture_for_an_unknown_run(client, isolated, monkeypatch):
    monkeypatch.setenv("MOCK", "1")
    response = client.post("/runs/run_not_a_demo/council")
    assert response.status_code == 404


def test_kit_rejects_a_council_for_a_different_run(client, isolated, monkeypatch):
    monkeypatch.setenv("MOCK", "0")
    council = client.post("/runs/run_42/council").json()
    council["run_id"] = "run_42"
    response = client.post("/runs/run_42_price3/kit", json={
        "council": council, "pack": "saas", "options": load_fixture("options_saas"),
    })
    assert response.status_code == 409


def test_trend_notes_are_cited_and_do_not_change_shares(isolated):
    population = load_fixture("population_saas")
    options = load_fixture("options_saas")
    result = load_fixture("run_result")
    adapter = MockEngineAdapter()
    plain = run_council(result, population, options, "saas", adapter=adapter)
    cited = run_council(
        result, population, options, "saas", adapter=adapter,
        trend_notes=[{
            "note": "Rising cost of living is squeezing student budgets.",
            "source_url": "https://example.com/placeholder-source",
            "quote": "Students are cutting back on subscriptions.",
        }],
        research_notes=[{
            "topic": "channels",
            "note": "Students hear about tools from friends.",
            "source_url": "https://example.com/placeholder-channels",
            "quote": "Most students said they heard about the tool from a friend.",
        }],
    )
    assert plain["measured"]["baseline_share"] == cited["measured"]["baseline_share"]
    assert plain["measured"]["fragility"] == cited["measured"]["fragility"]
    assert cited["council"].trend_context
    urls = [item.source_url for item in cited["council"].trend_context]
    assert "https://example.com/placeholder-source" in urls
    assert "https://example.com/placeholder-channels" in urls
    assert plain["council"].trend_context in (None, [])


def test_llm_failure_keeps_the_template(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "live")
    monkeypatch.setenv("LLM_PROVIDER_ORDER", "groq")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    wording = wording_from_env()
    draft = "Simulated outcome under stated assumptions: share 0.25."
    assert wording.rewrite_verdict(draft, {"share": 0.25}) == draft


def test_adapter_prefers_canonical_share_over_p50():
    def fake(agents, options, seed, repeats=1, **kwargs):
        return {"run_id": "run_1", "totals": {"you": {"share": 0.2, "p50": 0.5, "p10": 0.1, "p90": 0.3, "count": 1}}}

    evaluation = FrozenSignatureAdapter(fake).evaluate([], [], seed=1)
    assert evaluation.share("you") == 0.2


def test_price3_demo_kit_mentions_the_lower_price(client, isolated, monkeypatch):
    monkeypatch.setenv("MOCK", "0")
    response = client.post("/runs/run_42_price3/kit")
    assert response.status_code == 200
    kit = KitOutput.model_validate(response.json())
    assert response.json()["run_id"] == "run_42_price3"
    assert response.json()["scenario_origin"] == "demo"
    text = " ".join(kit.hypotheses)
    assert "S$3" in text or "3" in text
