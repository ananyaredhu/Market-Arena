import pytest

from backend.common.fixtures import load_fixture
from backend.common.stats import binom_tail, wilson_interval
from backend.engine.engine import run_scenario
from backend.glassbox.audit import CHECKS, audit
from backend.glassbox.explain import gather_facts
from backend.glassbox.narration import template_text

POP = load_fixture("population_saas")
OPTIONS = load_fixture("options_saas")


def options_for(run_name: str):
    o = [dict(x) for x in OPTIONS]
    if run_name.endswith("price3"):
        o[0]["price"] = 3.0
    return o


def gathered(run_name="run_result", choice="chain_app", agent_id=None):
    run, opts = load_fixture(run_name), options_for(run_name)
    aid = agent_id or next(c["agent_id"] for c in run["choices"] if c["choice"] == choice)
    return gather_facts(run, POP, opts, aid)


# ---------------------------------------------------------------- the audit agrees the template is faithful
@pytest.mark.parametrize("run_name", ["run_result", "run_result_price3"])
def test_every_template_sentence_is_faithful(run_name):
    run, opts = load_fixture(run_name), options_for(run_name)
    bad = []
    for c in run["choices"]:
        g = gather_facts(run, POP, opts, c["agent_id"])
        a = audit(template_text(g.facts), g)
        if not a.faithful:
            bad.append((c["agent_id"], a.failures))
    assert bad == []


def test_templates_stay_faithful_for_locked_and_unlucky_customers():
    pinned = next(a["id"] for a in POP["agents"] if a["budget"] >= 7)
    run = run_scenario(POP["agents"], OPTIONS, seed=3, locks={"agents": {pinned: "you"}})
    for c in run["choices"]:
        g = gather_facts(run, POP, OPTIONS, c["agent_id"])
        assert audit(template_text(g.facts), g).faithful, c["agent_id"]


# ---------------------------------------------------------------- it catches each kind of fault
def test_catches_a_wrong_number():
    g = gathered()
    assert "numbers" in audit("Chose ChainApp over StudyFlow because brand preference (+9.99) mattered.", g).failures


def test_catches_an_invented_option():
    g = gathered()
    f = g.facts
    outsider = next(x for x in f.option_labels if x not in {f.chosen, f.runner_up, f.your_product})
    assert "options" in audit(f"Chose {f.chosen} over {outsider} because of brand preference.", g).failures


def test_catches_an_invented_reason():
    g = gathered(choice="free_tool")
    top = {k for k, v in g.full_drivers if abs(v) >= 0.05}
    missing = next(k for k in ("risk", "switch", "brand", "feature", "price") if k not in top)
    word = {"risk": "risk", "switch": "switching", "brand": "brand", "feature": "features", "price": "price"}[missing]
    assert "reasons" in audit(f"Chose Free planner mostly because of {word}.", g).failures


def test_catches_a_missing_main_reason():
    g = gathered()
    pro = [k for k, v in g.full_drivers if v > 0 and abs(v) >= 0.05]
    other = next(k for k, _ in g.full_drivers if k not in pro[:1] and abs(_) >= 0.05)
    words = {"price": "price", "feature": "features", "brand": "brand", "switch": "switching", "risk": "risk",
             "outside": "doing nothing"}
    text = f"Chose ChainApp, even though {words[other]} counted against it."
    assert "main_reason" in audit(text, g).failures or other in pro[:1]


def test_catches_an_against_reason_presented_as_a_cause():
    """The real hallucination found with Groq: an against-reason offered as the cause of the choice."""
    run, opts = load_fixture("run_result"), options_for("run_result")
    for c in run["choices"]:
        g = gather_facts(run, POP, opts, c["agent_id"])
        against = [k for k, v in g.full_drivers if v < 0 and abs(v) >= 0.05][:3]
        if g.facts.chosen == "Do nothing" and "feature" in against:
            text = "The customer chose Do nothing because features were the biggest reason."
            assert {"direction", "main_reason"} & set(audit(text, g).failures)
            return
    pytest.skip("no suitable customer in this fixture")


