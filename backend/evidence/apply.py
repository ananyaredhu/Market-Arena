"""Turn evidence into bounded changes to the segment priors (Person A).

Only REAL DATASETS may move a prior. Surveys, news and blog statistics found on web pages never do: they are kept as
reference in the Resources library (resources.py) for the user and the Council to read and cite, not fed to the model.
Anything without a real dataset behind it stays the pack's synthetic assumption.

Today the one dataset is country economics (World Bank GDP per person, PPP):

  * country economics     budget ranges x `economics.budget_scale` (already bounded 0.25 to 2.0; an assumption
                          that spending scales with income, said so in the change log)

Every change is recorded in plain words (`applied`) and the segment keeps the url behind it (`sources`).
New datasets plug in here, each with its own bound and label.
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


def apply_evidence(pack: PackSpec, snap: EvidenceSnapshot | None) -> Applied:
    segs = [s.model_copy(deep=True) for s in pack.segments]
    out = Applied(segments=segs)
    if snap is None or snap.status in ("off", "failed"):
        return out

    e = snap.economics
    if e is not None and e.budget_scale != 1.0:
        label = (f"GDP per capita (PPP) {e.gdp_pc_ppp:,.0f} in {e.country} ({e.year}) vs "
                 f"{e.baseline_gdp_pc_ppp:,.0f} in {e.baseline_iso}")
        for s in segs:
            lo, hi = s.priors.budget
            s.priors.budget = (round(lo * e.budget_scale, 2), round(hi * e.budget_scale, 2))
            _tag(s, e.source_url, label, snap.created_at)
        out.applied.append(f"All segments: budget x{e.budget_scale} "
                           f"(GDP per capita PPP in {e.country} vs {e.baseline_iso}; an assumption that spending "
                           "scales with income)")
    return out
