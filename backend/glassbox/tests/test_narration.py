import pytest

from backend.common import llm
from backend.glassbox import narration
from backend.glassbox.narration import Driver, Facts, narrate, template_text, verify

LABELS = ("StudyFlow", "Free planner", "ChainApp", "NotebookApp", "Do nothing")


def facts(**kw) -> Facts:
    base = dict(
        chosen="ChainApp",
        runner_up="StudyFlow",
        your_product="StudyFlow",
        option_labels=LABELS,
        drivers=(Driver("feature", 1.5), Driver("price", -0.7), Driver("brand", 0.3)),
        p_choice_pct=41,
        price_unreachable=True,
        feature_attr="integrations",
        feature_amount=0.62,
    )
    base.update(kw)
    return Facts(**base)


# ---------------------------------------------------------------- template
def test_template_is_faithful_to_its_own_verifier():
    assert verify(template_text(facts()), facts()) == []


@pytest.mark.parametrize(
    "kw",
    [
        dict(),
        dict(drivers=(Driver("price", -0.4),)),  # only reasons against
        dict(drivers=()),
        dict(runner_up=None),
        dict(against_odds=True),
        dict(locked=True),
        dict(feature_amount=None, feature_attr=None, price_drop=1.2, price_unreachable=False),
        dict(feature_amount=None, feature_attr=None, price_unreachable=False, switch_incentive=0.9),
        dict(feature_amount=None, feature_attr=None, price_unreachable=False),  # no lever at all
        dict(already_top=True, chosen="StudyFlow", runner_up="ChainApp", price_rise=2.4, feature_amount=None,
             feature_attr=None, price_unreachable=False),
        dict(chose_you=True, chosen="StudyFlow", runner_up="ChainApp", preferred="ChainApp", locked=True,
             feature_amount=None, feature_attr=None, price_unreachable=False),  # pinned to you against the numbers
        dict(chose_you=True, chosen="StudyFlow", runner_up="ChainApp", preferred=None, feature_amount=None,
             feature_attr=None, price_unreachable=False),
    ],
)
def test_template_passes_verifier_in_every_shape(kw):
    f = facts(**kw)
    assert verify(template_text(f), f) == [], template_text(f)


def test_template_wording():
    assert template_text(facts()) == (
        "Chose ChainApp over StudyFlow because features (+1.50) and brand preference (+0.30) outweighed price (−0.70). "
        "Improving integrations by 0.62 would make StudyFlow their top choice."
    )


# ---------------------------------------------------------------- verifier: accepts honest paraphrase
def test_accepts_natural_paraphrase_with_real_numbers():
    text = "They went with ChainApp because its features (+1.5) and brand beat StudyFlow's lower price."
    assert verify(text, facts()) == []


# ---------------------------------------------------------------- verifier: rejects hallucination
@pytest.mark.parametrize(
    "text,fragment",
    [
        ("Chose ChainApp because features (+2.3) beat price.", "number 2.3"),
        ("Chose ChainApp because features beat price, and 12 other customers agreed.", "number 12"),
        ("Chose ChainApp over Free planner because of features and price.", "Free planner"),
        ("Chose ChainApp because of features and its great support team.", None),  # no checked claim: passes
        ("Chose ChainApp because of features and fear of risk.", "risk"),
        ("Chose ChainApp because of brand preference.", "main reason"),
        ("They picked something else because of features.", "chosen option"),
        ("Chose ChainApp because features matter " + "very " * 80 + "much.", "too long"),
        ("Chose ChainApp because features matter. " * 5, "more than 3 sentences"),
        ("", "empty"),
    ],
)
def test_verifier_rejects_unfaithful_text(text, fragment):
    problems = verify(text, facts())
    if fragment is None:
        assert problems == []
    else:
        assert any(fragment in p for p in problems), problems