def test_catches_telling_a_buyer_what_would_win_them():
    pinned = next(a["id"] for a in POP["agents"] if a["budget"] >= 7)
    run = run_scenario(POP["agents"], OPTIONS, seed=3, locks={"agents": {pinned: "you"}})
    g = gather_facts(run, POP, OPTIONS, pinned)
    if g.facts.already_top:
        pytest.skip("this customer genuinely prefers you")
    bad = "Chose StudyFlow. A price cut of 1.00 would make StudyFlow their top choice."
    assert "no_false_win" in audit(bad, g).failures


def test_catches_a_rambling_sentence():
    g = gathered()
    assert "concise" in audit("Chose ChainApp because of brand preference. " * 5, g).failures


def test_catches_a_real_number_attached_to_the_wrong_reason():
    """Found with Groq: 'the appeal of doing nothing (size 0.41)' when 0.41 is really the switching-cost size."""
    run, opts = load_fixture("run_result"), options_for("run_result")
    for c in run["choices"]:
        g = gather_facts(run, POP, opts, c["agent_id"])
        top = [(k, v) for k, v in g.full_drivers if abs(v) >= 0.05][:3]
        if len(top) >= 2 and top[0][1] > 0 and top[1][1] > 0:
            (k1, v1), (k2, v2) = top[0], top[1]
            words = {"price": "price", "feature": "features", "brand": "brand preference", "switch": "switching cost",
                     "risk": "risk", "outside": "the appeal of doing nothing"}
            swapped = (f"Chose {g.facts.chosen} because {words[k1]} ({abs(v2):.2f}) and "
                       f"{words[k2]} ({abs(v1):.2f}) mattered.")
            if abs(round(v1, 2)) != abs(round(v2, 2)):
                assert "number_binding" in audit(swapped, g).failures
                return
    pytest.skip("no customer with two reasons for the choice in this fixture")


def test_a_tie_between_two_main_reasons_is_accepted():
    """Customer a059: switching cost 0.4100 and the appeal of doing nothing 0.4090 are tied for main reason."""
    g = gathered(agent_id="a059")
    text = ("Chose Do nothing because of the appeal of doing nothing (0.41), "
            "even though features (0.59) counted against it.")
    assert audit(text, g).faithful, audit(text, g).failures


def test_correctly_attached_numbers_pass_the_binding_check():
    g = gathered()
    pro = [(k, v) for k, v in g.full_drivers if v > 0 and abs(v) >= 0.05]
    assert pro
    k, v = pro[0]
    words = {"price": "price", "feature": "features", "brand": "brand preference", "switch": "switching cost",
             "risk": "risk", "outside": "the appeal of doing nothing"}
    text = f"Chose {g.facts.chosen} mainly because of {words[k]} ({abs(v):.2f})."
    assert "number_binding" not in audit(text, g).failures


def test_every_check_name_is_reported_by_some_fault():
    assert set(CHECKS) == {"numbers", "number_binding", "reasons", "main_reason", "direction", "options",
                           "no_false_win", "concise"}


# ---------------------------------------------------------------- stats helpers
def test_wilson_interval_known_values():
    lo, hi = wilson_interval(95, 100)
    assert lo == pytest.approx(0.8882, abs=1e-3) and hi == pytest.approx(0.9784, abs=1e-3)
    assert wilson_interval(0, 0) == (0.0, 1.0)
    lo, hi = wilson_interval(10, 10)
    assert hi == 1.0 and 0.69 < lo < 0.73  # even 10/10 leaves real uncertainty


def test_binomial_tail_known_values():
    assert binom_tail(8, 10) == pytest.approx(0.0546875)
    assert binom_tail(0, 5) == pytest.approx(1.0)
    assert binom_tail(5, 5) == pytest.approx(1 / 32)
