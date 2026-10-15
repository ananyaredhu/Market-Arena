import copy

import pytest
from pydantic import ValidationError

from backend.scenarios.context import get_context
from backend.scenarios.overrides import (
    OverrideError,
    OverrideRequest,
    OverrideStore,
    add_override,
    apply_overrides,
    audit_trail,
    remove_override,
    run_with_overrides,
)


@pytest.fixture
def ctx():
    return get_context()


@pytest.fixture
def baseline(ctx):
    return run_with_overrides(ctx, [])[0]


def choice_of(run, agent_id):
    return next(c for c in run["choices"] if c["agent_id"] == agent_id)


def affordable_non_buyer(ctx, baseline) -> str:
    price = next(o["price"] for o in ctx.options if o["id"] == "you")
    return next(a["id"] for a in ctx.agents if a["budget"] >= price and choice_of(baseline, a["id"])["choice"] != "you")


def poor_agent(ctx) -> str:
    return next(a["id"] for a in ctx.agents if a["budget"] < 4)


# ---------------------------------------------------------------- lock
def test_lock_pins_the_choice_and_flags_it(ctx, baseline):
    aid = affordable_non_buyer(ctx, baseline)
    rec, run = add_override(ctx, OverrideRequest(type="lock", agent_id=aid, option_id="you"))
    c = choice_of(run, aid)
    assert c["choice"] == "you" and c["locked"] is True
    assert c["prev_choice"] == choice_of(baseline, aid)["choice"]  # who moved is recorded
    assert rec.created_by == "human" and "Pinned" in rec.effect
    assert run["overrides_applied"] == 1


def test_lock_to_an_unaffordable_option_is_refused_and_not_saved(ctx):
    with pytest.raises(OverrideError, match="price is above their budget"):
        add_override(ctx, OverrideRequest(type="lock", agent_id=poor_agent(ctx), option_id="you"))
    assert OverrideStore().list(ctx.project_id) == []


def test_segment_lock_applies_to_every_member(ctx):
    add_override(ctx, OverrideRequest(type="lock", segment_id="loyal", option_id="free_tool"))
    run = run_with_overrides(ctx, OverrideStore().list(ctx.project_id))[0]
    assert all(c["choice"] == "free_tool" for c in run["choices"] if c["segment"] == "loyal")


@pytest.mark.parametrize("req", [
    dict(type="lock", agent_id="a000"),  # no option
    dict(type="edit", agent_id="a000", param="budget"),  # no value
    dict(type="segment_tune", segment_id="budget", param="alpha"),  # no factor
    dict(type="segment_tune", segment_id="budget", param="alpha", factor=50),  # out of range
    dict(type="exclude"),  # no target
])
def test_malformed_requests_are_rejected(req):
    with pytest.raises(ValidationError):
        OverrideRequest(**req)


@pytest.mark.parametrize("req,fragment", [
    (dict(type="lock", agent_id="nobody", option_id="you"), "unknown customer"),
    (dict(type="lock", agent_id="a000", option_id="nope"), "unknown option"),
    (dict(type="exclude", segment_id="nope"), "unknown segment"),
    (dict(type="edit", agent_id="a000", param="mystery", value=1), "unknown parameter"),
    (dict(type="edit", agent_id="a000", param="tau", value=0), "tau must be"),
    (dict(type="edit", agent_id="a000", param="w:nope", value=1), "unknown attribute"),
])
def test_invalid_targets_and_values_are_refused(ctx, req, fragment):
    with pytest.raises(OverrideError, match=fragment):
        add_override(ctx, OverrideRequest(**req))
    assert OverrideStore().list(ctx.project_id) == []


# ---------------------------------------------------------------- edit and tune
def test_edit_changes_only_that_customer_and_records_before_and_after(ctx, baseline):
    agent = ctx.agents[3]
    rec, _ = add_override(ctx, OverrideRequest(type="edit", agent_id=agent["id"], param="budget", value=99.0))
    assert rec.before == agent["budget"] and rec.after == 99.0
    applied = apply_overrides(ctx, [rec])
    assert next(a for a in applied.agents if a["id"] == agent["id"])["budget"] == 99.0
    assert ctx.agents[3]["budget"] == agent["budget"]  # the original population is never mutated


def test_edit_a_feature_weight_and_a_brand(ctx):
    a = ctx.agents[0]["id"]
    r1, _ = add_override(ctx, OverrideRequest(type="edit", agent_id=a, param="w:ai_planning", value=0.9))
    r2, _ = add_override(ctx, OverrideRequest(type="edit", agent_id=a, param="brand:you", value=0.5))
    got = next(x for x in apply_overrides(ctx, [r1, r2]).agents if x["id"] == a)
    assert got["w"][ctx.population["attributes"].index("ai_planning")] == 0.9 and got["brand"]["you"] == 0.5


