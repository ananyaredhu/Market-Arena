"""Entry points that compose Strategist, Advocate, Moderator and Kit."""
from __future__ import annotations

from typing import List, Optional

from backend.council.advocate import run_advocate
from backend.council.engine_adapter import YOU_ID, EngineAdapter, evaluation_from_result, get_default_adapter
from backend.council.moderator import _segment_stats, build_council
from backend.council.schemas import CouncilOutput, KitOutput, RunResult
from backend.council.strategist import run_strategist
from backend.council.wording import Wording, wording_from_env
from backend.kit.generator import ALT_PRICE_FACTOR, generate_kit, money
from backend.kit.packs import kit_content, load_pack, outside_label


def _product(options: List[dict]) -> dict:
    you = next((o for o in options if o.get("id") == YOU_ID), None)
    return you or {"id": YOU_ID, "label": "your product", "price": 0.0}


def competitor_label(council: CouncilOutput, options: List[dict]) -> Optional[str]:
    if not council.competitor_reaction:
        return None
    cid = council.competitor_reaction.competitor_id
    return next((o.get("label", cid) for o in options if o.get("id") == cid), cid)


def _measured(rr: RunResult, strategist, advocate, population: dict) -> dict:
    """Numeric block kept separate from verdict prose. Values come from the run and the reports."""
    you = rr.totals.get(YOU_ID)
    stats = _segment_stats(rr)
    names = {s["id"]: s.get("name", s["id"]) for s in population.get("segments", [])}
    overall_n = sum(s["n"] for s in stats.values()) or 1
    overall = sum(s["n_you"] for s in stats.values()) / overall_n
    segments = []
    for sid, s in sorted(stats.items(), key=lambda kv: (-kv[1]["share"], kv[0])):
        relationship = "buys" if s["n_you"] > 0 and s["share"] >= overall else "rejects"
        segments.append({
            "id": sid,
            "name": names.get(sid, sid),
            "n": s["n"],
            "n_you": s["n_you"],
            "share": s["share"],
            "relationship": relationship,
        })
    risks = [
        {
            "title": r["title"],
            "baseline_share": r["baseline_share"],
            "perturbed_share": r["perturbed_share"],
            "abs_change": r["abs_change"],
        }
        for r in advocate.risks
    ]
    competitor = None
    if strategist.selected:
        sel = strategist.selected
        competitor = {
            "competitor_id": sel["competitor_id"],
            "move": sel["move"],
            "description": sel["description"],
            "baseline_share": sel["baseline_share"],
            "candidate_share": sel["candidate_share"],
            "share_change": sel["share_change"],
        }
    return {
        "baseline_share": you.share if you else None,
        "median_share": you.p50 if you else None,
        "p10": you.p10 if you else None,
        "p90": you.p90 if you else None,
        "fragility": advocate.fragility,
        "segments": segments,
        "risks": risks,
        "competitor": competitor,
    }


def run_council(
    run_result, population: dict, options: List[dict], pack: str, *,
    adapter: Optional[EngineAdapter] = None, wording: Optional[Wording] = None, seed: Optional[int] = None,
    trend_notes: Optional[List[dict]] = None, research_notes: Optional[List[dict]] = None,
) -> dict:
    rr = run_result if isinstance(run_result, RunResult) else RunResult(**run_result)
    adapter = adapter or get_default_adapter()
    seed = rr.seed if seed is None else seed
    agents = population.get("agents", [])
    # Reuse the supplied engine result as the baseline only when perturbations use that same engine.
    baseline = None
    if adapter.source == "engine" and YOU_ID in rr.totals:
        baseline = evaluation_from_result(rr, source=adapter.source)
    strategist = run_strategist(agents, options, adapter, seed, baseline=baseline)
    advocate = run_advocate(agents, options, adapter, seed, baseline=baseline)

    product = _product(options)
    context = {"outside": outside_label(pack)}
    price = product.get("price")
    if isinstance(price, (int, float)) and price >= 0:
        currency = load_pack(pack).get("currency", "S$")
        context.update(price=money(currency, price), price_low=money(currency, round(price * ALT_PRICE_FACTOR, 2)))

    council = build_council(
        rr, strategist, advocate, population=population, options=options,
        experiment_library=kit_content(pack)["experiment_library"], context=context,
        wording=wording if wording is not None else wording_from_env(),
        trend_notes=trend_notes, research_notes=research_notes,
    )
    return {
        "council": council,
        "strategist": strategist.to_dict(),
        "advocate": advocate.to_dict(),
        "measured": _measured(rr, strategist, advocate, population),
    }


def run_kit(council: CouncilOutput, pack: str, options: List[dict]) -> KitOutput:
    return generate_kit(council, pack, _product(options), competitor_label(council, options))
