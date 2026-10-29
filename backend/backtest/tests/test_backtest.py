import copy
from pathlib import Path

import pytest
import yaml

from backend.backtest import baselines
from backend.backtest.baselines import coin_expected_accuracy, llm_baseline, majority_class, naive_rule
from backend.backtest.case import Case, load_cases
from backend.backtest.report import evaluate, render_markdown, summarise, write_report
from backend.backtest.runner import (
    CaseError,
    build_options,
    default_case_paths,
    direction_rule,
    pack_fingerprint,
    predict,
)
from backend.common.llm import LLMError
from scripts.run_backtest import main as run_cli

PATHS = default_case_paths()
CASES, PROBLEMS = load_cases(PATHS)
BY_ID = {c.case_id: c for c in CASES}
# The plumbing tests below need a known set. Real cases keep being added, so they must not assume there are none.
PLUMBING = [c for c in CASES if c.status != "sourced"]


def raw(case_id: str) -> dict:
    return yaml.safe_load(Path(BY_ID[case_id].path).read_text())


def as_sourced(case_id: str, observed: dict | None = None, new_id: str | None = None) -> Case:
    """A real-looking case built from a synthetic one, to test the headline maths."""
    d = raw(case_id)
    d.update(status="sourced", case_id=new_id or case_id + "_real",
             sources=[{"url": "https://example.com/source", "accessed": "2026-10-15", "supports": "outcome"}])
    if observed:
        d["observed_outcome"] = observed
    return Case.model_validate(d)


# ---------------------------------------------------------------- loading and refusing unsafe cases
def test_all_shipped_case_files_load():
    assert PROBLEMS == [] and len(CASES) >= 6


def test_b_case_waiting_for_sourcing_is_listed_but_never_scored():
    c = BY_ID["cafe_case_01"]
    assert c.status == "needs_sourcing" and not c.scorable and c.observed is None
    assert "cafe_case_01" not in {r.case_id for r in evaluate(CASES)}


def test_synthetic_cases_are_scorable_but_flagged():
    assert all(c.scorable and c.synthetic for c in CASES if c.case_id.startswith("selftest_"))


def test_a_sourced_case_without_sources_is_refused():
    d = raw("selftest_price_cut") | {"status": "sourced", "case_id": "x", "sources": []}
    with pytest.raises(ValueError, match="at least one source"):
        Case.model_validate(d)


def test_a_sourced_case_without_an_observed_outcome_is_refused():
    d = raw("selftest_price_cut") | {"status": "sourced", "case_id": "x", "observed_outcome": None,
                                      "sources": [{"url": "u"}]}
    with pytest.raises(ValueError, match="observed_outcome"):
        Case.model_validate(d)


def test_a_direction_case_needs_an_after_scenario():
    d = raw("selftest_price_cut") | {"scenario_after": None}
    with pytest.raises(ValueError, match="scenario_after"):
        Case.model_validate(d)


def test_a_success_case_needs_a_threshold():
    d = raw("selftest_launch_success") | {"success": None}
    with pytest.raises(ValueError, match="success"):
        Case.model_validate(d)