def test_segment_tune_scales_every_member(ctx):
    rec, run = add_override(ctx, OverrideRequest(type="segment_tune", segment_id="budget", param="alpha", factor=0.5))
    after = apply_overrides(ctx, [rec]).agents
    for orig, new in zip(ctx.agents, after, strict=True):
        expected = orig["alpha"] * (0.5 if orig["segment"] == "budget" else 1)
        assert new["alpha"] == pytest.approx(expected)
    assert rec.after == pytest.approx(rec.before * 0.5)


def test_edit_before_value_reflects_earlier_overrides(ctx):
    a = next(x for x in ctx.agents if x["segment"] == "budget")
    add_override(ctx, OverrideRequest(type="segment_tune", segment_id="budget", param="alpha", factor=0.5))
    rec, _ = add_override(ctx, OverrideRequest(type="edit", agent_id=a["id"], param="alpha", value=0.2))
    assert rec.before == pytest.approx(a["alpha"] * 0.5)


def test_a_later_edit_that_breaks_an_earlier_lock_is_refused(ctx, baseline):
    aid = affordable_non_buyer(ctx, baseline)
    add_override(ctx, OverrideRequest(type="lock", agent_id=aid, option_id="you"))
    with pytest.raises(OverrideError, match="price is above their budget"):
        add_override(ctx, OverrideRequest(type="edit", agent_id=aid, param="budget", value=1.0))
    assert len(OverrideStore().list(ctx.project_id)) == 1  # the refused edit was not saved


# ---------------------------------------------------------------- exclude
def test_exclude_removes_customers_from_the_run(ctx):
    _, run = add_override(ctx, OverrideRequest(type="exclude", segment_id="loyal"))
    n_loyal = sum(a["segment"] == "loyal" for a in ctx.agents)
    assert len(run["choices"]) == len(ctx.agents) - n_loyal
    assert all(c["segment"] != "loyal" for c in run["choices"])


def test_excluding_everyone_is_refused(ctx):
    for seg in {a["segment"] for a in ctx.agents} - {"power"}:
        add_override(ctx, OverrideRequest(type="exclude", segment_id=seg))
    with pytest.raises(OverrideError, match="at least one"):
        add_override(ctx, OverrideRequest(type="exclude", segment_id="power"))


def test_acting_on_an_excluded_customer_is_refused(ctx):
    aid = next(a["id"] for a in ctx.agents if a["segment"] == "loyal")
    add_override(ctx, OverrideRequest(type="exclude", segment_id="loyal"))
    with pytest.raises(OverrideError, match="already excluded"):
        add_override(ctx, OverrideRequest(type="lock", agent_id=aid, option_id="outside"))


# ---------------------------------------------------------------- undo, persistence, audit trail
def test_removing_an_override_restores_the_baseline(ctx, baseline):
    rec, _ = add_override(ctx, OverrideRequest(type="exclude", segment_id="loyal"))
    run = remove_override(ctx, rec.id)
    after = [(c["agent_id"], c["choice"]) for c in run["choices"]]
    assert after == [(c["agent_id"], c["choice"]) for c in baseline["choices"]]
    assert OverrideStore().list(ctx.project_id) == []


def test_removing_an_unknown_override_raises(ctx):
    with pytest.raises(KeyError):
        remove_override(ctx, "nope")


def test_overrides_persist_across_store_instances_and_projects_are_separate(ctx):
    add_override(ctx, OverrideRequest(type="exclude", segment_id="loyal"))
    assert len(OverrideStore().list("proj_1")) == 1  # a brand-new store object reads the same file
    assert OverrideStore().list("other_project") == []


def test_audit_trail_separates_machine_from_human(ctx):
    assert "No human adjustments" in audit_trail(ctx)["summary"]
    rec, _ = add_override(ctx, OverrideRequest(type="exclude", segment_id="loyal", note="not my market"))
    trail = audit_trail(ctx)
    assert trail["machine_generated"]["agents"] == len(ctx.agents)
    assert trail["human_adjustments"][0]["id"] == rec.id and trail["human_adjustments"][0]["note"] == "not my market"
    assert "1 human adjustment" in trail["summary"]


def test_run_without_overrides_is_the_plain_baseline(ctx, baseline):
    assert "overrides_applied" not in baseline
    assert all(c["prev_choice"] is None for c in baseline["choices"])


def test_applying_overrides_is_deterministic(ctx):
    add_override(ctx, OverrideRequest(type="segment_tune", segment_id="exam", param="budget", factor=1.5))
    items = OverrideStore().list(ctx.project_id)
    assert run_with_overrides(copy.deepcopy(ctx), items)[0] == run_with_overrides(copy.deepcopy(ctx), items)[0]
