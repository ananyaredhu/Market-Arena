"""Intake rules: reading a price, a country and a name from a founder's idea, and warning when the pack does not fit."""
import pytest
from fastapi.testclient import TestClient

from backend.common.money import money_symbol
from backend.intake.geography import detect_geography, normalise_geography
from backend.intake.projects import ProjectCreateRequest, _extract_price, _product_name, build_product_profile
from backend.kit.generator import money
from backend.main import app
from backend.population.packs import load_pack

client = TestClient(app)


def profile(idea, pack="saas", geography=None):
    return build_product_profile(ProjectCreateRequest(idea=idea, pack=pack, geography=geography))


# ---------------------------------------------------------------------------------------------------- prices
@pytest.mark.parametrize("text,expected", [
    ("at S$9 a month", (9.0, "SGD")), ("at US$9", (9.0, "USD")), ("at SGD 9", (9.0, "SGD")), ("9 SGD", (9.0, "SGD")),
    ("at $9", (9.0, "SGD")), ("$9", (9.0, "SGD")), ("3$", (3.0, "SGD")), ("for $9.99/mo", (9.99, "SGD")),
    ("9 dollars monthly", (9.0, "SGD")), ("€4.50 a latte", (4.5, "EUR")), ("500 rupees", (500.0, "INR")),
    ("£3", (3.0, "GBP")), ("$1,500 per year", (1500.0, "SGD")), ("costs 1.5 SGD and 3 dollars", (1.5, "SGD")),
])
def test_prices_in_the_usual_forms_are_read(text, expected):
    assert _extract_price(text, "SGD") == expected


@pytest.mark.parametrize("text", [
    "for 9 students", "3 cups a day", "version 2.5 of the app", "a 5-minute walk", "0$ is free", "founded in 2019",
    "no price in here",
])
def test_a_number_without_a_currency_is_never_a_price(text):
    assert _extract_price(text, "SGD") is None


def test_the_earliest_price_wins_whatever_its_form():
    assert _extract_price("3 dollars now, S$9 later", "SGD") == (3.0, "SGD")
    assert _extract_price("S$9 now, or 3 dollars with the annual plan", "SGD") == (9.0, "SGD")


def test_a_bare_dollar_sign_is_the_markets_own_dollar_else_us_dollars_else_the_packs():
    assert _extract_price("$9", "SGD", "US") == (9.0, "USD")
    assert _extract_price("$9", "SGD", "AU") == (9.0, "AUD")
    assert _extract_price("$9", "SGD", "SG") == (9.0, "SGD")
    assert _extract_price("$9", "SGD", "DE") == (9.0, "USD")  # Germany has no dollar of its own
    assert _extract_price("$9", "SGD", None) == (9.0, "SGD")  # no market named: the pack's currency, as before


def test_the_original_bug_a_bare_dollar_price_now_gives_a_price_and_no_question():
    p = profile("A study planner app for NUS students at $9 a month")
    assert p.price == 9.0 and "What price will customers pay?" not in p.missing_assumptions


def test_the_founders_own_currency_is_kept_and_nothing_says_it_will_be_read_as_sgd():
    p = profile("An app for Mumbai students at 500 rupees a month")
    assert (p.price, p.currency, p.geography) == (500.0, "INR", "IN")
    assert not any("SGD" in m or "converted" in m for m in p.missing_assumptions)


def test_without_a_written_currency_the_countrys_currency_is_used():
    assert profile("A cafe in Berlin selling oat lattes", "cafe").currency == "EUR"
    assert profile("A study planner app for Mumbai students").currency == "INR"
    assert profile("A study planner app for students").currency == "SGD"  # no country named: the pack's


# ---------------------------------------------------------------------------------------------------- geography
@pytest.mark.parametrize("text,code", [
    ("A cafe in Berlin selling lattes", "DE"), ("pet grooming in Mumbai", "IN"), ("coffee in Turkey", "TR"),
    ("app for US students", "US"), ("an app in singapore", "SG"), ("Hong Kong cafe", "HK"),
    ("from Mumbai to Singapore", "IN"),
])
def test_a_country_or_city_named_in_the_idea_is_found(text, code):
    assert detect_geography(text) == code


@pytest.mark.parametrize("text", [
    "help us build an app", "We sell turkey sandwiches", "NUS students", "an app for students", "a chilean wine club",
])
def test_ordinary_words_are_not_countries(text):
    assert detect_geography(text) is None


def test_geography_can_be_given_as_a_code_or_a_name():
    assert [normalise_geography(x) for x in ("sg", "Germany", "usa", "Berlin", " ", None)] == [
        "SG", "DE", "US", "DE", None, None]
    assert profile("a study planner app at $9", geography="germany").geography == "DE"


