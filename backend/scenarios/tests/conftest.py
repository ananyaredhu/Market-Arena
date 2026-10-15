import pytest


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch, tmp_path):
    """Every test gets its own overrides file, so tests never touch (or depend on) real saved data."""
    monkeypatch.setenv("OVERRIDES_FILE", str(tmp_path / "overrides.json"))
    monkeypatch.setenv("LLM_MODE", "mock")
    monkeypatch.setenv("MOCK", "1")
