import pytest
from fastapi.testclient import TestClient

from backend.evidence import store
from backend.evidence.models import EvidenceSnapshot, Finding
from backend.main import app
from backend.scenarios.context import get_context
from backend.scenarios.overrides import OverrideRequest, add_override
from backend.scenarios.pricing import PriceSuggestRequest, PricingError, suggest_price

client = TestClient(app)


@pytest.fixture(autouse=True)
def empty_library(monkeypatch, tmp_path):
    monkeypatch.setattr(store, "RUN_DIR", tmp_path / "evidence")


def suggest(**kw):
    return suggest_price(get_context(), PriceSuggestRequest(**kw))


def test_the_suggestion_is_the_price_with_the_best_revenue_index():
    r = suggest()
    best = max(r["curve"], key=lambda row: row["revenue_index"])
    assert r["objective"] == "revenue index" and r["suggestion"]["price"] == best["price"]
    assert r["band"]["low"] <= r["suggestion"]["price"] <= r["band"]["high"]
    assert r["suggestion"]["revenue_index"] == pytest.approx(best["share_p50"] * best["price"] * 100)


def test_the_curve_covers_the_current_price_and_is_sorted():
    r = suggest()
    prices = [row["price"] for row in r["curve"]]
    assert prices == sorted(prices) and len(prices) == len(set(prices))
    assert [row["price"] for row in r["curve"] if row["is_current"]] == [r["current_price"]]


def test_a_cost_is_the_floor_and_the_suggestion_follows_profit():
    r = suggest(cost=4.0)
    assert r["objective"] == "profit index" and r["curve"][0]["price"] >= 4.0
    best = max(r["curve"], key=lambda row: row["profit_index"])
    assert r["suggestion"]["price"] == best["price"] and best["price"] > 4.0
    for row in r["curve"]:
        assert row["profit_index"] == pytest.approx(row["share_p50"] * (row["price"] - 4.0) * 100)


def test_a_higher_cost_never_lowers_the_suggested_price():
    low, high = suggest(cost=1.0)["suggestion"]["price"], suggest(cost=6.0)["suggestion"]["price"]
    assert high >= low


def test_a_cost_nobody_can_cover_says_so_instead_of_suggesting_a_price():
    r = suggest(cost=17.0, max_price=25.0)  # every price above cost is beyond what customers will pay
    assert r["suggestion"] is None and r["band"] is None and "earns anything" in r["notes"][0]


def test_a_minimum_not_below_the_maximum_is_refused_with_a_reason():
    with pytest.raises(PricingError, match="not below the highest"):
        suggest(cost=30.0, max_price=10.0)


def test_the_user_can_set_the_range_and_an_edge_best_price_is_flagged():
    r = suggest(min_price=0.5, max_price=3.0)
    assert r["curve"][0]["price"] == 0.5 and r["curve"][-1]["price"] == 3.0
    assert any("highest price tried" in n and "beyond it" in n for n in r["notes"])
    assert not any("beyond it" in n for n in suggest()["notes"])  # the default range brackets the best price


def test_the_same_request_gives_the_same_answer():
    assert suggest(cost=2.0) == suggest(cost=2.0)


def test_the_band_is_one_unbroken_run_of_prices():
    r = suggest()
    inside = [row["price"] for row in r["curve"] if r["band"]["low"] <= row["price"] <= r["band"]["high"]]
    assert all(row["revenue_index"] >= 0.95 * r["suggestion"]["revenue_index"]
               for row in r["curve"] if row["price"] in inside)


def test_saved_overrides_shape_the_curve():
    ctx = get_context()
    before = suggest_price(ctx, PriceSuggestRequest())
    buyers = [a["id"] for a in ctx.agents][:40]
    for agent in buyers:
        add_override(ctx, OverrideRequest(type="exclude", agent_id=agent))
    after = suggest_price(get_context(), PriceSuggestRequest())
    assert after["overrides_applied"] == 40 and after["customers"] == before["customers"] - 40
    assert after["curve"] != before["curve"]
    assert suggest_price(get_context(), PriceSuggestRequest(apply_overrides=False))["curve"] == before["curve"]


def test_real_prices_are_shown_as_reference_and_never_change_the_curve():
    base = suggest()
    store.save(EvidenceSnapshot(
        snapshot_id="ev_p", created_at="2026-10-27T00:00:00+00:00", pack="saas", geography="SG", status="ok",
        findings=[Finding(kind="competitor_price", subject="chain_app", claim="Taskade Pro is $10 a month", value=10.0,
                          currency="USD", quote="Pro $10/mo", url="https://www.taskade.com/blog/x")]))
    shown = suggest()
    assert shown["curve"] == base["curve"] and shown["suggestion"] == base["suggestion"]
    assert base["reference_prices"] == []
    assert [p["domain"] for p in shown["reference_prices"]] == ["taskade.com"]
    assert "not used in the curve" in shown["reference_note"]


def test_a_small_population_is_called_out_as_noisy():
    assert any("steps of" in n for n in suggest()["notes"])  # the fixture market has 80 customers


def test_route():
    r = client.post("/pricing/suggest", json={"cost": 2.0, "steps": 8})
    assert r.status_code == 200
    body = r.json()
    assert len(body["curve"]) >= 8 and body["suggestion"]["price"] > 2.0 and body["currency_symbol"] == "S$"
    assert client.post("/pricing/suggest", json={"cost": 30.0, "max_price": 10.0}).status_code == 422
    assert client.post("/pricing/suggest", json={"steps": 2}).status_code == 422
    assert client.post("/pricing/suggest").status_code == 200
