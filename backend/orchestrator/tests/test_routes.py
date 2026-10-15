"""Real project-to-scenario-to-run persistence and Council/Kit integration."""
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

import pytest
from fastapi.testclient import TestClient

from backend.common.contracts import RunResult
from backend.main import app
from backend.orchestrator import storage

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_real_mode(monkeypatch, tmp_path):
    monkeypatch.setenv("MOCK", "0")
    monkeypatch.setenv("LLM_MODE", "mock")
    monkeypatch.setenv("COUNCIL_ENGINE", "engine")
    monkeypatch.setenv("MARKET_ARENA_DATA_DIR", str(tmp_path))


def create_project(pack="saas"):
    idea = (
        "StudyFlow is a study planner for university students. "
        "14-day free trial, then S$9 a month."
        if pack == "saas"
        else "Corner Brew is a neighbourhood cafe for local customers, S$5 per cup."
    )
    response = client.post("/projects", json={"idea": idea, "pack": pack, "geography": "SG"})
    assert response.status_code == 200, response.text
    return response.json()


def create_scenario(project_id, **overrides):
    payload = {"project_id": project_id, "seed": 7, "n_agents": 40, "repeats": 3}
    payload.update(overrides)
    return client.post("/scenarios", json=payload)


def test_create_scenario_persists_population_options_and_unique_id(tmp_path):
    project = create_project()

    first = create_scenario(project["id"])
    second = create_scenario(project["id"])

    assert first.status_code == second.status_code == 200
    one, two = first.json(), second.json()
    assert one["id"].startswith("scn_") and one["id"] != two["id"]
    saved = json.loads((tmp_path / "scenarios" / f"{one['id']}.json").read_text())
    assert saved["project_id"] == project["id"]
    assert saved["population"]["pack"] == "saas"
    assert len(saved["population"]["agents"]) == 40
    assert saved["assumptions"]["competitors"].startswith("industry pack archetypes")


def test_invalid_project_is_404_and_invalid_inputs_are_422():
    assert create_scenario("proj_missing").status_code == 404
    project = create_project()
    assert create_scenario(project["id"], n_agents=1).status_code == 422
    assert create_scenario(project["id"], repeats=0).status_code == 422
    assert create_scenario(project["id"], options=[]).status_code == 422
    assert create_scenario(project["id"], options=[{"id": "stranger", "label": "X", "role": "you"}]).status_code == 422


def test_project_without_price_requires_simulation_input():
    response = client.post("/projects", json={
        "idea": "StudyFlow is a study planner for university students with a free tier.",
        "pack": "saas",
        "geography": "SG",
    })
    assert response.status_code == 200
    scenario = create_scenario(response.json()["id"])
    assert scenario.status_code == 422
    assert "positive product price" in scenario.json()["detail"]


def test_real_run_is_persisted_as_contract_result_and_person_b_bundle(tmp_path):
    project = create_project()
    scenario = create_scenario(project["id"]).json()

    response = client.post(f"/scenarios/{scenario['id']}/run")

    assert response.status_code == 200
    started = response.json()
    result = client.get(f"/runs/{started['run_id']}")
    assert result.status_code == 200
    run = RunResult.model_validate(result.json()).model_dump(mode="json")
    assert run["run_id"] == started["run_id"]
    assert run["seed"] == 7
    assert run["totals"]["you"]["p90"] >= run["totals"]["you"]["p10"]
    assert run["choices"] and "components" in run["choices"][0]
    bundle = json.loads((tmp_path / "runs" / f"{started['run_id']}.json").read_text())
    assert {"run_id", "project_id", "pack", "population", "options", "run_result"} <= set(bundle)
    assert bundle["run_id"] == bundle["run_result"]["run_id"] == started["run_id"]
    assert bundle["project_id"] == project["id"]
    assert client.post(f"/runs/{started['run_id']}/council", json={"project_id": project["id"]}).status_code == 200
    assert client.post(f"/runs/{started['run_id']}/kit", json={"project_id": project["id"]}).status_code == 200


def test_runs_with_same_seed_are_unique_deterministic_and_project_isolated():
    project_a, project_b = create_project(), create_project()
    scenario_a = create_scenario(project_a["id"]).json()
    scenario_a_repeat = create_scenario(project_a["id"]).json()
    scenario_b = create_scenario(project_b["id"]).json()
    run_a = client.post(f"/scenarios/{scenario_a['id']}/run").json()
    run_a_repeat = client.post(f"/scenarios/{scenario_a_repeat['id']}/run").json()
    run_b = client.post(f"/scenarios/{scenario_b['id']}/run").json()

    assert len({run_a["run_id"], run_a_repeat["run_id"], run_b["run_id"]}) == 3
    result_a = client.get(f"/runs/{run_a['run_id']}").json()
    result_a_repeat = client.get(f"/runs/{run_a_repeat['run_id']}").json()
    result_b = client.get(f"/runs/{run_b['run_id']}").json()
    assert result_a["seed"] == result_b["seed"] == 7
    assert result_a["choices"] == result_a_repeat["choices"] == result_b["choices"]
    assert result_a["choices"] == result_b["choices"]
    wrong_project = client.post(f"/runs/{run_a['run_id']}/council", json={"project_id": project_b["id"]})
    assert wrong_project.status_code == 409


