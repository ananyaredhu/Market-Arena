import copy
import time

import pytest

from backend.common.contracts import RunResult
from backend.common.fixtures import load_fixture
from backend.engine import engine, engine_ref

POP = load_fixture("population_saas")["agents"]
OPTIONS = load_fixture("options_saas")
NEW_FIELDS = ("p_choice", "locked")


def strip_new(result: dict) -> dict:
    out = copy.deepcopy(result)
    for c in out["choices"]:
        for k in NEW_FIELDS:
            c.pop(k)
    return out


def by_id(result: dict) -> dict:
    return {c["agent_id"]: c for c in result["choices"]}


# ---------------------------------------------------------------- parity with the reference engine
def test_matches_reference_when_no_new_options_used():
    assert strip_new(engine.run_scenario(POP, OPTIONS, seed=42)) == engine_ref.run_scenario(POP, OPTIONS, seed=42)


def test_canonical_run_unchanged_by_repeats():
    """Repeat 0 drives choices and counts, so asking for more repeats never changes who chose what."""
    one = engine.run_scenario(POP, OPTIONS, seed=42, repeats=1)
    many = engine.run_scenario(POP, OPTIONS, seed=42, repeats=30)
    assert one["choices"] == many["choices"]
    assert {k: v["count"] for k, v in one["totals"].items()} == {k: v["count"] for k, v in many["totals"].items()}


def test_result_validates_against_contract():
    RunResult.model_validate(engine.run_scenario(POP, OPTIONS, seed=42, repeats=5))


# ---------------------------------------------------------------- locks
def test_agent_lock_is_honoured_and_flagged():
    target = POP[0]["id"]
    r = engine.run_scenario(POP, OPTIONS, seed=42, locks={"agents": {target: "outside"}})
    c = by_id(r)[target]
    assert c["choice"] == "outside" and c["locked"] is True
    assert sum(1 for x in r["choices"] if x["locked"]) == 1


def test_segment_lock_and_agent_lock_beats_segment():
    seg = "loyal"
    members = [a["id"] for a in POP if a["segment"] == seg]
    exception = members[0]
    r = engine.run_scenario(
        POP, OPTIONS, seed=42, locks={"segments": {seg: "free_tool"}, "agents": {exception: "outside"}}
    )
    got = by_id(r)
    assert got[exception]["choice"] == "outside"
    assert all(got[a]["choice"] == "free_tool" for a in members[1:])


def test_lock_does_not_change_other_agents():
    free = [a for a in POP if a["budget"] >= 0][0]["id"]
    base = by_id(engine.run_scenario(POP, OPTIONS, seed=42))
    locked = by_id(engine.run_scenario(POP, OPTIONS, seed=42, locks={"agents": {free: "outside"}}))
    assert all(base[a]["choice"] == locked[a]["choice"] for a in base if a != free)


@pytest.mark.parametrize(
    "locks",
    [
        {"agents": {"nobody": "outside"}},
        {"agents": {POP[0]["id"]: "nonexistent_option"}},
    ],
)
def test_bad_locks_raise(locks):
    with pytest.raises(ValueError):
        engine.run_scenario(POP, OPTIONS, seed=42, locks=locks)


def test_lock_to_unaffordable_option_raises():
    poor = copy.deepcopy(POP)
    poor[0]["budget"] = 1.0  # cannot afford "you" at S$7
    with pytest.raises(ValueError, match="unaffordable"):
        engine.run_scenario(poor, OPTIONS, seed=42, locks={"agents": {poor[0]["id"]: "you"}})


# ---------------------------------------------------------------- prev
def test_prev_fills_prev_choice():
    cut = copy.deepcopy(OPTIONS)
    cut[0]["price"] = 3.0
    base = engine.run_scenario(POP, OPTIONS, seed=42)
    after = engine.run_scenario(POP, cut, seed=42, prev=base)
    before = by_id(base)
    assert all(c["prev_choice"] == before[c["agent_id"]]["choice"] for c in after["choices"])
    assert any(c["prev_choice"] != c["choice"] for c in after["choices"])  # somebody moved


def test_no_prev_means_no_prev_choice():
    assert all(c["prev_choice"] is None for c in engine.run_scenario(POP, OPTIONS, seed=42)["choices"])


# ---------------------------------------------------------------- jitter and ranges
def width(result: dict) -> float:
    return sum(t["p90"] - t["p10"] for t in result["totals"].values())


def test_jitter_widens_ranges():
    """Needs a big population: with few agents dice-roll noise swamps the assumption shocks."""
    big = [dict(POP[i % len(POP)], id=f"b{i}") for i in range(len(POP) * 50)]
    flat = engine.run_scenario(big, OPTIONS, seed=42, repeats=30, jitter=0.0)
    jittery = engine.run_scenario(big, OPTIONS, seed=42, repeats=30, jitter=0.3)
    assert width(jittery) > 1.5 * width(flat)  # measured: about 2.4x


def test_shocks_are_shared_within_a_segment():
    """Guards the design choice: independent per-agent noise would leave ranges unchanged."""
    big = [dict(POP[i % len(POP)], id=f"b{i}") for i in range(len(POP) * 50)]
    t = engine.run_scenario(big, OPTIONS, seed=42, repeats=30, jitter=0.3)["totals"]["free_tool"]
    assert t["p90"] - t["p10"] > 0.03


def test_ranges_are_ordered_and_contain_nothing_impossible():
    for t in engine.run_scenario(POP, OPTIONS, seed=42, repeats=30)["totals"].values():
        assert 0 <= t["p10"] <= t["p50"] <= t["p90"] <= 1


# ---------------------------------------------------------------- rules that must always hold
def test_deterministic_with_everything_on():
    kw = dict(seed=7, repeats=10, jitter=0.2, locks={"segments": {"loyal": "free_tool"}})
    assert engine.run_scenario(POP, OPTIONS, **kw) == engine.run_scenario(POP, OPTIONS, **kw)


def test_budget_never_violated_in_canonical_choices():
    budget = {a["id"]: a["budget"] for a in POP}
    price = {o["id"]: o.get("price", 0.0) for o in OPTIONS}
    for c in engine.run_scenario(POP, OPTIONS, seed=42, repeats=20, jitter=0.4)["choices"]:
        assert c["choice"] == "outside" or price[c["choice"]] <= budget[c["agent_id"]]


def test_p_choice_is_a_probability():
    for c in engine.run_scenario(POP, OPTIONS, seed=42)["choices"]:
        assert 0.0 <= c["p_choice"] <= 1.0


def test_thousand_agents_thirty_repeats_under_a_second():
    big = [dict(POP[i % len(POP)], id=f"b{i}") for i in range(1000)]
    t = time.perf_counter()
    engine.run_scenario(big, OPTIONS, seed=1, repeats=30)
    assert time.perf_counter() - t < 1.0
