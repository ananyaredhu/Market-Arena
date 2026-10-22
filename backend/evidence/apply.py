"""Turn evidence into changes to the segment priors (Person A).

Only REAL DATASETS may move a prior, and the measured change is applied in full: nothing is capped or skipped.
Surveys, news and blog statistics found on web pages never move a prior: they are kept as reference in the Resources
library (resources.py) for the user and the Council to read and cite, not fed to the model. Anything without a real
dataset behind it stays the pack's synthetic assumption.

Today the datasets are:

  * country economics     budget ranges x `economics.budget_scale` (World Bank GDP per person, PPP; the scale is
                          bounded 0.25 to 2.0; an assumption that spending scales with income, said so in the log)
  * consumer prices       budget ranges x (all-items CPI in the latest year / CPI in the starting year), the full
                          reported change (SingStat, Singapore). The starting year is the year the pack's budgets are
                          in; that is an assumption the user can edit (`price_base_year`, default 2024), said so in
                          the log. A starting year outside the published series changes nothing and says why.

Every change is recorded in plain words (`applied`) and the segment keeps the url behind it (`sources`).
New datasets plug in here, each labelled.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from backend.evidence.models import EvidenceSnapshot
from backend.population.models import PackSpec, SegmentSpec


@dataclass
class Applied:
    segments: list[SegmentSpec]
    applied: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def _tag(s: SegmentSpec, url: str, label: str, retrieved_at: str) -> None:
    """Mark the segment as evidence-adjusted and keep where the number came from (the contract's `Source`)."""
    s.evidence = "evidence"
    if not any(x["url"] == url and x["quote"] == label for x in s.sources):
        s.sources.append({"url": url, "quote": label, "retrieved_at": retrieved_at})


def _scale_budgets(segs: list[SegmentSpec], scale: float, url: str, label: str, retrieved_at: str) -> None:
    for s in segs:
        lo, hi = s.priors.budget
        s.priors.budget = (round(lo * scale, 2), round(hi * scale, 2))
        _tag(s, url, label, retrieved_at)


def apply_evidence(pack: PackSpec, snap: EvidenceSnapshot | None, price_base_year: int | None = None) -> Applied:
    segs = [s.model_copy(deep=True) for s in pack.segments]
    out = Applied(segments=segs)
    if snap is None:
        return out

    # Datasets are fetched before any search or model call, so they apply whatever happened to the web research.
    e = snap.economics
    if e is not None and e.budget_scale != 1.0:
        _scale_budgets(segs, e.budget_scale, e.source_url, (
            f"GDP per capita (PPP) {e.gdp_pc_ppp:,.0f} in {e.country} ({e.year}) vs "
            f"{e.baseline_gdp_pc_ppp:,.0f} in {e.baseline_iso}"), snap.created_at)
        out.applied.append(f"All segments: budget x{e.budget_scale} "
                           f"(GDP per capita PPP in {e.country} vs {e.baseline_iso}; an assumption that spending "
                           "scales with income)")

    pi = snap.price_index
    if pi is not None and price_base_year is not None:
        first, latest = min(pi.values, key=int), max(pi.values, key=int)
        base = str(price_base_year)
        if int(base) > int(latest):
            out.skipped.append(f"Consumer prices: the latest year published is {latest}, before the starting year "
                               f"{base}, so budgets were not moved for price changes")
        elif base not in pi.values:
            out.skipped.append(f"Consumer prices: {pi.name} has no {base} value (it covers {first} to {latest}), "
                               "so budgets were not moved for price changes")
        elif base != latest:
            scale = pi.values[latest] / pi.values[base]
            _scale_budgets(segs, scale, pi.url, (
                f"{pi.name}: {pi.values[base]} in {base}, {pi.values[latest]} in {latest}"), snap.created_at)
            out.applied.append(
                f"All segments: budget x{scale:.3f} (consumer prices {(scale - 1) * 100:+.1f}% from {base} to "
                f"{latest}, SingStat all-items CPI; assumes the pack's budgets are in {base} prices)")
    return out