def test_unknown_and_malformed_runs_are_reported():
    assert client.get("/runs/run_missing").status_code == 404
    from backend.intake.projects import project_data_dir

    runs = project_data_dir() / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    (runs / "run_broken.json").write_text("not-json")
    response = client.get("/runs/run_broken")
    assert response.status_code == 422
    assert "not valid JSON" in response.json()["detail"]
    scenarios = project_data_dir() / "scenarios"
    scenarios.mkdir(parents=True, exist_ok=True)
    (scenarios / "scn_broken.json").write_text("not-json")
    scenario_response = client.post("/scenarios/scn_broken/run")
    assert scenario_response.status_code == 422
    assert "not valid JSON" in scenario_response.json()["detail"]


@pytest.mark.parametrize(
    "relative_path,endpoint",
    [
        ("runs/run_invalid_utf8.json", "/runs/run_invalid_utf8"),
        ("scenarios/scn_invalid_utf8.json", "/scenarios/scn_invalid_utf8/run"),
    ],
)
def test_invalid_utf8_is_a_controlled_422(tmp_path, relative_path, endpoint):
    path = tmp_path / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\xff\xfe\xfa")

    response = client.get(endpoint) if endpoint.startswith("/runs/") else client.post(endpoint)

    assert response.status_code == 422
    assert "not valid JSON" in response.json()["detail"]


def test_scenario_identifier_collision_retries_without_overwrite(monkeypatch, tmp_path):
    project = create_project()
    collision_path = tmp_path / "scenarios" / "scn_taken.json"
    collision_path.parent.mkdir(parents=True)
    original = {"id": "scn_taken", "sentinel": "preserve"}
    collision_path.write_text(json.dumps(original))
    ids = iter(["scn_taken", "scn_available"])
    monkeypatch.setattr(storage, "new_scenario_id", lambda: next(ids))

    response = create_scenario(project["id"])

    assert response.status_code == 200
    assert response.json()["id"] == "scn_available"
    assert json.loads(collision_path.read_text()) == original


def test_run_identifier_collision_retries_and_keeps_one_canonical_id(monkeypatch, tmp_path):
    project = create_project()
    scenario = create_scenario(project["id"]).json()
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    collision_path = runs_dir / "run_taken.json"
    collision_path.write_text('{"sentinel":"preserve"}')
    ids = iter(["run_taken", "run_available"])
    monkeypatch.setattr(storage, "new_run_id", lambda: next(ids))

    response = client.post(f"/scenarios/{scenario['id']}/run")

    assert response.status_code == 200
    run_id = response.json()["run_id"]
    assert run_id == "run_available"
    assert json.loads(collision_path.read_text()) == {"sentinel": "preserve"}
    bundle = json.loads((runs_dir / f"{run_id}.json").read_text())
    assert bundle["run_id"] == bundle["run_result"]["run_id"] == run_id


def test_concurrent_saves_use_unique_temp_files_and_only_install_complete_json(monkeypatch, tmp_path):
    monkeypatch.setenv("MARKET_ARENA_DATA_DIR", str(tmp_path))
    original_mkstemp = storage.tempfile.mkstemp
    created_temps = []
    record_lock = Lock()

    def tracked_mkstemp(*args, **kwargs):
        result = original_mkstemp(*args, **kwargs)
        with record_lock:
            created_temps.append(result[1])
        return result

    monkeypatch.setattr(storage.tempfile, "mkstemp", tracked_mkstemp)
    same_record = {"id": "scn_race", "payload": [1, 2, 3]}

    def save_same_id(_):
        try:
            storage.save_scenario(same_record)
            return "saved"
        except storage.RecordCollisionError:
            return "collision"

    with ThreadPoolExecutor(max_workers=12) as pool:
        outcomes = list(pool.map(save_same_id, range(12)))

    assert outcomes.count("saved") == 1
    assert outcomes.count("collision") == 11
    assert len(created_temps) == len(set(created_temps)) == 12
    assert json.loads((tmp_path / "scenarios" / "scn_race.json").read_text()) == same_record
    assert not list((tmp_path / "scenarios").glob("*.tmp"))


def test_missing_scenario_is_404():
    assert client.post("/scenarios/scn_missing/run").status_code == 404


def test_mock_scenario_and_run_responses_remain_fixture_compatible(monkeypatch):
    monkeypatch.setenv("MOCK", "1")
    assert client.post("/scenarios").json()["id"] == "scn_1"
    assert client.post("/scenarios/scn_1/run").json() == {"run_id": "run_42", "status": "done"}
    RunResult.model_validate(client.get("/runs/run_42").json())
    assert "event: progress" in client.get("/runs/run_42/stream").text


def test_real_stream_is_explicitly_deferred():
    response = client.get("/runs/run_missing/stream")
    assert response.status_code == 501
    assert "synchronous runs" in response.json()["detail"]
