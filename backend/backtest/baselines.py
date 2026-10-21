"""Baselines the simulator must beat to be worth anything (Master Plan 13.1).

  coin      a fair coin over the possible outcomes (expected accuracy 1/k per case). The weakest baseline.
  naive     a one-line economics rule of thumb (cheaper => demand up, dearer => down; improved features => up).
            Strong on simple price cases, so beating it is the real test.
  majority  always guess the most common outcome in the case set. It looks at the answers, so it is an oracle
            upper bound for "no model at all"; reported for context.
  llm       one prompt to a language model describing the same scenario the simulator sees ("will sales go up,
            down or stay flat?"). The model may remember the real event from its training data, which can flatter it.
"""
from __future__ import annotations

import json
import os
from collections import Counter
from statistics import median

from pydantic import BaseModel, field_validator

from backend.backtest.case import Case
from backend.backtest.runner import build_options
from backend.common.llm import LLMError, complete_json
from backend.population.packs import load_pack

LLM_VOTES = 3


def coin_expected_accuracy(case: Case) -> float:
    return 1 / len(case.outcomes)


def naive_rule(case: Case) -> str:
    before = {o["id"]: o for o in build_options(case, case.scenario_before.products)}
    if case.question_type == "success":
        prices = [o["price"] for o in before.values() if o["role"] != "outside" and o["id"] != case.subject]
        cheaper = not prices or before[case.subject]["price"] <= median(prices)
        return "success" if cheaper else "fail"
    after = {o["id"]: o for o in build_options(case, case.scenario_after.products)}
    b, a = before[case.subject], after[case.subject]
    if a["price"] != b["price"]:
        return "up" if a["price"] < b["price"] else "down"
    fb, fa = sum(b["features"]), sum(a["features"])
    return "up" if fa > fb else "down" if fa < fb else "flat"


def majority_class(cases: list[Case]) -> str | None:
    seen = Counter(c.observed for c in cases if c.observed)
    return seen.most_common(1)[0][0] if seen else None


def _describe(case: Case, products: list[dict]) -> str:
    attrs = load_pack(case.pack).attributes
    lines = []
    for o in products:
        if o.get("role") == "outside":
            continue
        feats = ", ".join(f"{a} {v:.1f}" for a, v in zip(attrs, o["features"], strict=True))
        star = " (the product being studied)" if o["id"] == case.subject else ""
        lines.append(f"- {o.get('label', o['id'])}{star}: price {o['price']}; {feats}")
    return "\n".join(lines)


def _prompt(case: Case, vote: int) -> str:
    q = case.question.strip() or "Predict the outcome."
    text = f"Question: {q}\nMarket before:\n{_describe(case, case.scenario_before.products)}\n"
    if case.question_type == "direction":
        text += f"Market after:\n{_describe(case, case.scenario_after.products)}\n"
        text += "Will sales of the studied product go up, go down, or stay flat? "
    else:
        thr = case.success.threshold if case.success else 0
        text += f"Will the studied product reach at least {thr:.0%} of this market? "
    allowed = " or ".join(f'"{o}"' for o in case.outcomes)
    return text + f'Answer with JSON {{"outcome": {allowed}}}. (Independent forecast #{vote + 1}.)'


def _answer_model(allowed: tuple[str, ...]) -> type[BaseModel]:
    class Answer(BaseModel):
        outcome: str

        @field_validator("outcome")
        @classmethod
        def _ok(cls, v: str) -> str:
            v = v.strip().lower()
            if v not in allowed:
                raise ValueError(f"outcome must be one of {allowed}")
            return v

    return Answer


def llm_baseline(case: Case) -> str | None:
    """Majority of three independent LLM forecasts, or None when no LLM is available (mock mode, outage)."""
    if os.getenv("LLM_MODE", "mock") == "mock":
        return None
    votes = []
    for k in range(LLM_VOTES):
        try:
            votes.append(complete_json("backtest_baseline", _prompt(case, k), _answer_model(case.outcomes),
                                       system="You are a careful market forecaster. Reply with JSON only.").outcome)
        except (LLMError, ValueError, json.JSONDecodeError):
            continue
    return Counter(votes).most_common(1)[0][0] if votes else None
