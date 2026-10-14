"""Moderator: turns engine-grounded reports into a CouncilOutput.

Confidence rules (applied in order):

1. Base level from fragility: < 0.25 high, < 0.50 medium, otherwise low.
2. Capped at medium if any sensitivity test was skipped or failed, any
   competitor evaluation failed, or the run's p10-p90 spread exceeds half of
   its p50 share.
3. Capped at low if results come from the mock engine adapter.

Confidence describes how robust the *simulated* result is to its own
assumptions. It is not a statistical confidence level and not a forecast.

Every number in the verdict, segment lines and risks must be grounded in the
evidence set (see ``council.claims``). Experiment thresholds are proposals and
are labelled as such instead.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, List, Optional, Tuple

from backend.council.advocate import FACTORS, AdvocateReport
from backend.council.claims import Evidence, is_grounded, unsupported_numbers
from backend.council.engine_adapter import OUTSIDE_ID, YOU_ID
from backend.council.schemas import CompetitorReaction, CouncilOutput, Experiment, Risk, RunResult
from backend.council.strategist import PRICE_CUTS, StrategistReport
from backend.council.wording import TemplateWording, Wording

LEVELS = ("low", "medium", "high")
THRESHOLD_LABEL = "Proposed test threshold (not an established benchmark): "
WITHHELD = "Claim withheld: it cited a number that is not present in the simulation inputs."
MOVE_TEXT = {
    "price_cut_10": "a 10% price cut",
    "price_cut_20": "a 20% price cut",
    "add_feature": "adding a feature",
    "promo": "a promotion",
}


class _SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def _cap(level: str, cap: str) -> str:
    return LEVELS[min(LEVELS.index(level), LEVELS.index(cap))]


def decide_confidence(
    fragility: float, engine_source: str, advocate: AdvocateReport, strategist: StrategistReport,
    totals_you: Optional[dict],
) -> Tuple[str, List[str]]:
    reasons: List[str] = []
    level = "high" if fragility < 0.25 else "medium" if fragility < 0.5 else "low"
    tested = {p.parameter for p in advocate.perturbations if p.status == "ok"}
    if advocate.status != "ok" or len(tested) < 3 or any(p.status != "ok" for p in advocate.perturbations):
        level = _cap(level, "medium")
        reasons.append("Confidence capped at medium: not every sensitivity test could be run.")
    failed_moves = any(c.status == "failed" for c in strategist.candidates)
    if failed_moves or strategist.status in ("baseline_failed", "invalid_input"):
        level = _cap(level, "medium")
        reasons.append("Confidence capped at medium: some competitor moves could not be evaluated.")
    if totals_you and all(totals_you.get(k) is not None for k in ("p10", "p50", "p90")) and totals_you["p50"] > 0:
        if (totals_you["p90"] - totals_you["p10"]) / totals_you["p50"] > 0.5:
            level = _cap(level, "medium")
            reasons.append("Confidence capped at medium: the run's p10-p90 share range is wide.")
    if engine_source == "mock":
        level = _cap(level, "low")
        reasons.append("Confidence capped at low: results come from the mock engine adapter, not the real engine.")
    return level, reasons


def _segment_stats(rr: RunResult) -> Dict[str, dict]:
    stats: Dict[str, dict] = defaultdict(lambda: {"n": 0, "n_you": 0, "alts": Counter(), "gaps": []})
    for c in rr.choices:
        if not c.segment:
            continue
        s = stats[c.segment]
        s["n"] += 1
        if c.choice == YOU_ID:
            s["n_you"] += 1
        else:
            s["alts"][c.choice] += 1
            if c.runner_up == YOU_ID and c.gap is not None:
                s["gaps"].append(abs(c.gap))
    for s in stats.values():
        s["share"] = s["n_you"] / s["n"] if s["n"] else 0.0
        s["mean_gap"] = sum(s["gaps"]) / len(s["gaps"]) if s["gaps"] else None
    return dict(stats)


def build_evidence(
    rr: RunResult,
    strategist: StrategistReport,
    advocate: AdvocateReport,
    seg_stats: Dict[str, dict],
) -> Evidence:
    ev = Evidence()
    for t in rr.totals.values():
        ev.extend([t.share, t.p10, t.p50, t.p90], as_percent=True)
        ev.add(t.count)
    for s in seg_stats.values():
        ev.extend([s["n"], s["n_you"], len(s["gaps"])])
        ev.add(s["share"], as_percent=True)
        ev.add(s["mean_gap"])
    ev.extend([strategist.baseline_share], as_percent=True)
    for c in strategist.candidates:
        ev.extend([c.candidate_share, c.share_change], as_percent=True)
        if c.share_change is not None and strategist.baseline_share:
            ev.add(c.share_change / strategist.baseline_share, as_percent=True)
    ev.extend([round(v * 100) for v in PRICE_CUTS.values()])
    ev.extend([advocate.baseline_share, advocate.fragility], as_percent=True)
    for p in advocate.perturbations:
        ev.extend([p.perturbed_share, p.abs_change, p.rel_change], as_percent=True)
    ev.extend([round(abs(f - 1) * 100) for f in FACTORS])
    return ev


def _metric(before: float, after: float) -> str:
    change = after - before
    rel = f", {change / before:+.1%}" if before > 0 else ""
    return f"share {before:.3f} -> {after:.3f} ({change:+.3f}{rel})"


def _ranked_risks(
    strategist: StrategistReport,
    advocate: AdvocateReport,
    labels: Dict[str, str],
) -> List[Tuple[str, float, Risk]]:
    items: List[Tuple[str, float, Risk]] = []
    for r in advocate.risks:
        items.append((r["key"], r["abs_change"], Risk(
            title=r["title"],
            evidence=f"Devil's Advocate: if {r['assumption']}, the simulated share changes as shown.",
            metric=_metric(r["baseline_share"], r["perturbed_share"]),
        )))
    sel = strategist.selected
    if sel:
        name = labels.get(sel["competitor_id"], sel["competitor_id"])
        items.append(("competitor", sel["share_change"], Risk(
            title=f"{name} responds with {MOVE_TEXT.get(sel['move'], sel['move'])}",
            evidence="Competitor Strategist: the rival's best one-step response among the bounded moves.",
            metric=_metric(sel["baseline_share"], sel["candidate_share"]),
        )))
    items.sort(key=lambda x: x[1])
    return items[:3]


def _segment_lines(seg_stats: Dict[str, dict], seg_names: Dict[str, str], labels: Dict[str, str],
                   overall: float, product: str) -> Tuple[List[str], List[str]]:
    buys, rejects = [], []
    for sid, s in sorted(seg_stats.items(), key=lambda kv: (-kv[1]["share"], kv[0])):
        name = seg_names.get(sid, sid)
        base = f"{name}: {s['n_you']} of {s['n']} simulated agents chose {product} ({s['share']:.2f})"
        if s["n_you"] > 0 and s["share"] >= overall:
            buys.append(base)
        else:
            line = base
            if s["alts"]:
                alt, _ = sorted(s["alts"].items(), key=lambda kv: (-kv[1], kv[0]))[0]
                line += f"; most chose {labels.get(alt, alt)}"
            if s["mean_gap"] is not None:
                line += f"; {len(s['gaps'])} had {product} as runner-up (mean utility gap {s['mean_gap']:.2f})"
            rejects.append(line)
    return buys, rejects


def _experiments(risk_keys: List[str], library: dict, context: dict) -> List[Experiment]:
    picked, seen = [], set()
    candidates = [library[k] for k in risk_keys if k in library] + list(library.get("defaults", []))
    ctx = _SafeDict(context)
    for spec in candidates:
        if spec["title"] in seen:
            continue
        seen.add(spec["title"])
        threshold = spec["pass_threshold"].format_map(ctx)
        if not threshold.startswith(THRESHOLD_LABEL):
            threshold = THRESHOLD_LABEL + threshold
        picked.append(Experiment(
            title=spec["title"].format_map(ctx), hypothesis=spec["hypothesis"].format_map(ctx),
            pass_threshold=threshold, kind=spec["kind"],
        ))
        if len(picked) == 3:
            break
    return picked


def enforce_grounding(output: CouncilOutput, evidence: Evidence) -> CouncilOutput:
    """Replace any claim that cites a number missing from the evidence."""
    data = output.model_dump()
    removed: List[str] = []
    if not is_grounded(data["verdict"], evidence):
        removed += unsupported_numbers(data["verdict"], evidence)
        data["verdict"] = "Simulated outcome only. " + WITHHELD
    for key in ("who_buys", "who_rejects"):
        for i, line in enumerate(data[key]):
            if not is_grounded(line, evidence):
                removed += unsupported_numbers(line, evidence)
                data[key][i] = WITHHELD
    for risk in data["risks"]:
        for f in ("title", "evidence", "metric"):
            if not is_grounded(risk[f], evidence):
                removed += unsupported_numbers(risk[f], evidence)
                risk[f] = WITHHELD
    if removed:
        data["limitations"].append(f"Removed unsupported numbers: {sorted(set(removed))}")
    return CouncilOutput(**data)


def build_council(
    run_result, strategist: StrategistReport, advocate: AdvocateReport, *,
    population: Optional[dict] = None, options: Optional[List[dict]] = None,
    experiment_library: dict, context: Optional[dict] = None, wording: Optional[Wording] = None,
) -> CouncilOutput:
    rr = run_result if isinstance(run_result, RunResult) else RunResult(**run_result)
    wording = wording or TemplateWording()
    labels = {o["id"]: o.get("label", o["id"]) for o in (options or [])}
    labels.setdefault(OUTSIDE_ID, "the outside option")
    product = labels.get(YOU_ID, "your product")
    seg_names = {s["id"]: s.get("name", s["id"]) for s in (population or {}).get("segments", [])}
    limitations: List[str] = []

    totals_you = rr.totals[YOU_ID].model_dump() if YOU_ID in rr.totals else None
    if totals_you is None:
        limitations.append(f"RunResult has no totals for '{YOU_ID}'; headline share unavailable.")

    seg_stats = _segment_stats(rr)
    evidence = build_evidence(rr, strategist, advocate, seg_stats)
    overall = sum(s["n_you"] for s in seg_stats.values()) / max(1, sum(s["n"] for s in seg_stats.values()))
    buys, rejects = _segment_lines(seg_stats, seg_names, labels, overall, product)
    if not seg_stats:
        limitations.append("RunResult has no segment-level choices; buyer and rejector segments omitted.")

    engine_source = advocate.engine_source
    confidence, reasons = decide_confidence(advocate.fragility, engine_source, advocate, strategist, totals_you)
    ranked = _ranked_risks(strategist, advocate, labels)

    if totals_you:
        p50 = totals_you["p50"] if totals_you.get("p50") is not None else totals_you["share"]
        draft = f"Simulated outcome under stated assumptions: {product} takes a median share of {p50:.2f}"
        if totals_you.get("p10") is not None and totals_you.get("p90") is not None:
            draft += f" (p10 {totals_you['p10']:.2f}, p90 {totals_you['p90']:.2f})"
        draft += "."
    else:
        draft = "Simulated outcome under stated assumptions: the headline share is unavailable."
    if ranked:
        draft += f" Biggest threat: {ranked[0][2].title} ({ranked[0][2].metric})."
    else:
        draft += " No tested assumption or competitor move reduced the simulated share by a meaningful amount."
    draft += f" Fragility {advocate.fragility:.2f}, confidence {confidence}."

    verdict = draft
    if wording.name != "template":
        facts = {"product": product, "totals_you": totals_you, "fragility": advocate.fragility,
                 "confidence": confidence, "top_risks": [r.model_dump() for _, _, r in ranked]}
        try:
            candidate = wording.rewrite_verdict(draft, facts)
        except Exception as exc:  # noqa: BLE001
            candidate, limitations = "", limitations + [f"LLM wording failed ({exc}); template used."]
        bad = unsupported_numbers(candidate, evidence)
        if candidate and not bad and "simulat" in candidate.lower():
            verdict = candidate
        elif candidate:
            limitations.append(
                "LLM wording rejected "
                f"(unsupported numbers {bad} or missing 'simulated' label); template used."
            )

    reaction = None
    if strategist.selected:
        sel = strategist.selected
        reaction = CompetitorReaction(
            competitor_id=sel["competitor_id"],
            move=sel["move"],
            effect_on_share=round(sel["share_change"], 4),
        )

    ctx = dict(context or {})
    ctx.setdefault("product", product)
    if strategist.selected:
        cid = strategist.selected["competitor_id"]
        ctx.setdefault("competitor", labels.get(cid, cid))
    experiments = _experiments([k for k, _, _ in ranked], experiment_library, ctx)

    out = CouncilOutput(
        run_id=rr.run_id, verdict=verdict, confidence=confidence, fragility=advocate.fragility,
        who_buys=buys, who_rejects=rejects, risks=[r for _, _, r in ranked],
        competitor_reaction=reaction, experiments=experiments,
        limitations=limitations + reasons + strategist.limitations + advocate.limitations
        + ["Simulated outcome under stated assumptions; not a forecast of real sales."],
        engine_source=engine_source,
    )
    return enforce_grounding(out, evidence)
