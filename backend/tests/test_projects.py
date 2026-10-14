"""Focused coverage for the real-mode project intake vertical slice."""
from fastapi.testclient import TestClient

from backend.common.contracts import ProductProfile
from backend.main import app

client = TestClient(app)


def _real_mode(monkeypatch, tmp_path):
    monkeypatch.setenv("MOCK", "0")
    monkeypatch.setenv("MARKET_ARENA_DATA_DIR", str(tmp_path / "projects"))


def test_create_project_builds_a_valid_profile_and_unique_id(monkeypatch, tmp_path):
    _real_mode(monkeypatch, tmp_path)
    body = {
        "idea": "StudyFlow is a study planner for university students. 14-day free trial, then S$9 a month.",
        "pack": "saas",
        "geography": "sg",
    }

    response = client.post("/projects", json=body)
    duplicate = client.post("/projects", json=body)

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"].startswith("proj_")
    assert payload["id"] != duplicate.json()["id"]
    profile = ProductProfile.model_validate(payload["profile"])
    assert profile.pack == "saas"
    assert profile.price == 9.0
    assert profile.currency == "SGD"
    assert profile.geography == "SG"


def test_blank_idea_is_rejected(monkeypatch, tmp_path):
    _real_mode(monkeypatch, tmp_path)

    response = client.post("/projects", json={"idea": "   ", "pack": "saas"})

    assert response.status_code == 422
    assert "idea must not be blank" in response.text


def test_unsupported_pack_is_rejected(monkeypatch, tmp_path):
    _real_mode(monkeypatch, tmp_path)

    response = client.post("/projects", json={"idea": "A marketplace for plants", "pack": "marketplace"})

    assert response.status_code == 422
    assert "unsupported pack 'marketplace'" in response.text


def test_project_is_persisted_and_retrieved(monkeypatch, tmp_path):
    _real_mode(monkeypatch, tmp_path)
    created = client.post(
        "/projects",
        json={"idea": "A neighbourhood cafe with fast coffee", "pack": "cafe"},
    ).json()

    saved_files = list((tmp_path / "projects").glob("proj_*.json"))
    retrieved = client.get(f"/projects/{created['id']}")

    assert len(saved_files) == 1
    assert retrieved.status_code == 200
    assert retrieved.json() == created
    assert retrieved.json()["profile"]["price"] == 0.0
    assert "What price will customers pay?" in retrieved.json()["profile"]["missing_assumptions"]


def test_unknown_project_id_returns_404(monkeypatch, tmp_path):
    _real_mode(monkeypatch, tmp_path)

    response = client.get("/projects/proj_missing")

    assert response.status_code == 404
    assert "was not found" in response.text


def test_mock_mode_keeps_fixture_project_response(monkeypatch, tmp_path):
    monkeypatch.setenv("MOCK", "1")
    monkeypatch.setenv("MARKET_ARENA_DATA_DIR", str(tmp_path / "projects"))

    response = client.post("/projects")
    retrieved = client.get("/projects/anything")

    assert response.status_code == 200
    assert response.json()["id"] == "proj_1"
    assert response.json()["profile"]["name"] == "StudyFlow"
    assert retrieved.status_code == 200
    assert retrieved.json()["id"] == "anything"
