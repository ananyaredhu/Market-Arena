"""The founder's currency is kept; the pack's money assumptions are re-expressed in it, their price is not."""
import pytest
from fastapi.testclient import TestClient

from backend.common.money import currency_of, money_symbol
from backend.evidence import worldbank
from backend.intake.currency import bare_dollar, currency_of_country, reference_country
from backend.kit.generator import money
from backend.main import app
from backend.population.generator import generate_population, template_population
from backend.population.localise import localise_pack, localised, money_scale
from backend.population.models import PopulationRequest
from backend.population.packs import load_pack

PPP = {"SG": 0.79, "IN": 20.0, "US": 1.0, "DE": 0.71}


@pytest.fixture(autouse=True)
def offline_ppp(monkeypatch):
    """No test reaches the World Bank: the PPP factors above stand in for the dataset."""
    def fake(iso, client=None, cache_dir=None):
        v = PPP.get(iso.upper())
        return None if v is None else {"country": iso.upper(), "year": 2025, "value": v, "url": f"https://wb.test/{iso}"}
    monkeypatch.setattr(worldbank, "ppp_factor", fake)


def test_the_scale_is_the_ratio_of_purchasing_power_factors():
    loc = money_scale("SGD", "INR", "IN")
    assert loc.scaled and loc.code == "INR" and loc.scale == pytest.approx(20.0 / 0.79)
    assert "not an exchange rate" in loc.note and "Your own price is not converted" in loc.note


def test_the_pack_currency_or_none_means_no_scaling():
    for currency in (None, "SGD"):
        loc = money_scale("SGD", currency, "IN")
        assert not loc.scaled and loc.scale == 1.0 and loc.code == "SGD"


def test_a_missing_dataset_leaves_the_pack_as_written_and_says_so():
    loc = money_scale("SGD", "PLN", "PL")  # no factor for Poland in the stand-in data
    assert not loc.scaled and "no purchasing-power data" in loc.note and "PLN" in loc.note
    assert money_scale("SGD", "XYZ", None).scaled is False


def test_every_money_assumption_moves_together_and_the_pack_is_not_mutated():
    pack = load_pack("saas")
    before = pack.model_dump()
    local, loc = localised(pack, "INR", "IN")
    k = loc.scale
    assert pack.model_dump() == before and local.currency == "INR"
    for old, new in zip(pack.segments, local.segments, strict=True):
        assert new.priors.budget[1] == pytest.approx(old.priors.budget[1] * k, rel=1e-3)
        assert new.priors.alpha[0] == pytest.approx(old.priors.alpha[0] / k)
        assert new.priors.w == old.priors.w and new.priors.tau == old.priors.tau  # unit-free priors do not move
    assert [c["price"] for c in local.competitors] == [round(c["price"] * k, 2) for c in pack.competitors]
    assert local.demo_product["price"] == round(pack.demo_product["price"] * k, 2)


def test_price_times_sensitivity_is_unchanged_so_the_market_behaves_the_same():
    pack = load_pack("saas")
    local = localise_pack(pack, money_scale("SGD", "INR", "IN"))
    for old, new in zip(pack.segments, local.segments, strict=True):
        assert new.priors.alpha[1] * new.priors.budget[1] == pytest.approx(old.priors.alpha[1] * old.priors.budget[1],
                                                                          rel=1e-3)


def test_a_rupee_market_gives_the_same_shares_as_the_singapore_market_it_was_scaled_from():
    from backend.engine.engine import run_scenario

    def share(currency):
        req = PopulationRequest(pack="saas", n_agents=200, seed=3, geography="IN", currency=currency)
        pop = template_population(req)
        pack, _ = localised(load_pack("saas"), currency, "IN")
        you = {**pack.demo_product}
        options = [you, *pack.competitors, {"id": "outside", "label": "Do nothing", "role": "outside"}]
        return run_scenario(pop["agents"], options, 3, repeats=5)["totals"]["you"]["p50"]

    assert share("INR") == pytest.approx(share("SGD"), abs=0.01)


def test_generated_population_records_the_currency_and_validates():
    pop = generate_population(PopulationRequest(pack="saas", n_agents=100, seed=1, geography="IN", currency="INR"))
    assert currency_of(pop, "SGD") == "INR"
    gen = pop["generation"]["currency"]
    assert gen["scaled"] and gen["code"] == "INR" and pop["generation"]["validation"] == "passed"
    assert max(a["budget"] for a in pop["agents"]) > 100  # rupee budgets, not S$3-25
    plain = generate_population(PopulationRequest(pack="saas", n_agents=100, seed=1))
    assert currency_of(plain, "SGD") == "SGD" and not plain["generation"]["currency"]["scaled"]


def test_a_stored_run_is_read_back_in_the_founders_currency(monkeypatch, tmp_path):
    monkeypatch.setenv("MOCK", "0")
    monkeypatch.setenv("MARKET_ARENA_DATA_DIR", str(tmp_path / "projects"))
    c = TestClient(app)
    project = c.post("/projects", json={"idea": "A study planner app for Mumbai students at 500 rupees a month",
                                       "pack": "saas"}).json()
    assert project["profile"]["currency"] == "INR" and project["profile"]["price"] == 500.0
    scenario = c.post("/scenarios", json={"project_id": project["id"], "n_agents": 100, "repeats": 3}).json()
    rival_prices = [o["price"] for o in scenario["options"] if o["role"] == "competitor"]
    assert max(rival_prices) > 100  # rivals are in rupees too
    run = c.post(f"/scenarios/{scenario['id']}/run").json()
    compare = c.post("/scenarios/compare", json={"run_id": run["run_id"], "project_id": project["id"],
                                                 "changes": {"you": {"price": 400}}}).json()
    assert compare["currency_symbol"] == "₹" and compare["scenarios"]["a"]["you_price"] == 500.0  # never converted
    found = c.post("/pricing/suggest", json={"run_id": run["run_id"], "project_id": project["id"]}).json()
    assert found["currency_symbol"] == "₹" and found["current_price"] == 500.0


def test_a_project_without_a_price_is_suggested_a_price_in_its_own_currency(monkeypatch, tmp_path):
    monkeypatch.setenv("MOCK", "0")
    monkeypatch.setenv("MARKET_ARENA_DATA_DIR", str(tmp_path / "projects"))
    c = TestClient(app)
    project = c.post("/projects", json={"idea": "A study planner app for Mumbai students", "pack": "saas"}).json()
    assert project["profile"]["currency"] == "INR" and project["profile"]["price"] == 0.0
    body = c.post(f"/projects/{project['id']}/price-suggestion", json={"n_agents": 100, "repeats": 3}).json()
    assert body["currency"] == "INR" and body["currency_symbol"] == "₹"
    assert body["suggestion"]["price"] > 20 and "not an exchange rate" in body["currency_note"]


def test_kit_and_council_text_use_the_founders_currency():
    assert money("INR", 500) == "₹500" and money("EUR", 4.5) == "€4.50" and money_symbol("PLN") == "PLN "


def test_currency_helpers():
    assert currency_of_country("IN") == "INR" and currency_of_country("DE") == "EUR"
    assert currency_of_country("XX") is None
    assert bare_dollar("AU") == "AUD" and bare_dollar("IN") == "USD" and bare_dollar(None) is None
    assert reference_country("INR", "IN") == "IN" and reference_country("USD", "IN") == "US"
    assert reference_country("EUR", "DE") == "DE" and reference_country("EUR", "IN") == "DE"
    assert reference_country("XYZ", "IN") is None
