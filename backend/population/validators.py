"""Guards against optimistic, homogeneous or malformed populations (Person A).

`validate_population(population, pack)` returns a list of `Issue`s; an empty list means the population passed.
The `pack` is the TEMPLATE the population is judged against (Master Plan 4.5: "guard against LLM optimism").

Checks (codes):
  shares          segment shares sum to 1 and agent counts match them
  structure       every agent has the right shape (weights per attribute, tau > 0, budget >= 0)
  diversity       parameters actually vary inside each segment (not copies of one customer)
  wtp_bound       average and maximum budget stay near what the template allows
  hostile         at least one hostile segment (flagged, or switching cost >= 0.5 on average)
  outside_share   enough non-buyers: measured by running the engine on the pack's own demo options
"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import mean

from backend.engine.engine import run_scenario
from backend.population.models import PackSpec

MIN_SPREAD = 0.10  # (max - min) / mean of budget and alpha within a segment
OUTSIDE_REPEATS = 20  # engine repeats used to estimate the expected outside-option share
MIN_AGENTS_FOR_DIVERSITY = 8
MIN_HOSTILE_SHARE = 0.10
HOSTILE_SWITCH = 0.5
WTP_AVG_FACTOR = 1.5  # average budget may be at most this multiple of the template's own average
WTP_MAX_FACTOR = 3.0  # no single budget above this multiple of the template's highest range top


@dataclass(frozen=True)
class Issue:
    code: str
    message: str

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


def template_avg_budget(pack: PackSpec) -> float:
    return sum(s.share * (s.priors.budget[0] + s.priors.budget[1]) / 2 for s in pack.segments)


def _hostile_ids(population: dict, by_seg: dict[str, list[dict]]) -> list[str]:
    flagged = {s["id"] for s in population.get("segments", []) if s.get("hostile")}
    heavy = {sid for sid, ag in by_seg.items() if ag and mean(a["switch"] for a in ag) >= HOSTILE_SWITCH}
    return sorted(flagged | heavy)


def _engine_options(pack: PackSpec) -> list[dict]:
    options = [dict(pack.demo_product)] if pack.demo_product else []
    options += [dict(c) for c in pack.competitors]
    options.append({"id": pack.outside_id, "label": "Do nothing", "role": "outside"})
    return options


def validate_population(population: dict, pack: PackSpec, *, options: list[dict] | None = None) -> list[Issue]:
    issues: list[Issue] = []
    agents: list[dict] = population.get("agents", [])
    segments: list[dict] = population.get("segments", [])
    n = len(agents)
    if n == 0:
        return [Issue("structure", "population has no agents")]

    # ---- structure
    n_attr = len(population.get("attributes", pack.attributes))
    bad = [a["id"] for a in agents if len(a["w"]) != n_attr or a["tau"] <= 0 or a["budget"] < 0]
    if bad:
        msg = f"{len(bad)} agent(s) malformed (weights length, tau <= 0 or budget < 0), e.g. {bad[:3]}"
        issues.append(Issue("structure", msg))

    # ---- shares
    total = sum(s["share"] for s in segments)
    if abs(total - 1.0) > 0.01:
        issues.append(Issue("shares", f"segment shares sum to {total:.3f}, expected 1.0"))
    by_seg: dict[str, list[dict]] = {}
    for a in agents:
        by_seg.setdefault(a["segment"], []).append(a)
    tol = max(0.02, 1.5 / n)
    for s in segments:
        got = len(by_seg.get(s["id"], [])) / n
        if abs(got - s["share"]) > tol:
            issues.append(Issue("shares", f"segment '{s['id']}' has {got:.1%} of agents but share {s['share']:.1%}"))

    # ---- diversity: catches clones and zero-width ranges. It uses the observed spread (max - min) relative
    # to the mean, not the standard deviation, so a legitimately narrow range (e.g. alpha 0.25 to 0.30)
    # is not flagged by sampling noise.
    for sid, ag in by_seg.items():
        if len(ag) < MIN_AGENTS_FOR_DIVERSITY:
            continue
        for key in ("budget", "alpha"):
            vals = [a[key] for a in ag]
            m = mean(vals)
            spread = (max(vals) - min(vals)) / m if m > 0 else 0.0
            if spread < MIN_SPREAD:
                msg = f"segment '{sid}': {key} barely varies (spread {spread:.3f} < {MIN_SPREAD})"
                issues.append(Issue("diversity", msg))

    # ---- willingness to pay
    cap = pack.max_avg_budget or WTP_AVG_FACTOR * template_avg_budget(pack)
    avg = mean(a["budget"] for a in agents)
    if avg > cap:
        issues.append(Issue("wtp_bound", f"average budget {avg:.2f} exceeds the plausible bound {cap:.2f}"))
    top = WTP_MAX_FACTOR * max(s.priors.budget[1] for s in pack.segments)
    over = [a["id"] for a in agents if a["budget"] > top]
    if over:
        issues.append(Issue("wtp_bound", f"{len(over)} agent(s) have a budget above {top:.2f}, e.g. {over[:3]}"))

    # ---- hostile segment
    hostile = _hostile_ids(population, by_seg)
    hostile_share = sum(len(by_seg[h]) for h in hostile) / n
    if hostile_share < MIN_HOSTILE_SHARE:
        msg = f"hostile segments hold {hostile_share:.1%} of agents, need at least {MIN_HOSTILE_SHARE:.0%}"
        issues.append(Issue("hostile", msg))

    # ---- outside option share (engine-measured); skipped if structure is already broken.
    # Uses the median over repeats, not one draw: with few agents a single draw is mostly dice-roll noise.
    if not bad:
        result = run_scenario(agents, options or _engine_options(pack), seed=0, repeats=OUTSIDE_REPEATS)
        outside = result["totals"].get(pack.outside_id, {}).get("p50", 0.0)
        if outside < pack.min_outside_share:
            issues.append(
                Issue(
                    "outside_share",
                    f"only {outside:.1%} pick the outside option, need at least {pack.min_outside_share:.0%}",
                )
            )

    return issues
