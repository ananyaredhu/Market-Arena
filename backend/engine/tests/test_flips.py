import copy

import numpy as np
import pytest

from backend.common.fixtures import load_fixture
from backend.engine.flips import build_table, default_price_cut, flip_for_agent, flip_summary

POP = load_fixture("population_saas")
AGENTS = POP["agents"]
ATTRS = POP["attributes"]
OPTIONS = load_fixture("options_saas")
J = 0  # "you" is the first option


def table(options=OPTIONS, agents=AGENTS):
    return build_table(agents, options, ATTRS)


def is_top(options, agents, i) -> bool:
    """Is 'you' this agent's highest-utility AFFORDABLE option? (the thing a flip is meant to achieve)"""
    t = table(options, agents)
    if not t.afford[i, J]:
        return False
    others = [k for k in range(len(t.ids)) if k != J and t.afford[i, k]]
    return bool(t.U_raw[i, J] >= max(t.U_raw[i, k] for k in others) - 1e-9)


def with_you(**changes):
    opts = copy.deepcopy(OPTIONS)
    opts[J].update(changes)
    return opts


def flipped_cases(kind):
    t = table()
    for i in range(len(AGENTS)):
        f = flip_for_agent(t, i)
        if not f["already_top"] and f[kind]:
            yield i, f


# ---------------------------------------------------------------- the stated flips really work
def test_price_drop_closes_the_gap_and_a_smaller_drop_does_not():
    cases = list(flipped_cases("price_drop"))
    assert len(cases) > 10
    for i, f in cases:
        new_price = OPTIONS[J]["price"] - f["price_drop"]
        assert is_top(with_you(price=new_price), AGENTS, i), f"agent {i}: stated price drop does not flip"
        if f["price_drop"] > 0.05:
            assert not is_top(with_you(price=new_price + 0.05), AGENTS, i), f"agent {i}: drop is larger than needed"


def test_feature_boost_closes_the_gap():
    cases = list(flipped_cases("feature_boost"))
    assert cases, "fixture should contain agents a feature boost can flip"
    for i, f in cases:
        k = ATTRS.index(f["feature_boost"]["attr"])
        feats = list(OPTIONS[J]["features"])
        feats[k] += f["feature_boost"]["amount"]
        assert feats[k] <= 1 + 1e-9
        assert is_top(with_you(features=feats), AGENTS, i)


def test_switch_incentive_closes_the_gap_and_respects_the_switching_cost():
    t = table()
    cases = list(flipped_cases("switch_incentive"))
    assert cases
    for i, f in cases:
        assert t.alpha[i] * f["switch_incentive"] >= f["gap"] - 1e-9  # worth enough
        assert f["gap"] <= t.switch[i] + 1e-9  # cannot remove more than the switching cost they have


def test_price_rise_for_agents_who_already_prefer_you():
    """The fixture market is hostile (nobody prefers 'you'), so test in a market where 'you' is strong."""
    strong = with_you(price=1.0, features=[1.0] * len(ATTRS), novelty=0.0)
    t = table(options=strong)
    cases = [(i, flip_for_agent(t, i)) for i in range(len(AGENTS))]
    top = [(i, f) for i, f in cases if f["already_top"] and f["price_rise"] is not None]
    assert len(top) > 10
    for i, f in top:
        assert f["price_drop"] is None
        raised = copy.deepcopy(strong)
        raised[J]["price"] = strong[J]["price"] + f["price_rise"] + 0.02
        assert not is_top(raised, AGENTS, i), f"agent {i}: still prefers you after the stated price rise"


# ---------------------------------------------------------------- explicit "not possible"
def test_unaffordable_agent_needs_price_within_budget_and_gets_a_note():
    poor = copy.deepcopy(AGENTS)
    poor[0]["budget"] = 2.0
    t = table(agents=poor)
    f = flip_for_agent(t, 0)
    assert f["price_drop"] is None or f["price_drop"] >= OPTIONS[J]["price"] - 2.0 - 1e-9
    assert f["feature_boost"] is None and f["switch_incentive"] is None  # cannot fix affordability
    assert "budget" in f["note"]


def test_price_alone_cannot_flip_when_the_needed_cut_exceeds_the_price():
    stubborn = copy.deepcopy(AGENTS)
    stubborn[0]["alpha"] = 0.001  # almost price-insensitive: a huge cut would be needed
    stubborn[0]["brand"]["free_tool"] = 3.0
    f = flip_for_agent(table(agents=stubborn), 0)
    assert f["price_drop"] is None and "cannot flip" in f["note"]


def test_zero_weight_features_are_skipped():
    a = copy.deepcopy(AGENTS)
    a[0]["w"] = [0.0] * len(ATTRS)
    assert flip_for_agent(table(agents=a), 0)["feature_boost"] is None


def test_unknown_target_raises():
    with pytest.raises(ValueError):
        flip_for_agent(table(), 0, target="nope")


# ---------------------------------------------------------------- aggregate summary
def test_summary_agrees_with_the_per_agent_flips():
    """Cross-check: segment counts from the vectorised summary equal a loop over flip_for_agent."""
    t = table()
    cut = default_price_cut(OPTIONS[J]["price"])
    rows = [r for r in flip_summary(t, min_pct=0.0, top=100) if r["lever"] == "price_cut"]
    for r in rows:
        expected = 0
        for i in range(len(AGENTS)):
            if AGENTS[i]["segment"] != r["segment"]:
                continue
            f = flip_for_agent(t, i)
            if not f["already_top"] and f["price_drop"] is not None and f["price_drop"] <= cut + 1e-9:
                expected += 1
        assert r["n_flipped"] == expected, r


def test_summary_shape_and_order():
    rows = flip_summary(table(), min_pct=0.0, top=100)
    assert rows and all(0 <= r["pct"] <= 1 for r in rows)
    pcts = [r["pct"] for r in rows]
    assert pcts == sorted(pcts, reverse=True)
    assert all(r["n_flipped"] <= r["n_segment"] for r in rows)


def test_default_price_cut():
    assert default_price_cut(7.0) == 2.0 and default_price_cut(0.5) == 1.0 and np.isfinite(default_price_cut(4.8))
