"""Turn a verified evidence snapshot into bounded changes to the segment priors (Person A).

The model never sets a final number. Code reads verified findings and moves priors only inside fixed bands around the
pack's template, so a wrong or manipulated source can bend the population a little, never break it:

  * country economics     budget ranges x `economics.budget_scale` (already bounded 0.25 to 2.0; an assumption)
  * segment_budget        budget range replaced by the sourced figure; a figure that does not overlap 0.5x to 2x
                          of the template is judged not comparable and skipped (never clamped to the edge)
  * free_tool_adoption    the free tool's share of the incumbent mix moves toward the sourced share, by at most 0.25
  * trend notes           optional; budget +-10% or price sensitivity +-15%; total drift per segment bounded to +-20%
  * competitor_price      NOT applied here: option prices come from intake. Listed as advisory for the user.

Figures in a currency other than the pack's cannot be converted honestly, so they are skipped and listed.
Every change is recorded in plain words (`applied`) and the segment keeps the urls behind it (`sources`).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from backend.evidence.models import EvidenceSnapshot, Finding
from backend.population.models import PackSpec, SegmentSpec

BUDGET_BAND = (0.5, 2.0)
ADOPTION_MAX_MOVE = 0.25
DRIFT_BOUNDS = (0.8, 1.2)
TREND_BUDGET_STEP = 0.10
TREND_ALPHA_STEP = 0.15
FREE_TOOL = "free_tool"


@dataclass
class Applied:
    segments: list[SegmentSpec]
    applied: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    advisory: list[str] = field(default_factory=list)  # competitor prices found, for the user to review


def _targets(f_subject: str | None, segments: list[SegmentSpec]) -> list[SegmentSpec]:
    if f_subject is None or f_subject in ("all", "*"):
        return segments
    return [s for s in segments if s.id == f_subject]


def _range(f: Finding) -> tuple[float, float] | None:
    if f.low is not None and f.high is not None:
        return (f.low, f.high)
    if f.value is not None:
        return (round(f.value * 0.75, 2), round(f.value * 1.25, 2))
    return None


def _tag(s: SegmentSpec, url: str, quote: str, retrieved_at: str) -> None:
    """Mark the segment as evidence-adjusted and keep the verified quote (the contract's `Source`)."""
    s.evidence = "evidence"
    if not any(x["url"] == url and x["quote"] == quote for x in s.sources):
        s.sources.append({"url": url, "quote": quote, "retrieved_at": retrieved_at})


def apply_evidence(pack: PackSpec, snap: EvidenceSnapshot | None, *, use_trends: bool = True) -> Applied:
    segs = [s.model_copy(deep=True) for s in pack.segments]
    out = Applied(segments=segs)
    if snap is None or snap.status in ("off", "failed"):
        return out
    template = {s.id: s for s in pack.segments}
    budget_set: set[str] = set()  # segments whose budget came from a sourced figure (no economics scaling on top)

    for f in snap.findings:
        if f.kind == "competitor_price":
            out.advisory.append(f"{f.subject or 'a competitor'}: {f.claim} ({f.url})")
            continue
        if f.currency and f.currency.upper() != pack.currency.upper() and f.kind == "segment_budget":
            out.skipped.append(f"{f.claim}: figure is in {f.currency}, pack uses {pack.currency}; not converted")
            continue
        targets = _targets(f.subject, segs)
        if f.kind == "segment_budget":
            r = _range(f)
            if r is None or not targets:
                out.skipped.append(f"{f.claim}: no usable range or unknown segment '{f.subject}'")
                continue
            for s in targets:
                t = template[s.id].priors.budget
                lo = max(r[0], t[0] * BUDGET_BAND[0])
                hi = min(r[1], t[1] * BUDGET_BAND[1])
                if lo > hi:
                    # Far from the template (e.g. household tuition for a $7 app): almost certainly measuring a
                    # different thing, so it is not used. Clamping it to the band's edge would pass off a guess as data.
                    out.skipped.append(f"{s.name}: '{f.claim[:70]}' is outside {BUDGET_BAND[0]}x to {BUDGET_BAND[1]}x "
                                       "of the template budget, so it is probably not comparable; not used")
                    continue
                s.priors.budget = (round(lo, 2), round(hi, 2))
                budget_set.add(s.id)
                _tag(s, f.url, f.quote, snap.created_at)
                out.applied.append(f"{s.name}: budget {s.priors.budget[0]} to {s.priors.budget[1]} ({f.claim})")
        elif f.kind == "free_tool_adoption":
            if f.value is None or not targets:
                out.skipped.append(f"{f.claim}: no share or unknown segment '{f.subject}'")
                continue
            for s in targets:
                inc = s.priors.incumbent
                if FREE_TOOL not in inc:
                    continue
                total = sum(inc.values())
                old = inc[FREE_TOOL] / total
                new = min(max(f.value, old - ADOPTION_MAX_MOVE), old + ADOPTION_MAX_MOVE)
                rest = total - inc[FREE_TOOL]
                for k in inc:
                    inc[k] = new if k == FREE_TOOL else (inc[k] / rest * (1 - new) if rest > 0 else 0.0)
                _tag(s, f.url, f.quote, snap.created_at)
                out.applied.append(f"{s.name}: free-tool share {old:.2f} to {new:.2f} ({f.claim})")

    if snap.economics:
        e = snap.economics
        for s in segs:
            if s.id in budget_set or e.budget_scale == 1.0:
                continue
            lo, hi = s.priors.budget
            s.priors.budget = (round(lo * e.budget_scale, 2), round(hi * e.budget_scale, 2))
        if e.budget_scale != 1.0:
            out.applied.append(f"All segments without a sourced budget: x{e.budget_scale} "
                               f"(GDP per capita PPP in {e.country} vs {e.baseline_iso}; an assumption)")

    if use_trends:
        drift = {s.id: 1.0 for s in segs}
        for n in snap.trend_notes:
            step = {"budget_down": ("budget", 1 - TREND_BUDGET_STEP), "budget_up": ("budget", 1 + TREND_BUDGET_STEP),
                    "price_sensitivity_up": ("alpha", 1 + TREND_ALPHA_STEP),
                    "price_sensitivity_down": ("alpha", 1 - TREND_ALPHA_STEP)}.get(n.effect)
            if step is None:
                continue
            hit = [s for s in segs if n.segments is None or s.id in n.segments]
            if not hit:
                out.skipped.append(f"Trend '{n.note[:80]}': it names segments that do not exist ({n.segments})")
                continue
            for s in hit:
                kind, mult = step
                new_drift = min(max(drift[s.id] * mult, DRIFT_BOUNDS[0]), DRIFT_BOUNDS[1])
                mult = new_drift / drift[s.id]
                drift[s.id] = new_drift
                r = getattr(s.priors, kind)
                setattr(s.priors, kind, (round(r[0] * mult, 4), round(r[1] * mult, 4)))
                _tag(s, n.url, n.quote, snap.created_at)
            out.applied.append(f"Trend: {n.note} ({n.effect.replace('_', ' ')}, "
                               f"{'all segments' if n.segments is None else ', '.join(n.segments)})")
    return out
