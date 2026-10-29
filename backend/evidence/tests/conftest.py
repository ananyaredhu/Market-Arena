from types import SimpleNamespace

import pytest


@pytest.fixture(autouse=True)
def no_dataset_network(monkeypatch):
    """Tests never reach the World Bank, SingStat, Eurostat or BLS through the researcher.

    A test wanting a dataset passes its own.
    """
    from backend.evidence import agent, worldbank

    monkeypatch.setattr(worldbank, "country_economics", lambda *a, **k: None)
    none = SimpleNamespace(dataset_facts=lambda *a, **k: [], cpi_index=lambda *a, **k: None)
    for name in ("singstat", "eurostat", "bls"):
        monkeypatch.setattr(agent, name, none)
