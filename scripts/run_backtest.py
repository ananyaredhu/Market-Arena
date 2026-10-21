"""Run the backtest on case files and print direction accuracy against the baselines.

    python -m scripts.run_backtest                       # all case files (backtest/cases and backend/council/backtest)
    python -m scripts.run_backtest path/to/case.yaml     # specific files
    python -m scripts.run_backtest --llm-baseline        # also ask an LLM the same question (needs keys in .env)

Writes docs/eval/backtest_report.md and .json. Synthetic self-test cases are scored but never counted
in the headline.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from backend.backtest.case import load_cases
from backend.backtest.report import evaluate, write_report
from backend.backtest.runner import default_case_paths
from backend.common.env import load_env

OUT = Path(__file__).resolve().parents[1] / "docs" / "eval"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cases", nargs="*", help="case files (default: all known case folders)")
    ap.add_argument("--llm-baseline", action="store_true", help="add the single-LLM-prompt baseline (live LLM)")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)

    if args.llm_baseline:
        load_env()
        os.environ["LLM_MODE"] = "live"
    paths = [Path(p) for p in args.cases] or default_case_paths()
    cases, problems = load_cases(paths)
    results = evaluate(cases, use_llm=args.llm_baseline)
    s = write_report(results, cases, problems, args.llm_baseline, args.out)

    print(f"{len(cases)} case file(s) loaded, {len(results)} scored "
          f"({s['real_cases_scored']} real, {s['synthetic_scored']} synthetic), {len(problems)} unusable")
    for r in results:
        tag = "synthetic" if r.synthetic else ("right" if r.correct else "WRONG")
        print(f"  {r.case_id:<28} observed={r.observed:<8} ours={r.predicted:<8} ({r.agreement:.0%} of seeds) "
              f"naive={r.naive:<8} [{tag}]")
    if s["real_cases_scored"]:
        lo, hi = s["ours_interval"]
        print(f"\nOURS {s['ours_correct']}/{s['real_cases_scored']} (95% interval {lo:.0%} to {hi:.0%}); "
              f"naive {s['naive_correct']}/{s['real_cases_scored']}; chance {s['chance_expected']:.0%}; "
              f"p vs chance {s['p_value_vs_chance']:.3f}")
    else:
        print(f"\nNo real sourced cases scored yet. Waiting for sourcing: {s['needs_sourcing'] or 'none'}")
    print(f"report: {args.out / 'backtest_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
