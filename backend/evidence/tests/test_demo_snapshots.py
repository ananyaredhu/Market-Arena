"""The committed demo snapshots (fixtures/evidence/) must load offline and drive a population without any network."""
import pytest

from backend.evidence import store
from backend.evidence.apply import apply_evidence
from backend.population.generator import generate_population
from backend.population.models import PopulationRequest
from backend.population.packs import load_pack

DEMOS = ["ev_saas_SG_demo", "ev_cafe_SG_demo"]


@pytest.fixture(autouse=True)
def only_the_demo_folder(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "RUN_DIR", tmp_path / "empty")  # nothing from a local data/ folder can help


@pytest.mark.parametrize("snapshot_id", DEMOS)
def test_demo_snapshot_loads_and_has_real_evidence(snapshot_id):
    snap = store.load(snapshot_id)
    pack = snapshot_id.split("_")[1]
    assert snap.pack == pack and snap.geography == "SG" and snap.status in ("ok", "partial")
    assert snap.economics and snap.price_index and snap.datasets
    assert {"2024", "2025"} <= set(snap.price_index.values)
    assert snap.findings and all(f.quote and f.url.startswith("http") for f in snap.findings)


@pytest.mark.parametrize("snapshot_id", DEMOS)
def test_demo_snapshot_moves_budgets_with_prices_and_nothing_else(snapshot_id):
    pack = load_pack(snapshot_id.split("_")[1])
    r = apply_evidence(pack, store.load(snapshot_id), 2024)
    assert r.applied and "from 2024 to 2025" in r.applied[-1]
    for before, after in zip(pack.segments, r.segments, strict=True):
        assert after.priors.alpha == before.priors.alpha and after.priors.incumbent == before.priors.incumbent
        assert after.priors.budget[1] >= before.priors.budget[1]  # prices rose from 2024 to 2025


@pytest.mark.parametrize("snapshot_id", DEMOS)
def test_a_population_can_be_built_from_the_demo_snapshot_offline(snapshot_id):
    pack = snapshot_id.split("_")[1]
    pop = generate_population(PopulationRequest(pack=pack, n_agents=60, evidence_snapshot_id=snapshot_id))
    assert pop["evidence_snapshot_id"] == snapshot_id and pop["generation"]["evidence"]["used"]
