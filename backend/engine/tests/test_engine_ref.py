import copy

from hypothesis import given, settings
from hypothesis import strategies as st

from backend.common.fixtures import load_fixture
from backend.engine.engine_ref import run_scenario

POP = load_fixture("population_saas")["agents"]
OPTIONS = load_fixture("options_saas")


def price_of(options, oid):
    return next(o["price"] for o in options if o["id"] == oid)


def test_same_seed_same_result():
    assert run_scenario(POP, OPTIONS, seed=7, repeats=5) == run_scenario(POP, OPTIONS, seed=7, repeats=5)


def test_different_seed_can_differ():
    a = run_scenario(POP, OPTIONS, seed=1)
    b = run_scenario(POP, OPTIONS, seed=2)
    assert [c["choice"] for c in a["choices"]] != [c["choice"] for c in b["choices"]]


def test_budget_never_violated():
    r = run_scenario(POP, OPTIONS, seed=42)
    budget = {a["id"]: a["budget"] for a in POP}
    for c in r["choices"]:
        if c["choice"] != "outside":
            assert price_of(OPTIONS, c["choice"]) <= budget[c["agent_id"]]


def test_outside_option_present_and_shares_sum_to_one():
    r = run_scenario(POP, OPTIONS, seed=42)
    assert "outside" in r["option_ids"]
    assert abs(sum(t["share"] for t in r["totals"].values()) - 1.0) < 1e-9
    assert sum(t["count"] for t in r["totals"].values()) == len(POP)


def test_everyone_unaffordable_goes_outside():
    poor = copy.deepcopy(POP)
    for a in poor:
        a["budget"] = -1.0
    r = run_scenario(poor, OPTIONS, seed=1)
    assert all(c["choice"] == "outside" for c in r["choices"])


def test_repeats_give_ordered_range():
    t = run_scenario(POP, OPTIONS, seed=42, repeats=30)["totals"]["you"]
    assert t["p10"] <= t["p50"] <= t["p90"]


def test_components_present():
    c = run_scenario(POP, OPTIONS, seed=42)["choices"][0]
    assert set(c["components"]) == {"brand", "feature", "price", "switch", "risk"}


@settings(max_examples=25, deadline=None)
@given(p_low=st.floats(0, 10), bump=st.floats(0.01, 10), seed=st.integers(0, 10_000))
def test_monotonicity_higher_price_never_raises_share(p_low, bump, seed):
    """'you' is the first option, so with a shared seed a higher price cannot gain share."""
    lo = copy.deepcopy(OPTIONS)
    hi = copy.deepcopy(OPTIONS)
    lo[0]["price"] = p_low
    hi[0]["price"] = p_low + bump
    share_lo = run_scenario(POP, lo, seed)["totals"]["you"]["count"]
    share_hi = run_scenario(POP, hi, seed)["totals"]["you"]["count"]
    assert share_hi <= share_lo


def test_thousand_agents_fast():
    import time

    big = [dict(POP[i % len(POP)], id=f"b{i}") for i in range(1000)]
    t = time.perf_counter()
    run_scenario(big, OPTIONS, seed=1, repeats=1)
    assert time.perf_counter() - t < 1.0