def test_an_unreadable_file_is_reported_not_fatal(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("case_id: x\npack: saas\nstatus: nonsense\n")
    cases, problems = load_cases([bad, Path(BY_ID["selftest_price_cut"].path)])
    assert len(cases) == 1 and problems and "bad.yaml" in problems[0][0]


def test_product_with_wrong_feature_count_is_refused():
    c = copy.deepcopy(BY_ID["selftest_price_cut"])
    c.scenario_before.products[0]["features"] = [0.5]
    with pytest.raises(CaseError, match="needs 4 feature values"):
        build_options(c, c.scenario_before.products)


def test_unknown_subject_is_refused():
    c = copy.deepcopy(BY_ID["selftest_price_cut"])
    c.subject = "ghost"
    with pytest.raises(CaseError, match="subject"):
        build_options(c, c.scenario_before.products)


# ---------------------------------------------------------------- predictions
@pytest.mark.parametrize("case_id", [c.case_id for c in CASES if c.case_id.startswith("selftest_")])
def test_synthetic_cases_behave_as_constructed(case_id):
    c = BY_ID[case_id]
    p = predict(c)
    assert p.outcome == c.observed and p.agreement == 1.0


def test_prediction_is_deterministic():
    c = BY_ID["selftest_price_cut"]
    a, b = predict(c), predict(c)
    assert a.outcome == b.outcome and a.mean_delta == b.mean_delta


def test_no_change_gives_exactly_zero_movement():
    p = predict(BY_ID["selftest_no_change"])
    assert p.mean_delta == 0 and p.outcome == "flat"


def test_direction_rule_thresholds():
    assert direction_rule(0.02, 0.01) == "up" and direction_rule(-0.02, 0.01) == "down"
    assert direction_rule(0.005, 0.01) == "flat" and direction_rule(0.01, 0.01) == "up"


def test_pack_fingerprint_is_stable():
    assert pack_fingerprint("saas") == pack_fingerprint("saas") and len(pack_fingerprint("saas")) == 12


# ---------------------------------------------------------------- baselines
def test_coin_expectation_depends_on_the_number_of_outcomes():
    assert coin_expected_accuracy(BY_ID["selftest_price_cut"]) == pytest.approx(1 / 3)
    assert coin_expected_accuracy(BY_ID["selftest_launch_success"]) == 0.5


def test_naive_rule():
    assert naive_rule(BY_ID["selftest_price_cut"]) == "up" and naive_rule(BY_ID["selftest_price_rise"]) == "down"
    assert naive_rule(BY_ID["selftest_no_change"]) == "flat"
    assert naive_rule(BY_ID["selftest_launch_success"]) == "success"
    assert naive_rule(BY_ID["selftest_launch_fail"]) == "fail"


def test_naive_rule_uses_features_when_the_price_is_unchanged():
    c = copy.deepcopy(BY_ID["selftest_no_change"])
    c.scenario_after.products[0]["features"] = [0.9, 0.9, 0.9, 0.9]
    assert naive_rule(c) == "up"


def test_majority_class():
    assert majority_class([BY_ID["selftest_price_cut"], BY_ID["selftest_price_rise"], BY_ID["selftest_no_change"],
                           BY_ID["selftest_launch_success"]]) in {"up", "down", "flat", "success"}
    assert majority_class([]) is None


def test_llm_baseline_is_off_in_mock_mode(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "mock")
    assert llm_baseline(BY_ID["selftest_price_cut"]) is None


def test_llm_baseline_takes_the_majority_and_ignores_invalid_answers(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "live")
    answers = iter(["up", "up", "sideways"])  # the third is not an allowed outcome

    def fake(task, prompt, model, **kw):
        return model.model_validate({"outcome": next(answers)})

    monkeypatch.setattr(baselines, "complete_json", fake)
    assert llm_baseline(BY_ID["selftest_price_cut"]) == "up"


def test_llm_baseline_is_none_when_the_provider_fails(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "live")

    def boom(*a, **k):
        raise LLMError("down")

    monkeypatch.setattr(baselines, "complete_json", boom)
    assert llm_baseline(BY_ID["selftest_price_cut"]) is None


# ---------------------------------------------------------------- scoring and the headline
def test_synthetic_cases_never_count_in_the_headline():
    s = summarise(evaluate(PLUMBING), PLUMBING)
    assert s["real_cases_scored"] == 0 and s["synthetic_scored"] == 5 and s["synthetic_correct"] == 5
    assert "cafe_case_01" in s["needs_sourcing"]


def test_a_wrong_prediction_is_marked_wrong_and_listed_as_a_failure():
    wrong = as_sourced("selftest_price_cut", {"direction": "down", "metric": "units"}, "real_wrong")
    right = as_sourced("selftest_price_rise", None, "real_right")
    results = evaluate([wrong, right])
    s = summarise(results, [wrong, right])
    assert s["real_cases_scored"] == 2 and s["ours_correct"] == 1
    md = render_markdown(results, [wrong, right], [], s,
                         {"when": "now", "pack_fingerprints": "saas:x", "llm_baseline": False})
    assert "real_wrong" in md.split("## Failures")[1].split("##")[0] and "**wrong**" in md


def test_headline_reports_an_interval_and_the_comparison_with_chance():
    cases = [as_sourced("selftest_price_cut", None, "r1"), as_sourced("selftest_price_rise", None, "r2"),
             as_sourced("selftest_no_change", None, "r3")]
    results = evaluate(cases)
    s = summarise(results, cases)
    assert s["ours_correct"] == 3 and 0 < s["ours_interval"][0] < 1
    assert s["p_value_vs_chance"] == pytest.approx((1 / 3) ** 3)  # three direction cases, chance 1/3 each
    md = render_markdown(results, cases, [], s, {"when": "now", "pack_fingerprints": "saas:x", "llm_baseline": False})
    assert "95% interval" in md and "Read the interval" in md and "oracle" in md


def test_report_says_plainly_when_there_are_no_real_cases():
    results = evaluate(PLUMBING)
    s = summarise(results, PLUMBING)
    md = render_markdown(results, PLUMBING, PROBLEMS, s, {"when": "now", "pack_fingerprints": "saas:x",
                                                       "llm_baseline": False})
    assert "No sourced real cases have been scored yet" in md and "cafe_case_01" in md
    assert "Plumbing self-test" in md and "5 of 5" in md


def test_write_report_creates_both_files(tmp_path):
    results = evaluate(CASES)
    write_report(results, CASES, PROBLEMS, False, tmp_path)
    assert (tmp_path / "backtest_report.md").exists() and (tmp_path / "backtest_report.json").exists()


def test_cli_end_to_end(tmp_path, capsys):
    assert run_cli(["--out", str(tmp_path), *[c.path for c in PLUMBING]]) == 0
    out = capsys.readouterr().out
    assert "5 scored" in out and "0 real" in out and (tmp_path / "backtest_report.md").exists()


# ---------------------------------------------------------------- the real cases that are committed
REAL = [c for c in CASES if c.status == "sourced"]


@pytest.mark.parametrize("case", REAL, ids=[c.case_id for c in REAL])
def test_every_committed_real_case_is_complete_and_dated(case):
    assert not case.synthetic and case.observed is not None and case.limitations.strip()
    assert all(src.get("url", "").startswith("https://") and src.get("accessed") and src.get("supports")
               for src in case.sources)
    assert any("sec.gov" in src["url"] or "investor." in src["url"] for src in case.sources), \
        "a real case needs at least one primary source"
    assert case.scorable and case.scenario_before.products
