"""Person A's features on a run that C's routes created and stored (project, scenario, run, then A's screens)."""
import json

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.scenarios.context import DEFAULT_REPEATS, RunContextError, get_context

client = TestClient(app)

IDEAS = {
    "saas": "StudyFlow is a study planner for university students. 14-day free trial, then S$9 a month.",
    "cafe": "Corner Brew is a neighbourhood cafe for local customers, S$5 per cup.",
}


@pytest.fixture(autouse=True)
def real_mode(monkeypatch, tmp_path):
    monkeypatch.setenv("MOCK", "0")
    monkeypatch.setenv("MARKET_ARENA_DATA_DIR", str(tmp_path))


def make_run(pack="saas", n_agents=60, repeats=4, seed=7):
    project = client.post("/projects", json={"idea": IDEAS[pack], "pack": pack, "geography": "SG"}).json()
    scenario = client.post("/scenarios", json={"project_id": project["id"], "seed": seed, "n_agents": n_agents,
                                               "repeats": repeats}).json()
    run = client.post(f"/scenarios/{scenario['id']}/run").json()
    return project["id"], run["run_id"]


@pytest.mark.parametrize("pack", ["saas", "cafe"])
def test_the_context_is_the_runs_own_market(pack):
    project_id, run_id = make_run(pack)
    ctx = get_context("proj_1", run_id)  # the project id asked for is ignored: the run knows its project
    assert (ctx.project_id, ctx.run_id, ctx.seed, ctx.repeats) == (project_id, run_id, 7, 4)
    assert len(ctx.agents) == 60 and ctx.population["pack"] == pack
    assert ctx.period == ("month" if pack == "saas" else "visit")


def test_without_overrides_the_adjusted_run_is_exactly_the_stored_run():
    _, run_id = make_run()
    stored = client.get(f"/runs/{run_id}").json()
    adjusted = client.get(f"/runs/{run_id}/adjusted").json()
    assert adjusted["run_id"] == run_id
    assert adjusted["choices"] == stored["choices"] and adjusted["overrides_applied"] == 0


def test_unknown_run_ids_and_no_run_id_still_use_the_fixtures():
    assert get_context("proj_1", "run_42").run_id is None
    assert get_context("proj_1").run_id is None
    assert get_context("proj_1", "run_does_not_exist").run_id is None


def test_a_broken_stored_run_is_refused_not_replaced_by_a_fixture(tmp_path):
    _, run_id = make_run()
    path = tmp_path / "runs" / f"{run_id}.json"
    bundle = json.loads(path.read_text())
    bundle["pack"] = "no_such_pack"
    path.write_text(json.dumps(bundle))
    with pytest.raises(RunContextError):
        get_context("proj_1", run_id)
    assert client.get(f"/runs/{run_id}/adjusted").status_code == 422


def test_repeats_fall_back_when_the_scenario_file_is_gone(tmp_path):
    _, run_id = make_run()
    for f in (tmp_path / "scenarios").glob("*.json"):
        f.unlink()
    assert get_context("proj_1", run_id).repeats == DEFAULT_REPEATS


def test_glassbox_explains_a_customer_of_the_real_run():
    _, run_id = make_run()
    agent = client.get(f"/runs/{run_id}/adjusted").json()["choices"][0]["agent_id"]
    r = client.get(f"/runs/{run_id}/agents/{agent}")
    assert r.status_code == 200 and r.json()["agent_id"] == agent
    assert client.get(f"/runs/{run_id}/agents/not_a_customer").status_code == 404
    flips = client.get(f"/runs/{run_id}/flip-summary").json()
    assert flips["run_id"] == run_id and isinstance(flips["rows"], list)


def test_overrides_work_on_the_real_run_and_belong_to_its_project():
    project_id, run_id = make_run()
    choices = client.get(f"/runs/{run_id}/adjusted").json()["choices"]
    target = next(c for c in choices if c["choice"] != "outside")
    r = client.post("/overrides", json={"run_id": run_id, "type": "lock", "agent_id": target["agent_id"],
                                        "option_id": "outside"})
    assert r.status_code == 200, r.text
    assert r.json()["override"]["project_id"] == project_id
    moved = next(c for c in r.json()["run"]["choices"] if c["agent_id"] == target["agent_id"])
    assert moved["choice"] == "outside" and moved["prev_choice"] == target["choice"]

    after = client.get(f"/runs/{run_id}/adjusted").json()
    assert after["overrides_applied"] == 1
    trail = client.get("/overrides", params={"run_id": run_id}).json()
    assert trail["project_id"] == project_id and trail["machine_generated"]["agents"] == 60
    assert len(trail["human_adjustments"]) == 1

    undone = client.delete(f"/overrides/{r.json()['override']['id']}", params={"run_id": run_id})
    assert undone.status_code == 200
    assert client.get(f"/runs/{run_id}/adjusted").json()["overrides_applied"] == 0


