import pytest
from fastapi.testclient import TestClient

from backend.common.contracts import AgentExplain
from backend.main import app
from backend.scenarios.context import get_context
from backend.scenarios.overrides import run_with_overrides

client = TestClient(app)


def buyer_candidate() -> str:
    """A customer who can afford 'you' but does not pick it in the baseline."""
    ctx = get_context()
    base = run_with_overrides(ctx, [])[0]
    chose = {c["agent_id"]: c["choice"] for c in base["choices"]}
    return next(a["id"] for a in ctx.agents if a["budget"] >= 7 and chose[a["id"]] != "you")


# ---------------------------------------------------------------- overrides
def test_bare_post_in_mock_mode_still_answers_200():
    assert client.post("/overrides").status_code == 200


def test_bare_post_without_mock_is_422(monkeypatch):
    monkeypatch.setenv("MOCK", "0")
    assert client.post("/overrides").status_code == 422


def test_lock_flow_end_to_end():
    aid = buyer_candidate()
    payload = {"type": "lock", "agent_id": aid, "option_id": "you", "note": "friend of founder"}
    r = client.post("/overrides", json=payload)
    assert r.status_code == 200
    body = r.json()
    oid = body["override"]["id"]
    assert body["override"]["created_by"] == "human" and body["moved"] >= 1
    assert next(c for c in body["run"]["choices"] if c["agent_id"] == aid)["locked"] is True

    trail = client.get("/overrides").json()
    assert [o["id"] for o in trail["human_adjustments"]] == [oid] and "1 human adjustment" in trail["summary"]

    adjusted = client.get("/runs/run_42/adjusted").json()
    assert next(c for c in adjusted["choices"] if c["agent_id"] == aid)["choice"] == "you"

    e = AgentExplain.model_validate(client.get(f"/runs/run_42/agents/{aid}").json())
    assert "set manually" in e.narration  # the Glass-Box knows a person pinned this choice

    undone = client.delete(f"/overrides/{oid}").json()
    assert undone["removed"] == oid and client.get("/overrides").json()["human_adjustments"] == []


def test_refused_override_is_422_with_the_engines_reason_and_nothing_saved():
    poor = next(a["id"] for a in get_context().agents if a["budget"] < 4)
    r = client.post("/overrides", json={"type": "lock", "agent_id": poor, "option_id": "you"})
    assert r.status_code == 422 and "price is above their budget" in r.json()["detail"]
    assert client.get("/overrides").json()["human_adjustments"] == []


def test_malformed_override_is_422():
    assert client.post("/overrides", json={"type": "lock", "agent_id": "a000"}).status_code == 422


def test_delete_unknown_override_is_404():
    assert client.delete("/overrides/nope").status_code == 404


def test_exclude_shrinks_the_adjusted_run_and_hides_the_customer_from_the_glass_box(monkeypatch):
    victim = next(a["id"] for a in get_context().agents if a["segment"] == "loyal")
    client.post("/overrides", json={"type": "exclude", "agent_id": victim})
    run = client.get("/runs/run_42/adjusted").json()
    assert victim not in {c["agent_id"] for c in run["choices"]}
    monkeypatch.setenv("MOCK", "0")
    assert client.get(f"/runs/run_42/agents/{victim}").status_code == 404


def test_adjusted_price_cut_run_keeps_the_override_and_marks_switchers():
    aid = buyer_candidate()
    client.post("/overrides", json={"type": "lock", "agent_id": aid, "option_id": "you"})
    run = client.get("/runs/run_42_price3/adjusted").json()
    assert run["run_id"] == "run_42_price3" and run["overrides_applied"] == 1
    assert any(c["prev_choice"] != c["choice"] for c in run["choices"])


def test_projects_do_not_share_overrides():
    aid = buyer_candidate()
    client.post("/overrides", json={"project_id": "other", "type": "lock", "agent_id": aid, "option_id": "you"})
    assert client.get("/overrides").json()["human_adjustments"] == []
    assert len(client.get("/overrides", params={"project_id": "other"}).json()["human_adjustments"]) == 1


# ---------------------------------------------------------------- compare
def test_compare_with_no_body_is_the_default_price_cut():
    r = client.post("/scenarios/compare")
    assert r.status_code == 200
    body = r.json()
    assert body["scenarios"]["b"]["summary"] == ["StudyFlow price S$7.00 → S$3.00"]
    assert {"a", "b", "headline", "revenue", "deltas", "flip_summary_b"} <= set(body)


def test_compare_with_custom_changes():
    r = client.post("/scenarios/compare", json={"changes": {"you": {"price": 9.0}}, "label_b": "Premium"})
    body = r.json()
    assert r.status_code == 200 and body["scenarios"]["b"]["label"] == "Premium"
    assert body["headline"]["delta_p50"] <= 0  # a higher price cannot gain share


@pytest.mark.parametrize("payload", [
    {"changes": {"nope": {"price": 1}}},
    {"changes": {"you": {"price": -1}}},
    {"changes": {"you": {"features": [3, 0, 0, 0]}}},
    {"changes": {}},
])
def test_compare_bad_input_is_422(payload):
    assert client.post("/scenarios/compare", json=payload).status_code == 422
