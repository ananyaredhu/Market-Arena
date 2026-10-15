import pytest

from backend.engine.engine import run_scenario
from backend.scenarios.compare import CompareError, CompareRequest, OptionChange, apply_changes, compare
from backend.scenarios.context import get_context
from backend.scenarios.overrides import OverrideRequest, add_override


@pytest.fixture
def ctx():
    return get_context()


def req(**changes) -> CompareRequest:
    return CompareRequest(changes={k: OptionChange(**v) for k, v in changes.items()})


# ---------------------------------------------------------------- fairness and correctness
def test_default_compare_is_a_price_cut_that_gains_share(ctx):
    r = compare(ctx, CompareRequest())
    assert r["scenarios"]["b"]["summary"] == ["StudyFlow price S$7.00 → S$3.00"]
    assert r["headline"]["delta_p50"] > 0
    assert r["b"]["totals"]["you"]["share"] > r["a"]["totals"]["you"]["share"]


def test_scenario_a_is_exactly_the_plain_engine_run(ctx):
    r = compare(ctx, CompareRequest())
    assert r["a"] == run_scenario(ctx.agents, ctx.options, ctx.seed, ctx.repeats)


def test_same_seed_so_a_no_op_change_moves_nobody(ctx):
    """Common random numbers: setting your price to what it already is must not shuffle a single customer."""
    r = compare(ctx, req(you={"price": 7.0}))
    assert sum(c["prev_choice"] != c["choice"] for c in r["b"]["choices"]) == 0
    assert r["headline"]["delta_p50"] == 0 and r["revenue"]["change_pct"] == 0


def test_changing_only_a_rival_moves_only_customers_who_were_looking_at_it(ctx):
    r = compare(ctx, req(chain_app={"price": 20.0}))
    movers = [c for c in r["b"]["choices"] if c["prev_choice"] != c["choice"]]
    assert movers and all(c["prev_choice"] == "chain_app" for c in movers)  # only ChainApp's own customers can leave it
    d = {x["option_id"]: x for x in r["deltas"]}
    assert d["chain_app"]["share_b"] < d["chain_app"]["share_a"]
    assert sum(x["share_b"] - x["share_a"] for x in r["deltas"]) == pytest.approx(0)


def test_your_price_cut_only_moves_customers_to_you(ctx):
    r = compare(ctx, CompareRequest())
    movers = [c for c in r["b"]["choices"] if c["prev_choice"] != c["choice"]]
    assert movers and all(c["choice"] == "you" for c in movers)  # nobody shuffles between FreeTool and Do nothing


def test_b_carries_prev_choice_from_a(ctx):
    r = compare(ctx, CompareRequest())
    a = {c["agent_id"]: c["choice"] for c in r["a"]["choices"]}
    assert all(c["prev_choice"] == a[c["agent_id"]] for c in r["b"]["choices"])
    assert any(c["prev_choice"] != c["choice"] for c in r["b"]["choices"])


def test_headline_range_is_conservative(ctx):
    r = compare(ctx, CompareRequest())
    ya, yb = r["a"]["totals"]["you"], r["b"]["totals"]["you"]
    assert r["headline"]["delta_p50"] == pytest.approx(yb["p50"] - ya["p50"])
    assert r["headline"]["range_low"] == pytest.approx(yb["p10"] - ya["p90"])
    assert r["headline"]["range_high"] == pytest.approx(yb["p90"] - ya["p10"])
    assert r["headline"]["range_low"] <= r["headline"]["delta_p50"] <= r["headline"]["range_high"]


def test_revenue_index_shows_the_price_versus_share_tradeoff(ctx):
    r = compare(ctx, CompareRequest())
    rv = r["revenue"]
    ya, yb = r["a"]["totals"]["you"]["p50"], r["b"]["totals"]["you"]["p50"]
    assert rv["revenue_a"] == pytest.approx(ya * 7.0 * 100) and rv["revenue_b"] == pytest.approx(yb * 3.0 * 100)
    assert rv["change_pct"] == pytest.approx(rv["revenue_b"] / rv["revenue_a"] - 1)


def test_deltas_cover_every_option_and_shares_still_sum_to_one(ctx):
    r = compare(ctx, CompareRequest())
    assert {d["option_id"] for d in r["deltas"]} == set(r["a"]["option_ids"])
    for run in (r["a"], r["b"]):
        assert sum(t["share"] for t in run["totals"].values()) == pytest.approx(1.0)


def test_compare_is_deterministic(ctx):
    assert compare(ctx, CompareRequest()) == compare(get_context(), CompareRequest())


def test_flip_summary_is_for_scenario_b(ctx):
    r = compare(ctx, CompareRequest())
    assert r["flip_summary_b"] and all("text" in x for x in r["flip_summary_b"])


# ---------------------------------------------------------------- changes: features and validation
def test_feature_changes_by_name_and_by_list(ctx):
    opts = apply_changes(ctx, {"you": OptionChange(features={"integrations": 0.9})})
    assert opts[0]["features"][3] == 0.9 and opts[0]["features"][0] == ctx.options[0]["features"][0]
    opts = apply_changes(ctx, {"you": OptionChange(features=[1, 1, 1, 1])})
    assert opts[0]["features"] == [1, 1, 1, 1]
    assert ctx.options[0]["features"] == [0.8, 0.5, 0.6, 0.3]  # originals untouched


def test_better_features_gain_share(ctx):
    r = compare(ctx, req(you={"features": [1.0, 1.0, 1.0, 1.0]}))
    assert r["headline"]["delta_p50"] > 0


@pytest.mark.parametrize("changes,fragment", [
    ({"nope": OptionChange(price=1)}, "unknown option"),
    ({"outside": OptionChange(price=1)}, "outside option cannot"),
    ({"you": OptionChange(features=[0.5])}, "needs 4 values"),
    ({"you": OptionChange(features=[2, 0, 0, 0])}, "between 0 and 1"),
    ({"you": OptionChange(features={"nope": 0.5})}, "unknown feature"),
    ({}, "no changes"),
])
def test_invalid_changes_are_refused(ctx, changes, fragment):
    with pytest.raises(CompareError, match=fragment):
        compare(ctx, CompareRequest(changes=changes))


def test_negative_price_is_rejected_by_the_model():
    with pytest.raises(ValueError):
        OptionChange(price=-1)


# ---------------------------------------------------------------- overrides interplay
def test_saved_overrides_apply_to_both_scenarios(ctx):
    add_override(ctx, OverrideRequest(type="exclude", segment_id="loyal"))
    n = len(ctx.agents) - sum(a["segment"] == "loyal" for a in ctx.agents)
    r = compare(ctx, CompareRequest())
    assert len(r["a"]["choices"]) == len(r["b"]["choices"]) == n and r["overrides_applied"] == 1


def test_overrides_can_be_left_out(ctx):
    add_override(ctx, OverrideRequest(type="exclude", segment_id="loyal"))
    r = compare(ctx, CompareRequest(apply_overrides=False))
    assert len(r["a"]["choices"]) == len(ctx.agents) and r["overrides_applied"] == 0


def test_a_pinned_customer_who_cannot_afford_b_gives_a_clear_error(ctx):
    aid = next(a["id"] for a in ctx.agents if 7 <= a["budget"] < 9)
    add_override(ctx, OverrideRequest(type="lock", agent_id=aid, option_id="you"))
    with pytest.raises(CompareError, match="saved overrides"):
        compare(ctx, req(you={"price": 9.5}))