def test_reason_that_counted_against_the_choice_must_be_framed_as_such():
    """Found with a real model: 'chose X because the -0.55 impact from features' when features counted AGAINST X."""
    f = facts(chosen="Do nothing", runner_up="Free planner",
              drivers=(Driver("feature", -0.55), Driver("brand", -0.51), Driver("outside", 0.47)),
              price_unreachable=False, feature_amount=None, feature_attr=None)
    wrong = "The customer chose Do nothing because the −0.55 impact from features was the biggest reason."
    assert any("main reason" in p for p in verify(wrong, f))  # never mentions the appeal of doing nothing
    wrong2 = "They chose Do nothing thanks to the appeal of doing nothing (0.47) and features (0.55)."
    assert any("AGAINST" in p for p in verify(wrong2, f))  # features presented as a cause without contrast
    right = "They chose Do nothing because the appeal of doing nothing (0.47) outweighed features (0.55)."
    assert verify(right, f) == []


def test_prompt_spells_out_direction_instead_of_signed_numbers():
    d = facts().as_prompt_dict()
    assert [x["reason"] for x in d["reasons_for_choosing"]] == ["features", "brand preference"]
    assert [x["reason"] for x in d["reasons_against_choosing"]] == ["price"]
    assert all(x["size"] > 0 for x in d["reasons_for_choosing"] + d["reasons_against_choosing"])
    assert "drivers" not in d


def test_reason_not_in_facts_is_rejected():
    f = facts(drivers=(Driver("feature", 1.5),), price_unreachable=False, feature_amount=None, feature_attr=None,
              price_drop=1.0)
    assert verify("Chose ChainApp because of its features and brand.", f)  # brand is not in the facts


def test_switching_cost_is_not_mistaken_for_price():
    f = facts(drivers=(Driver("switch", -0.5), Driver("feature", 0.9)), price_unreachable=False,
              feature_amount=None, feature_attr=None, switch_incentive=0.4)
    assert verify("Chose ChainApp because features (+0.9) beat the switching cost (−0.5).", f) == []


# ---------------------------------------------------------------- narrate(): LLM path with real retry loop
@pytest.fixture
def live(monkeypatch, tmp_path):
    monkeypatch.setenv("LLM_MODE", "live")
    monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.setenv("LLM_PROVIDER_ORDER", "groq")
    monkeypatch.setattr(llm, "CACHE_DIR", tmp_path)
    llm._cooldown_until.clear()


def fake_transport(monkeypatch, answers):
    calls = []

    def transport(p, messages, timeout):
        calls.append(messages)
        a = answers[min(len(calls) - 1, len(answers) - 1)]
        if isinstance(a, Exception):
            raise a
        return {"text": '{"narration": "%s"}' % a, "usage": {}}

    monkeypatch.setattr(llm, "_http_transport", transport)
    return calls


def test_mock_mode_uses_template_and_makes_no_call(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "mock")
    text, source = narrate(facts())
    assert source == "template" and text == template_text(facts())


def test_good_llm_answer_is_used(live, monkeypatch):
    good = "They chose ChainApp mainly for its features (+1.5) and brand, even though price (−0.7) counted against it."
    fake_transport(monkeypatch, [good])
    assert narrate(facts()) == (good, "llm")


def test_hallucinated_answer_is_retried_with_the_exact_problem(live, monkeypatch):
    bad = "Chose ChainApp because features (+3.9) won."
    good = "Chose ChainApp because features (+1.5) outweighed price."
    calls = fake_transport(monkeypatch, [bad, good])
    text, source = narrate(facts())
    assert (text, source) == (good, "llm") and len(calls) == 2
    assert "number 3.9 is not in the facts" in calls[1][-1]["content"]  # the model was told what was wrong


def test_persistent_hallucination_falls_back_to_template(live, monkeypatch):
    fake_transport(monkeypatch, ["Chose ChainApp because of 17 reasons."])
    assert narrate(facts()) == (template_text(facts()), "template")


def test_provider_failure_falls_back_to_template(live, monkeypatch):
    fake_transport(monkeypatch, [TimeoutError()])
    assert narrate(facts()) == (template_text(facts()), "template")


def test_llm_prompt_contains_only_the_facts(live, monkeypatch):
    calls = fake_transport(monkeypatch, ["Chose ChainApp because features (+1.5) beat price."])
    narrate(facts())
    prompt = calls[0][-1]["content"]
    assert "ChainApp" in prompt and "1.5" in prompt and "0.62" in prompt
    assert "Free planner" not in prompt and "NotebookApp" not in prompt  # unrelated options are never shown


def test_module_exposes_no_secret_or_agent_internals():
    assert not hasattr(narration, "run_scenario")  # narration never touches the engine