def test_geography_read_from_the_text_replaces_the_singapore_question():
    p = profile("A cafe in Berlin selling oat lattes for €4.50", "cafe")
    assert p.geography == "DE" and not any("geography" in m for m in p.missing_assumptions)
    q = profile("A study planner app for students at $9")
    assert q.geography == "SG" and any("Which geography" in m for m in q.missing_assumptions)


# ---------------------------------------------------------------------------------------------------- pack fit
def test_an_idea_that_does_not_fit_the_pack_is_warned_not_refused():
    p = profile("A pet-grooming marketplace in Mumbai for 500 rupees")
    assert "does not clearly match" in p.missing_assumptions[0]
    wrong = profile("A cafe in Berlin selling oat lattes for €4.50", "saas")
    assert "reads like a cafe idea" in wrong.missing_assumptions[0]


def test_a_fitting_idea_gets_no_fit_warning():
    for idea, pack in (("StudyFlow is an AI planner for students", "saas"), ("A coffee shop near the MRT", "cafe")):
        assert not any("market" in m and "idea" in m for m in profile(idea, pack).missing_assumptions)


# ---------------------------------------------------------------------------------------------------- questions, names
def test_the_cafe_pack_asks_about_free_samples_like_saas_asks_about_a_trial():
    asked = "Is there a free sample, loyalty reward or introductory offer?"
    assert asked in profile("A coffee shop near the MRT at S$5", "cafe").missing_assumptions
    assert asked not in profile("A coffee shop near the MRT, loyalty points, S$5", "cafe").missing_assumptions


def test_names_keep_their_own_capitals():
    assert _product_name("StudyFlow is an AI planner for students", "saas") == "StudyFlow"
    assert _product_name("A study planner app for NUS students", "saas") == "Study Planner App"
    assert _product_name("A cafe in Berlin, selling oat lattes for 4", "cafe") == "Cafe In Berlin"


# ---------------------------------------------------------------------------------------------------- currency
def test_both_packs_name_their_currency_by_code_and_money_reads_as_a_symbol():
    assert load_pack("cafe").currency == load_pack("saas").currency == "SGD"
    assert money("SGD", 7) == "S$7" and money("S$", 7.5) == "S$7.50" and money("XYZ", 3) == "XYZ 3"
    assert money_symbol("INR") == "₹"


# ---------------------------------------------------------------------------------------------------- price suggestion
def test_a_project_without_a_price_gets_a_suggestion_and_nothing_is_saved(monkeypatch, tmp_path):
    monkeypatch.setenv("MOCK", "0")
    monkeypatch.setenv("MARKET_ARENA_DATA_DIR", str(tmp_path / "projects"))
    project = client.post("/projects", json={"idea": "A study planner app for NUS students", "pack": "saas"}).json()
    assert project["profile"]["price"] == 0.0
    r = client.post(f"/projects/{project['id']}/price-suggestion", json={"n_agents": 100, "repeats": 3})
    assert r.status_code == 200
    body = r.json()
    assert body["price_was_missing"] is True and body["placeholder_price"] == 7.0
    best = body["suggestion"]["price"]
    assert best > 0 and body["band"]["low"] <= best <= body["band"]["high"]
    assert body["reference_prices"] == [] and "not saved" in body["basis"]
    assert client.get(f"/projects/{project['id']}").json()["profile"]["price"] == 0.0  # the project is unchanged


def test_the_suggestion_is_the_same_whatever_placeholder_price_is_used(monkeypatch, tmp_path):
    monkeypatch.setenv("MOCK", "0")
    monkeypatch.setenv("MARKET_ARENA_DATA_DIR", str(tmp_path / "projects"))
    free = client.post("/projects", json={"idea": "A study planner app for NUS students", "pack": "saas"}).json()
    idea = "A study planner app for NUS students at S$12"
    priced = client.post("/projects", json={"idea": idea, "pack": "saas"}).json()
    ask = {"n_agents": 100, "repeats": 3}
    a = client.post(f"/projects/{free['id']}/price-suggestion", json=ask).json()
    b = client.post(f"/projects/{priced['id']}/price-suggestion", json=ask).json()
    assert a["suggestion"]["price"] == b["suggestion"]["price"] and b["price_was_missing"] is False


def test_an_unknown_project_is_a_404(monkeypatch, tmp_path):
    monkeypatch.setenv("MOCK", "0")
    monkeypatch.setenv("MARKET_ARENA_DATA_DIR", str(tmp_path / "projects"))
    assert client.post("/projects/nope/price-suggestion").status_code == 404
