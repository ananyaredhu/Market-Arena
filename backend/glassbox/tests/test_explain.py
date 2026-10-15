import re

import pytest

from backend.common.contracts import AgentExplain
from backend.common.fixtures import load_fixture
from backend.engine.engine import run_scenario
from backend.engine.flips import build_table
from backend.glassbox.explain import AgentNotFound, drivers_for, explain_agent, money_symbol, summarize_flips

POP = load_fixture("population_saas")
OPTIONS = load_fixture("options_saas")
RUN = load_fixture("run_result")
IDS = [a["id"] for a in POP["agents"]]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "mock")


def test_every_agent_explains_and_matches_the_contract():
    for aid in IDS:
        AgentExplain.model_validate(explain_agent(RUN, POP, OPTIONS, aid))


def test_drivers_add_up_to_the_engines_own_utility_gap():
    """Strong invariant: sum of (chosen - runner-up) terms == the engine's stored gap U(chosen) - U(runner-up)."""
    checked = 0
    for ch in RUN["choices"]:
        if ch["runner_up"] is None:
            continue
        agent = next(a for a in POP["agents"] if a["id"] == ch["agent_id"])
        t = build_table([agent], OPTIONS, POP["attributes"])
        pos = {o: k for k, o in enumerate(t.ids)}
        total = sum(v for _, v in drivers_for(t, pos[ch["choice"]], pos[ch["runner_up"]], limit=None, min_abs=0.0))
        assert total == pytest.approx(ch["gap"], abs=1e-6), ch["agent_id"]
        checked += 1
    assert checked > 50


def test_every_number_in_the_sentence_comes_from_the_structured_fields():
    for aid in IDS:
        e = explain_agent(RUN, POP, OPTIONS, aid)
        allowed = {abs(d["delta"]) for d in e["top_drivers"]}
        f = e["flip"]
        allowed |= {x for x in (f["price_drop"], f["price_rise"], f["switch_incentive"]) if x is not None}
        if f["feature_boost"]:
            allowed.add(f["feature_boost"]["amount"])
        for tok in re.findall(r"\d+(?:\.\d+)?", e["narration"]):
            assert any(abs(float(tok) - a) < 0.005 for a in allowed), (aid, tok, e["narration"])


def test_unlikely_draw_is_called_out_when_p_choice_is_known():
    run = run_scenario(POP["agents"], OPTIONS, seed=3)
    for ch in run["choices"]:
        e = explain_agent(run, POP, OPTIONS, ch["agent_id"])
        if "unlikely draw" in e["narration"]:
            assert f"{round(100 * ch['p_choice'])}%" in e["narration"]
            return
    pytest.fail("expected at least one customer whose choice was not their highest-utility option")


def test_locked_choice_is_said_to_be_manual():
    agent = POP["agents"][0]["id"]
    run = run_scenario(POP["agents"], OPTIONS, seed=3, locks={"agents": {agent: "outside"}})
    assert "set manually" in explain_agent(run, POP, OPTIONS, agent)["narration"]


def test_unknown_agent_raises():
    with pytest.raises(AgentNotFound):
        explain_agent(RUN, POP, OPTIONS, "nobody")


def test_template_source_is_reported_offline():
    assert explain_agent(RUN, POP, OPTIONS, IDS[0])["narration_source"] == "template"


def test_money_symbol():
    assert money_symbol("SGD") == "S$" and money_symbol("XYZ") == "XYZ "


# ---------------------------------------------------------------- aggregate
def test_summary_rows_are_readable_and_consistent():
    rows = summarize_flips(POP, OPTIONS)
    assert rows and rows == summarize_flips(POP, OPTIONS)
    for r in rows:
        assert r["text"].startswith(f"{round(100 * r['pct'])}% of {r['segment_name']} flip to you")
        assert 0 <= r["n_flipped"] <= r["n_segment"]