def test_a_second_run_of_the_same_project_inherits_its_overrides():
    project_id, run_id = make_run()
    agent = client.get(f"/runs/{run_id}/adjusted").json()["choices"][0]["agent_id"]
    assert client.post("/overrides", json={"run_id": run_id, "type": "exclude", "agent_id": agent}).status_code == 200
    scenario = client.post("/scenarios", json={"project_id": project_id, "seed": 7, "n_agents": 60,
                                               "repeats": 4}).json()
    second = client.post(f"/scenarios/{scenario['id']}/run").json()["run_id"]
    assert client.get(f"/runs/{second}/adjusted").json()["overrides_applied"] == 1


def test_compare_runs_from_the_real_market_with_its_currency_and_period():
    _, run_id = make_run("cafe")
    r = client.post("/scenarios/compare", json={"run_id": run_id, "changes": {"you": {"price": 3.0}}})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["period"] == "visit" and body["project_id"] != "proj_1"


def test_a_scenario_can_use_a_saved_evidence_snapshot(monkeypatch, tmp_path):
    from backend.evidence import store
    from backend.evidence.models import Economics, EvidenceSnapshot

    monkeypatch.setattr(store, "RUN_DIR", tmp_path / "evidence")
    econ = Economics(country="India", iso="IN", gdp_pc_ppp=10000, year=2025, baseline_iso="SG",
                     baseline_gdp_pc_ppp=160000, budget_scale=0.5, source_url="https://api.worldbank.org/x")
    store.save(EvidenceSnapshot(snapshot_id="ev_real_runs", created_at="2026-10-21T00:00:00+00:00", pack="saas",
                                geography="SG", status="ok", economics=econ))
    project = client.post("/projects", json={"idea": IDEAS["saas"], "pack": "saas", "geography": "SG"}).json()
    r = client.post("/scenarios", json={"project_id": project["id"], "n_agents": 40, "repeats": 2,
                                        "evidence_snapshot_id": "ev_real_runs"})
    assert r.status_code == 200, r.text
    evidence = r.json()["assumptions"]["population"]["evidence"]
    assert evidence["status"] == "ok" and evidence["used"] and evidence["applied"]


def test_a_scenario_moves_budgets_with_prices_from_the_chosen_starting_year(monkeypatch, tmp_path):
    from backend.evidence import store
    from backend.evidence.models import EvidenceSnapshot, PriceIndex

    monkeypatch.setattr(store, "RUN_DIR", tmp_path / "evidence")
    index = PriceIndex(name="CPI", table_id="M213801", url="https://tablebuilder.singstat.gov.sg/x",
                       retrieved_at="2026-10-21T00:00:00+00:00", values={"2022": 90.0, "2024": 100.0, "2025": 110.0})
    store.save(EvidenceSnapshot(snapshot_id="ev_cpi_run", created_at="2026-10-21T00:00:00+00:00", pack="saas",
                                geography="SG", status="off", price_index=index))
    project = client.post("/projects", json={"idea": IDEAS["saas"], "pack": "saas", "geography": "SG"}).json()

    def applied(year):
        r = client.post("/scenarios", json={"project_id": project["id"], "n_agents": 40, "repeats": 2,
                                            "evidence_snapshot_id": "ev_cpi_run", "price_base_year": year})
        assert r.status_code == 200, r.text
        return r.json()["assumptions"]["population"]["evidence"]

    assert "+10.0% from 2024 to 2025" in applied(2024)["applied"][0]
    assert "+22.2% from 2022 to 2025" in applied(2022)["applied"][0]
    assert "no 2023 value" in applied(2023)["skipped"][0]


@pytest.mark.parametrize("pack", ["saas", "cafe"])
def test_price_suggestion_runs_on_the_real_market_with_its_currency_and_period(pack):
    _, run_id = make_run(pack, n_agents=300)
    r = client.post("/pricing/suggest", json={"run_id": run_id, "cost": 1.0})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["period"] == ("month" if pack == "saas" else "visit") and body["customers"] == 300
    assert body["curve"][0]["price"] >= 1.0 and len(body["curve"]) >= 14
