"""Competitor Strategist: one-step best response for every rival.

For each competitor, four bounded moves are applied in turn and evaluated
through the engine adapter. The engine's numbers decide the winner; no LLM is
involved.

Selection rule: the candidate with the most negative change in our share
wins. Changes within ``TIE_TOLERANCE`` of each other are ties, broken by the
competitor's position in the input option list and then by ``MOVES`` order
(earlier wins). A move is only selected if it reduces our share by more than
``TIE_TOLERANCE``.
"""
from __future__ import annotations

import copy
import math
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Tuple

from council.engine_adapter import YOU_ID, EngineAdapter

MOVES: Tuple[str, ...] = ("price_cut_10", "price_cut_20", "add_feature", "promo")
PRICE_CUTS = {"price_cut_10": 0.10, "price_cut_20": 0.20}
# Illustrative modelling assumptions for non-price moves (need team approval).
FEATURE_STEP = 0.3        # added to one attribute, capped at 1.0
PROMO_BRAND_BOOST = 0.3   # added to every agent's brand affinity for the rival
TIE_TOLERANCE = 1e-9
TIE_BREAK_RULE = (
    "Largest reduction in our share wins; changes within 1e-9 are ties, broken by "
    "competitor input order, then move order " + ", ".join(MOVES) + "."
)


class MoveNotApplicable(ValueError):
    pass


@dataclass
class Candidate:
    competitor_id: str
    move: str
    status: str  # ok | failed | invalid_input | not_applicable
    description: str = ""
    candidate_share: Optional[float] = None
    share_change: Optional[float] = None
    error: Optional[str] = None


@dataclass
class StrategistReport:
    status: str  # ok | no_competitors | baseline_failed | invalid_input
    engine_source: str
    seed: int
    baseline_share: Optional[float]
    candidates: List[Candidate] = field(default_factory=list)
    per_competitor_best: Dict[str, Optional[str]] = field(default_factory=dict)
    selected: Optional[dict] = None
    tie_break_rule: str = TIE_BREAK_RULE
    limitations: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _valid_number(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _validate_competitor(comp: dict, you: dict) -> Optional[str]:
    if not _valid_number(comp.get("price")) or comp["price"] < 0:
        return f"invalid price {comp.get('price')!r}"
    feats = comp.get("features")
    if not isinstance(feats, list) or not feats or not all(_valid_number(f) for f in feats):
        return "missing or invalid feature vector"
    if len(feats) != len(you.get("features") or []):
        return "feature vector length does not match our product"
    return None


def apply_move(move: str, competitor_id: str, agents: List[dict], options: List[dict]):
    """Return (agents, options, description) with the move applied to copies."""
    agents = copy.deepcopy(agents)
    options = copy.deepcopy(options)
    comp = next(o for o in options if o["id"] == competitor_id)
    you = next(o for o in options if o["id"] == YOU_ID)

    if move in PRICE_CUTS:
        if comp["price"] <= 0:
            raise MoveNotApplicable("price is already zero; a price cut is not possible")
        old = comp["price"]
        comp["price"] = round(old * (1 - PRICE_CUTS[move]), 6)
        return agents, options, f"price {old:g} -> {comp['price']:g}"

    if move == "add_feature":
        feats = comp["features"]
        if all(f >= 1.0 for f in feats):
            raise MoveNotApplicable("all attributes are already at the maximum")
        gaps = [y - c if c < 1.0 else -math.inf for y, c in zip(you["features"], feats)]
        best_gap = max(gaps)
        if best_gap > 0:
            k = gaps.index(best_gap)  # attribute where we lead most; lowest index on ties
        else:
            open_attrs = [(f, i) for i, f in enumerate(feats) if f < 1.0]
            k = min(open_attrs)[1]    # otherwise the rival's weakest attribute
        old = feats[k]
        feats[k] = round(min(1.0, old + FEATURE_STEP), 6)
        return agents, options, f"attribute {k}: {old:g} -> {feats[k]:g}"

    if move == "promo":
        for a in agents:
            brand = a.setdefault("brand", {})
            brand[competitor_id] = float(brand.get(competitor_id, 0.0)) + PROMO_BRAND_BOOST
        return agents, options, f"brand affinity +{PROMO_BRAND_BOOST:g} for all agents"

    raise ValueError(f"unknown move '{move}'")


def run_strategist(
    agents: List[dict], options: List[dict], adapter: EngineAdapter, seed: int
) -> StrategistReport:
    report = StrategistReport(status="ok", engine_source=adapter.source, seed=seed, baseline_share=None)
    you = next((o for o in options if o.get("id") == YOU_ID), None)
    if you is None:
        report.status = "invalid_input"
        report.limitations.append(f"no option with id '{YOU_ID}'; cannot measure our share")
        return report
    competitors = [o for o in options if o.get("role") == "competitor"]
    if not competitors:
        report.status = "no_competitors"
        report.limitations.append("no competitors in the scenario; competitor reaction not assessed")
        return report

    try:
        report.baseline_share = adapter.evaluate(agents, options, seed).share(YOU_ID)
    except Exception as exc:  # noqa: BLE001 - reported, never hidden
        report.status = "baseline_failed"
        report.limitations.append(f"baseline evaluation failed: {exc}")
        return report

    for comp in competitors:
        cid = comp["id"]
        problem = _validate_competitor(comp, you)
        for move in MOVES:
            if problem:
                report.candidates.append(Candidate(cid, move, "invalid_input", error=problem))
                continue
            try:
                a2, o2, desc = apply_move(move, cid, agents, options)
            except MoveNotApplicable as exc:
                report.candidates.append(Candidate(cid, move, "not_applicable", error=str(exc)))
                continue
            try:
                share = adapter.evaluate(a2, o2, seed).share(YOU_ID)
            except Exception as exc:  # noqa: BLE001
                report.candidates.append(Candidate(cid, move, "failed", desc, error=str(exc)))
                continue
            report.candidates.append(
                Candidate(cid, move, "ok", desc, candidate_share=share, share_change=share - report.baseline_share)
            )
        if problem:
            report.limitations.append(f"competitor '{cid}' skipped: {problem}")

    comp_order = {c["id"]: n for n, c in enumerate(competitors)}

    def key(c: Candidate):
        return (round(c.share_change / TIE_TOLERANCE) * TIE_TOLERANCE, comp_order[c.competitor_id], MOVES.index(c.move))

    ok = [c for c in report.candidates if c.status == "ok"]
    for comp in competitors:
        mine = sorted((c for c in ok if c.competitor_id == comp["id"]), key=key)
        report.per_competitor_best[comp["id"]] = mine[0].move if mine else None

    failed = [c for c in report.candidates if c.status == "failed"]
    if failed:
        report.limitations.append(f"{len(failed)} candidate evaluation(s) failed and were excluded")

    harmful = sorted((c for c in ok if c.share_change < -TIE_TOLERANCE), key=key)
    if harmful:
        best = harmful[0]
        report.selected = {
            "competitor_id": best.competitor_id,
            "move": best.move,
            "description": best.description,
            "baseline_share": report.baseline_share,
            "candidate_share": best.candidate_share,
            "share_change": best.share_change,
        }
    elif ok:
        report.limitations.append("no evaluated competitor move reduced our simulated share")
    else:
        report.limitations.append("no competitor move could be evaluated")
    return report
