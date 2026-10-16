"""Council history reads stored runs and saved verdicts. It does not rerun the engine."""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from backend.council.history import save_council_record
from backend.intake.projects import ProjectCreateRequest, create_persisted_project
from backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKET_ARENA_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("MOCK", "0")
    monkeypatch.setenv("COUNCIL_ENGINE", "engine")
    return tmp_path


def _project(idea: str, pack: str) -> str:
    created = create_persisted_project(ProjectCreateRequest(idea=idea, pack=pack, geography="SG"))
    return created["id"]


def _bundle(run_id: str, project_id: str, *, share: float | None = 0.2, pack: str = "saas",
            price: float = 9, seed: int = 1, scenario_id: str | None = "scn_a",
            created_at: str | None = None, scenario_origin: str | None = None, run_result: dict | None = None) -> dict:
    if run_result is None:
        you = {"count": 1, "p10": 0.1, "p50": 0.2, "p90": 0.3}
        if share is not None:
            you["share"] = share
        run_result = {
            "run_id": run_id,
            "seed": seed,
            "option_ids": ["you", "outside"],
            "totals": {"you": you, "outside": {"count": 1, "share": 0.8, "p10": 0.7, "p50": 0.8, "p90": 0.9}},
            "choices": [],
        }
    bundle = {
        "run_id": run_id,
        "project_id": project_id,
        "pack": pack,
        "population": {"pack": pack, "agents": [{"id": "a1"}]},
        "options": [
            {"id": "you", "role": "you", "label": "StudyFlow", "price": price, "features": [0.5, 0.5]},
            {"id": "outside", "role": "outside", "label": "Do nothing", "price": 0, "features": []},
        ],
        "run_result": run_result,
        "scenario_id": scenario_id,
    }
    if created_at:
        bundle["created_at"] = created_at
    if scenario_origin:
        bundle["scenario_origin"] = scenario_origin
    return bundle


def _write(folder, bundle: dict) -> None:
    path = folder / "runs"
    path.mkdir(parents=True, exist_ok=True)
    (path / f"{bundle['run_id']}.json").write_text(json.dumps(bundle), encoding="utf-8")


def _council(
    run_id: str, project_id: str, verdict: str, confidence: str = "medium", move: str = "price_cut_10",
) -> None:
    save_council_record({
        "run_id": run_id,
        "project_id": project_id,
        "pack": "saas",
        "scenario_origin": "stored",
        "verdict": verdict,
        "confidence": confidence,
        "competitor_reaction": {"competitor_id": "chain_app", "move": move, "effect_on_share": -0.04},
        "baseline_share": 0.2,
    })


def test_history_keeps_one_project_and_skips_another(client, isolated):
    owner = _project("StudyFlow is a planner for university students at S$9", "saas")
    other = _project("A cafe for office workers near the station", "cafe")
    _write(isolated, _bundle(
        "run_early", owner, share=0.2, created_at="2026-10-15T01:00:00+00:00", scenario_id="scn_1",
    ))
    _write(isolated, _bundle(
        "run_late", owner, share=0.35, price=6, created_at="2026-10-16T01:00:00+00:00", scenario_id="scn_2",
    ))
    _write(isolated, _bundle("run_other", other, share=0.9, pack="cafe"))
    _council("run_early", owner, "Simulated outcome: hold the price.", "low", "price_cut_20")
    _council("run_late", owner, "Simulated outcome: a lower price holds more share.", "high", "add_feature")

    response = client.get(f"/projects/{owner}/council-history")
    assert response.status_code == 200
    body = response.json()
    ids = [entry["run_id"] for entry in body["entries"]]
    assert ids == ["run_early", "run_late"]
    assert "run_other" not in ids
    early = body["entries"][0]
    assert early["scenario_id"] == "scn_1"
    assert early["run_label"] == "live"
    assert early["share"] == 0.2
    assert early["verdict"].startswith("Simulated outcome")
    assert early["confidence"] == "low"
    assert early["competitor_move"]["move"] == "price_cut_20"
    assert "not real" in body["note"].lower() or "not observed" in body["note"].lower()


