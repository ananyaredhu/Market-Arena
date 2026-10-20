"""Independent faithfulness AUDIT of Glass-Box sentences (Person A).

`narration.verify` is the GATE: it runs in real time and decides whether an LLM sentence may be shown. This module is
the MEASUREMENT: it re-checks a sentence against the engine's UNROUNDED ground truth with separate code, so the
reported "% faithful" is not circular. A sentence is faithful only if it passes every check:

  numbers       every number quoted is one of the numbers the engine produced for this customer
  number_binding each number sits next to the reason it belongs to (not a real number on the wrong reason)
  reasons       only reasons that really drove the decision (top drivers or flip levers) are mentioned
  main_reason   the biggest reason FOR the choice is mentioned
  direction     a reason that counted AGAINST the choice is framed as such (despite / even though ...)
  options       only options that are part of this decision are named
  no_false_win  a customer who already chose your product is never told what would "win" them
  concise       short enough to read (<= 320 characters, <= 3 sentences)
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from backend.glassbox.explain import Gathered
from backend.glassbox.narration import CONTRAST, LEXICON, MAX_CHARS, MAX_SENTENCES, TIE, misbound_numbers

CHECKS = ("numbers", "number_binding", "reasons", "main_reason", "direction", "options", "no_false_win", "concise")
_NUM = re.compile(r"\d+(?:\.\d+)?")
_WIN_CLAIM = re.compile(
    r"would make .* top choice|win this customer|price cut of|improving .* by|switching credit", re.I
)


@dataclass(frozen=True)
class Audit:
    faithful: bool
    failures: tuple[str, ...]  # names from CHECKS that failed


def _true_top(g: Gathered) -> list[tuple[str, float]]:
    """The (up to 3) reasons that really drove the decision, from the unrounded full list."""
    return [(k, v) for k, v in g.full_drivers if abs(v) >= 0.05][:3]


def _lever_concepts(g: Gathered) -> set[str]:
    f = g.flip
    c = set()
    if f["price_drop"] is not None or f["price_rise"] is not None or f["price_unreachable"]:
        c.add("price")
    if f["feature_boost"]:
        c.add("feature")
    if f["switch_incentive"] is not None:
        c.add("switch")
    if not (f["price_drop"] is not None or f["price_rise"] is not None or f["feature_boost"]
            or f["switch_incentive"] is not None):
        c |= {"price", "feature", "switch"}  # "no single price, feature or credit change would win this customer"
    return c


def audit(text: str, g: Gathered) -> Audit:
    failed: list[str] = []
    low = text.lower()
    top = _true_top(g)
    f = g.flip

    # numbers: only values the engine produced for THIS customer
    allowed = [round(abs(v), 2) for _, v in top]
    allowed += [x for x in (f["price_drop"], f["price_rise"], f["switch_incentive"]) if x is not None]
    if f["feature_boost"]:
        allowed.append(f["feature_boost"]["amount"])
    if g.facts.p_choice_pct is not None:
        allowed.append(float(g.facts.p_choice_pct))
    if any(not any(abs(float(t) - a) < 0.005 for a in allowed) for t in _NUM.findall(text)):
        failed.append("numbers")

    # options: only the options in this decision
    f_ = g.facts
    ok_labels = {f_.chosen, f_.your_product} | ({f_.runner_up} if f_.runner_up else set())
    ok_labels |= {f_.preferred} if f_.preferred else set()
    if any(lbl.lower() in low for lbl in set(f_.option_labels) - ok_labels):
        failed.append("options")

    # reasons: strip allowed option names first ("Do nothing" contains a reason word)
    scrubbed = low
    for lbl in ok_labels:
        scrubbed = scrubbed.replace(lbl.lower(), " ")
    cited = {k for k, words in LEXICON.items() if any(w in scrubbed for w in words)}
    allowed_concepts = {k for k, _ in top} | _lever_concepts(g)
    if cited - allowed_concepts:
        failed.append("reasons")

    # number_binding: each number must sit next to the reason it belongs to (ground truth from the unrounded drivers)
    by_reason: dict[str, set[float]] = {k: set() for k in LEXICON}
    for k, v in top:
        by_reason[k].add(round(abs(v), 2))
    for concept, value in (("price", f["price_drop"]), ("price", f["price_rise"]),
                           ("switch", f["switch_incentive"]),
                           ("feature", f["feature_boost"]["amount"] if f["feature_boost"] else None)):
        if value is not None:
            by_reason[concept].add(value)
    if misbound_numbers(scrubbed, by_reason):
        failed.append("number_binding")

    # main reason: the biggest reason FOR the choice (else the biggest number)
    pool = [(k, v) for k, v in top if v > 0] or list(top)
    if pool:
        biggest = max(abs(v) for _, v in pool)
        tied = {k for k, v in pool if abs(v) >= TIE * biggest}  # near-ties are equally valid "main reasons"
        if not tied & cited:
            failed.append("main_reason")

    # direction: reasons that counted against must be framed as such
    against = {k for k, v in top if v < 0}
    if (cited & against) and not any(c in low for c in CONTRAST):
        failed.append("direction")

    # a customer who already chose you must not be told what would win them
    if f_.chose_you and not f_.already_top and _WIN_CLAIM.search(text):
        failed.append("no_false_win")

    if len(text) > MAX_CHARS or len(re.findall(r"[.!?](?:\s|$)", text)) > MAX_SENTENCES:
        failed.append("concise")

    return Audit(faithful=not failed, failures=tuple(failed))
