"""Score the backtest and write the report (Person A).

Headline rules (Master Plan 13.2, "honest reporting"):
  * Only sourced, real cases count. Synthetic self-tests are reported separately and never in the headline.
  * Every accuracy comes with a 95% Wilson interval, and our result is compared with chance and the baselines.
  * Failures are listed, never hidden. Cases still marked needs_sourcing are listed as such.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from backend.backtest.baselines import coin_expected_accuracy, llm_baseline, majority_class, naive_rule
from backend.backtest.case import Case
from backend.backtest.runner import REPEATS, Prediction, pack_fingerprint, predict
from backend.common.stats import binom_tail, pct, wilson_interval


@dataclass
class CaseResult:
    case_id: str
    pack: str
    synthetic: bool
    question: str
    question_type: str
    observed: str
    predicted: str
    correct: bool
    agreement: float
    mean_before: float
    mean_after: float | None
    mean_delta: float | None
    sd_delta: float | None
    naive: str
    naive_correct: bool
    coin: float
    llm: str | None
    llm_correct: bool | None
    owner_path: str


def score_case(case: Case, use_llm: bool) -> CaseResult:
    pred: Prediction = predict(case)
    naive = naive_rule(case)
    llm = llm_baseline(case) if use_llm else None
    return CaseResult(
        case_id=case.case_id, pack=case.pack, synthetic=case.synthetic, question=case.question.strip(),
        question_type=case.question_type, observed=case.observed, predicted=pred.outcome,
        correct=pred.outcome == case.observed, agreement=pred.agreement, mean_before=pred.mean_before,
        mean_after=pred.mean_after, mean_delta=pred.mean_delta, sd_delta=pred.sd_delta, naive=naive,
        naive_correct=naive == case.observed, coin=coin_expected_accuracy(case), llm=llm,
        llm_correct=(llm == case.observed) if llm is not None else None, owner_path=case.path,
    )


def evaluate(cases: list[Case], use_llm: bool = False) -> list[CaseResult]:
    return [score_case(c, use_llm) for c in cases if c.scorable]


def summarise(results: list[CaseResult], cases: list[Case]) -> dict:
    real = [r for r in results if not r.synthetic]
    k = sum(r.correct for r in real)
    n = len(real)
    chance = sum(r.coin for r in real) / n if n else 0.5
    llm_real = [r for r in real if r.llm_correct is not None]
    maj = majority_class([c for c in cases if c.scorable and not c.synthetic])
    return {
        "real_cases_scored": n,
        "ours_correct": k,
        "ours_interval": wilson_interval(k, n),
        "chance_expected": chance,
        "p_value_vs_chance": binom_tail(k, n, chance) if n else None,
        "naive_correct": sum(r.naive_correct for r in real),
        "majority_class": maj,
        "majority_correct": sum(1 for r in real if r.observed == maj) if maj else 0,
        "llm_cases": len(llm_real),
        "llm_correct": sum(1 for r in llm_real if r.llm_correct),
        "ours_vs_naive": {"ours_only": sum(r.correct and not r.naive_correct for r in real),
                          "naive_only": sum(r.naive_correct and not r.correct for r in real)},
        "synthetic_scored": sum(r.synthetic for r in results),
        "synthetic_correct": sum(r.correct for r in results if r.synthetic),
        "needs_sourcing": [c.case_id for c in cases if c.status == "needs_sourcing"],
    }


def _row(label: str, k: int, n: int) -> str:
    if n == 0:
        return f"| {label} | 0 / 0 | n/a | n/a |"
    lo, hi = wilson_interval(k, n)
    return f"| {label} | {k} / {n} | {pct(k / n)} | {pct(lo)} to {pct(hi)} |"


def render_markdown(results: list[CaseResult], cases: list[Case], problems: list[tuple[str, str]], s: dict,
                    meta: dict) -> str:
    md = ["# Backtest report", "",
          f"*Generated {meta['when']} · priors `{meta['pack_fingerprints']}` · {REPEATS} repeats × seeds per case · "
          f"LLM baseline: {'on' if meta['llm_baseline'] else 'off'}*", "",
          "**What this tests.** Whether the simulator's predicted *direction* (a price or feature change) or "
          "*success* (a launch reaching a stated target) matches what really happened in documented real events. "
          "It is not a forecast of sales and says nothing about magnitude.", ""]
    n = s["real_cases_scored"]
    if n == 0:
        md += ["## Headline", "", f"**No sourced real cases have been scored yet.** {len(s['needs_sourcing'])} case(s) "
               f"are waiting for sourcing: {', '.join(s['needs_sourcing']) or 'none'}. Until real cases exist there is "
               "no accuracy to report; the synthetic self-tests below only prove the plumbing works.", ""]
    else:
        md += ["## Headline (real, sourced cases only)", "", "| Method | Correct | Accuracy | 95% interval |",
               "|---|---|---|---|", _row("**Market Arena simulator**", s["ours_correct"], n),
               f"| Chance (fair coin over the outcomes) | n/a | {pct(s['chance_expected'])} | |",
               _row("Naive rule of thumb (cheaper → up, dearer → down)", s["naive_correct"], n),
               _row(f"Majority-class guess ('{s['majority_class']}', an oracle that sees the answers)",
                    s["majority_correct"], n)]
        if s["llm_cases"]:
            md.append(_row("Single LLM prompt (majority of 3)", s["llm_correct"], s["llm_cases"]))
        p = s["p_value_vs_chance"]
        md += ["", f"Chance of doing at least this well by luck alone: p = {p:.3f} (exact binomial). "
               f"Head to head with the naive rule: the simulator alone was right on {s['ours_vs_naive']['ours_only']} "
               f"case(s), the naive rule alone on {s['ours_vs_naive']['naive_only']}.", "",
               f"**Read the interval, not just the percentage:** with {n} case(s) the data cannot separate a good "
               "model from a lucky one.", ""]
    md += ["## Every case", "", "| Case | Question | Observed | Simulator | Seeds agree | Naive | LLM | |",
           "|---|---|---|---|---|---|---|---|"]
    for r in results:
        tag = "synthetic" if r.synthetic else ("right" if r.correct else "**wrong**")
        llm = "-" if r.llm is None else f"{r.llm} {'✓' if r.llm_correct else '✗'}"
        shift = "" if r.mean_delta is None else f" ({r.mean_delta:+.1%} ± {r.sd_delta:.1%})"
        md.append(f"| {r.case_id} | {r.question[:70]} | {r.observed} | {r.predicted}{shift} | {pct(r.agreement)} | "
                  f"{r.naive} {'✓' if r.naive_correct else '✗'} | {llm} | {tag} |")
    wrong = [r for r in results if not r.synthetic and not r.correct]
    md += ["", "## Failures", ""]
    md += [f"- **{r.case_id}**: observed `{r.observed}`, simulator said `{r.predicted}` "
           f"(share before {r.mean_before:.1%}"
           + (f", after {r.mean_after:.1%}" if r.mean_after is not None else "") + "). Explain why before using it."
           for r in wrong] or ["None among the scored real cases." if n else "No real cases scored."]
    md += ["", "## Plumbing self-test (synthetic, not counted above)", "",
           f"{s['synthetic_correct']} of {s['synthetic_scored']} synthetic cases behave as constructed.", "",
           "## Cases not scored", ""]
    unscored = [c for c in cases if not c.scorable]
    md += [f"- `{c.case_id}` ({c.status}) from `{c.path}`" for c in unscored] or ["None."]
    md += [f"- file `{f}` could not be used: {why}" for f, why in problems]
    md += ["", "## Protocol (what keeps this honest)", "",
           "1. One frozen set of priors (the pack's template) for every case; nothing is tuned per case.",
           "2. No LLM is used by the simulator side, so a result cannot depend on a model's mood.",
           "3. The prediction rule (share change of at least ±1 point is up/down, otherwise flat; success if the "
           "share reaches the threshold) is fixed in code before any outcome is looked at.",
           "4. Case inputs must come from information public *before* the event, and thresholds must be fixed "
           "beforehand with a written rationale.",
           "5. Five independent populations are simulated per case; the prediction is the majority, and how many "
           "agree is shown.",
           "6. Every outcome needs a source URL and access date; unsourced cases are never scored.", "",
           "## Limits", "",
           "- Few cases means wide intervals. This is evidence about direction on the cases tried, not proof.",
           "- Real outcomes have confounders (season, marketing, competitors) that the simulator does not model.",
           "- The pack priors are illustrative assumptions, not data. A good result says the structure is sensible; "
           "a bad one may mean the priors do not fit that market.",
           "- A language model may remember a real event from its training data, which can flatter the LLM baseline.",
           ""]
    return "\n".join(md)


def write_report(results: list[CaseResult], cases: list[Case], problems: list[tuple[str, str]], use_llm: bool,
                 out: Path) -> dict:
    s = summarise(results, cases)
    meta = {"when": datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"), "llm_baseline": use_llm,
            "pack_fingerprints": ", ".join(f"{p}:{pack_fingerprint(p)}" for p in sorted({c.pack for c in cases}))}
    out.mkdir(parents=True, exist_ok=True)
    (out / "backtest_report.md").write_text(render_markdown(results, cases, problems, s, meta))
    (out / "backtest_report.json").write_text(json.dumps(
        {"meta": meta, "summary": s, "results": [asdict(r) for r in results], "problems": problems}, indent=2,
        default=str))
    return s