def test_snapshot_from_another_project_is_not_reused(client, isolated):
    owner = _project("StudyFlow is a planner for university students at S$9", "saas")
    other = _project("A cafe for office workers near the station", "cafe")
    _write(isolated, _bundle("run_shared", owner, share=0.22))
    _council("run_shared", other, "Simulated outcome: this verdict belongs to the cafe project.")
    entry = client.get(f"/projects/{owner}/council-history").json()["entries"][0]
    assert entry["share"] == 0.22
    assert entry["verdict"] is None
    assert entry["council_available"] is False
    assert any("different project" in line for line in entry["limitations"])


def test_missing_council_is_blank_not_invented(client, isolated):
    owner = _project("StudyFlow is a planner for university students at S$9", "saas")
    _write(isolated, _bundle("run_plain", owner, share=0.15))
    body = client.get(f"/projects/{owner}/council-history").json()
    entry = body["entries"][0]
    assert entry["council_available"] is False
    assert entry["verdict"] is None
    assert entry["confidence"] is None
    assert entry["competitor_move"] is None
    assert entry["share"] == 0.15
    assert any("not been saved" in line for line in entry["limitations"])


def test_malformed_bundle_is_reported_for_that_project(client, isolated):
    owner = _project("StudyFlow is a planner for university students at S$9", "saas")
    broken = {
        "run_id": "run_broken",
        "project_id": owner,
        "pack": "saas",
        "population": {},
        "options": [],
        "run_result": {"run_id": "run_someone_else", "seed": 1, "option_ids": [], "totals": {}, "choices": []},
    }
    _write(isolated, broken)
    (isolated / "runs" / "run_garbage.json").write_text("{", encoding="utf-8")
    response = client.get(f"/projects/{owner}/council-history")
    assert response.status_code == 200
    assert response.json()["entries"] == []
    assert response.json()["problems"][0]["run_id"] == "run_broken"
    assert "run_id" in response.json()["problems"][0]["detail"]


def test_unknown_project_is_404(client, isolated):
    response = client.get("/projects/proj_missing/council-history")
    assert response.status_code == 404
    assert "proj_missing" in response.json()["detail"]


def test_compare_uses_stored_numbers_and_states_limits(client, isolated):
    owner = _project("StudyFlow is a planner for university students at S$9", "saas")
    _write(isolated, _bundle("run_base", owner, share=0.2, price=9, seed=3, created_at="2026-10-15T01:00:00+00:00"))
    _write(isolated, _bundle("run_next", owner, share=0.35, price=6, seed=3, created_at="2026-10-16T01:00:00+00:00"))
    _council("run_base", owner, "Simulated outcome: the free tool still leads.", "medium", "price_cut_10")
    _council("run_next", owner, "Simulated outcome: your share is higher at the lower price.", "high", "add_feature")

    response = client.get(
        f"/projects/{owner}/council-history/compare",
        params={"base": "run_base", "other": "run_next"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["observed"]["share"]["comparable"] is True
    assert body["observed"]["share"]["value"] == pytest.approx(0.15)
    assert body["interpretation"]["verdict"]["changed"] is True
    assert body["interpretation"]["confidence"]["base"] == "medium"
    assert body["interpretation"]["confidence"]["other"] == "high"
    assert body["interpretation"]["confidence"]["steps"] == 1
    assert body["interpretation"]["competitor_move"]["changed"] is True
    assert any("price" in item["field"] for item in body["scenario_differences"])
    joined = " ".join(body["limitations"]).lower()
    assert "not proof" in joined or "not a change in real demand" in joined
    assert any("not observed" in line.lower() or "not a change in real demand" in line.lower() for line in (
        [body["observed"]["share"]["detail"]] + body["limitations"]
    ))


def test_missing_and_non_numeric_shares_are_not_compared(client, isolated):
    owner = _project("StudyFlow is a planner for university students at S$9", "saas")
    missing = _bundle("run_missing_share", owner, share=None)
    _write(isolated, missing)
    bad = _bundle("run_bad_share", owner)
    bad["run_result"]["totals"]["you"]["share"] = "high"
    _write(isolated, bad)
    listed = client.get(f"/projects/{owner}/council-history").json()["entries"]
    assert all(entry["share"] is None for entry in listed)
    compared = client.get(
        f"/projects/{owner}/council-history/compare",
        params={"base": "run_missing_share", "other": "run_bad_share"},
    )
    assert compared.status_code == 200
    assert compared.json()["observed"]["share"]["comparable"] is False
    assert compared.json()["observed"]["share"]["value"] is None
    assert compared.json()["interpretation"]["verdict"]["comparable"] is False


def test_other_project_run_cannot_be_compared(client, isolated):
    owner = _project("StudyFlow is a planner for university students at S$9", "saas")
    other = _project("A cafe for office workers near the station", "cafe")
    _write(isolated, _bundle("run_mine", owner))
    _write(isolated, _bundle("run_theirs", other, pack="cafe"))
    response = client.get(
        f"/projects/{owner}/council-history/compare",
        params={"base": "run_mine", "other": "run_theirs"},
    )
    assert response.status_code == 404
    assert "run_theirs" in response.json()["detail"]


def test_same_run_twice_is_rejected(client, isolated):
    owner = _project("StudyFlow is a planner for university students at S$9", "saas")
    _write(isolated, _bundle("run_only", owner))
    response = client.get(
        f"/projects/{owner}/council-history/compare",
        params={"base": "run_only", "other": "run_only"},
    )
    assert response.status_code == 422


def test_demo_bundle_is_labelled_and_history_does_not_call_the_engine(client, isolated, monkeypatch):
    owner = _project("StudyFlow is a planner for university students at S$9", "saas")
    _write(isolated, _bundle("run_demo_saved", owner, scenario_origin="demo", share=0.1))
    _write(isolated, _bundle("run_live_saved", owner, share=0.4, created_at="2026-10-16T02:00:00+00:00"))

    def explode(*_args, **_kwargs):
        raise AssertionError("history must not rerun the engine")

    monkeypatch.setattr("backend.engine.engine.run_scenario", explode)
    monkeypatch.setattr("backend.council.run_inputs.run_scenario", explode)
    first = client.get(f"/projects/{owner}/council-history")
    second = client.get(f"/projects/{owner}/council-history")
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    labels = {entry["run_id"]: entry["run_label"] for entry in first.json()["entries"]}
    assert labels["run_demo_saved"] == "demo"
    assert labels["run_live_saved"] == "live"


def test_opening_the_council_saves_a_snapshot_that_history_can_reread(client, isolated, monkeypatch):
    from backend.common.fixtures import load_fixture
    from backend.council.run_inputs import save_bundle

    owner = _project("StudyFlow is a planner for university students at S$9", "saas")
    population = load_fixture("population_saas")
    options = load_fixture("options_saas")
    result = load_fixture("run_result")
    save_bundle({
        "run_id": "run_42",
        "project_id": owner,
        "pack": "saas",
        "population": population,
        "options": options,
        "run_result": result,
        "scenario_id": "scn_saved",
        "trend_notes": [],
        "research_notes": [],
    })
    opened = client.post("/runs/run_42/council", json={"project_id": owner})
    assert opened.status_code == 200, opened.text
    verdict = opened.json()["verdict"]

    def explode(*_args, **_kwargs):
        raise AssertionError("rereading history must not rerun the engine")

    monkeypatch.setattr("backend.engine.engine.run_scenario", explode)
    monkeypatch.setattr("backend.council.run_inputs.run_scenario", explode)
    listed = client.get(f"/projects/{owner}/council-history")
    assert listed.status_code == 200
    entry = listed.json()["entries"][0]
    assert entry["run_id"] == "run_42"
    assert entry["scenario_id"] == "scn_saved"
    assert entry["verdict"] == verdict
    assert entry["council_available"] is True
    again = client.get(f"/projects/{owner}/council-history")
    assert again.json()["entries"][0]["verdict"] == verdict


def test_overlapping_snapshot_writes_keep_a_readable_record(isolated):
    owner = _project("StudyFlow is a planner for university students at S$9", "saas")

    def write(index: int) -> None:
        save_council_record({
            "run_id": "run_overlap",
            "project_id": owner,
            "pack": "saas",
            "scenario_origin": "stored",
            "verdict": f"saved {index}",
            "confidence": "low",
        })

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(write, range(8)))

    saved = json.loads((isolated / "council" / "run_overlap.json").read_text())
    assert saved["run_id"] == "run_overlap"
    assert saved["project_id"] == owner
    assert saved["verdict"].startswith("saved ")
    assert list((isolated / "council").glob("*.tmp")) == []
