"""Devil's Advocate: deterministic sensitivity analysis over population priors.

Each perturbation scales exactly one agent parameter by -20% and +20% and
re-evaluates the scenario through the engine adapter:

* ``budget``  - willingness to pay (hard affordability limit)
* ``alpha``   - price sensitivity
* ``brand``   - competitor brand strength (every brand affinity except ours)

Fragility score (0 = robust, 1 = fragile)::

    A = min(1, max_i |s_i - s_0| / max(s_0, SHARE_FLOOR))
    W = fraction of evaluated perturbations where the leading option changes
    fragility = clip(0.7 * A + 0.3 * W, 0, 1)

``s_0`` is our baseline share and ``s_i`` our share under perturbation ``i``.
``SHARE_FLOOR`` stops tiny baselines from making every result look fragile.
If nothing could be evaluated, fragility is 1.0 (unknown is treated as fragile).

Limitations: the score measures how much the *simulated* result depends on
assumed priors within a fixed +/-20% band. It is not a calibrated confidence
interval, does not cover joint perturbations or structural model error, and
says nothing about real customer behaviour.
"""
from __future__ import annotations

import copy
import math
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional

from council.engine_adapter import OUTSIDE_ID, YOU_ID, EngineAdapter

FACTORS = (0.8, 1.2)
SHARE_FLOOR = 0.05
MIN_RISK_DROP = 0.005  # drops smaller than this are not reported as risks
WEIGHT_MAGNITUDE = 0.7
WEIGHT_LEADER = 0.3

PARAMETERS = {
    "budget": "willingness to pay (budget)",
    "alpha": "price sensitivity",
    "brand": "competitor brand strength",
}
RISK_TITLES = {
    ("budget", 0.8): "Willingness to pay is lower than assumed",
    ("budget", 1.2): "Higher budgets favour premium rivals",
    ("alpha", 0.8): "Customers are less price-driven than assumed",
    ("alpha", 1.2): "Customers are more price-sensitive than assumed",
    ("brand", 0.8): "Rival brands are weaker than assumed",
    ("brand", 1.2): "Rival brands are stronger than assumed",
}
FORMULA = (
    "fragility = clip(0.7 * min(1, max|share change| / max(baseline share, 0.05)) "
    "+ 0.3 * share of perturbations that change the leading option, 0, 1)"
)


@dataclass
class Perturbation:
    parameter: str
    factor: float
    direction: str
    assumption: str
    status: str  # ok | failed
    baseline_share: Optional[float] = None
    perturbed_share: Optional[float] = None
    abs_change: Optional[float] = None
    rel_change: Optional[float] = None
    baseline_leader: Optional[str] = None
    perturbed_leader: Optional[str] = None
    leader_changed: Optional[bool] = None
    error: Optional[str] = None


@dataclass
class AdvocateReport:
    status: str  # ok | baseline_failed | no_perturbations
    engine_source: str
    seed: int
    baseline_share: Optional[float]
    baseline_leader: Optional[str]
    perturbations: List[Perturbation] = field(default_factory=list)
    risks: List[dict] = field(default_factory=list)
    fragility: float = 1.0
    fragility_formula: str = FORMULA
    limitations: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _leader(shares: Dict[str, float], order: List[str]) -> str:
    return max(order, key=lambda i: (shares.get(i, -1.0), -order.index(i)))


def check_availability(parameter: str, agents: List[dict]) -> Optional[str]:
    """Return a limitation message if the parameter cannot be perturbed."""
    if not agents:
        return "population has no agents"
    if parameter in ("budget", "alpha"):
        bad = [a.get("id") for a in agents if not _num(a.get(parameter))]
        if bad:
            return f"{len(bad)} agent(s) have no numeric '{parameter}' prior"
        return None
    if parameter == "brand":
        values = [
            v for a in agents if isinstance(a.get("brand"), dict)
            for k, v in a["brand"].items() if k != YOU_ID and _num(v)
        ]
        if not values or all(v == 0 for v in values):
            return "no non-zero competitor brand priors; scaling would have no effect"
        return None
    return f"unknown parameter '{parameter}'"


def perturb(agents: List[dict], parameter: str, factor: float) -> List[dict]:
    out = copy.deepcopy(agents)
    for a in out:
        if parameter in ("budget", "alpha"):
            a[parameter] = a[parameter] * factor
        elif parameter == "brand":
            a["brand"] = {k: (v * factor if k != YOU_ID else v) for k, v in (a.get("brand") or {}).items()}
    return out


def _assumption(parameter: str, factor: float) -> str:
    pct = round((factor - 1) * 100)
    return f"{PARAMETERS[parameter]} is {abs(pct)}% {'lower' if pct < 0 else 'higher'} than assumed"


def fragility_score(baseline: float, perturbations: List[Perturbation]) -> float:
    ok = [p for p in perturbations if p.status == "ok"]
    if not ok:
        return 1.0
    magnitude = min(1.0, max(abs(p.abs_change) for p in ok) / max(baseline, SHARE_FLOOR))
    leader = sum(1 for p in ok if p.leader_changed) / len(ok)
    return round(min(1.0, max(0.0, WEIGHT_MAGNITUDE * magnitude + WEIGHT_LEADER * leader)), 4)


def run_advocate(agents: List[dict], options: List[dict], adapter: EngineAdapter, seed: int) -> AdvocateReport:
    order = [o["id"] for o in options if o.get("role") != OUTSIDE_ID] + [OUTSIDE_ID]
    report = AdvocateReport(status="ok", engine_source=adapter.source, seed=seed, baseline_share=None, baseline_leader=None)
    try:
        base = adapter.evaluate(agents, options, seed)
        s0 = base.share(YOU_ID)
    except Exception as exc:  # noqa: BLE001 - reported, never hidden
        report.status = "baseline_failed"
        report.limitations.append(f"baseline evaluation failed: {exc}")
        return report
    report.baseline_share = s0
    report.baseline_leader = _leader(base.shares, order)

    for parameter in PARAMETERS:
        problem = check_availability(parameter, agents)
        if problem:
            report.limitations.append(f"{PARAMETERS[parameter]} not tested: {problem}")
            continue
        for factor in FACTORS:
            p = Perturbation(
                parameter=parameter, factor=factor, direction=f"{round((factor - 1) * 100):+d}%",
                assumption=_assumption(parameter, factor), status="ok",
                baseline_share=s0, baseline_leader=report.baseline_leader,
            )
            try:
                ev = adapter.evaluate(perturb(agents, parameter, factor), options, seed)
                s = ev.share(YOU_ID)
            except Exception as exc:  # noqa: BLE001
                p.status, p.error = "failed", str(exc)
                report.perturbations.append(p)
                continue
            p.perturbed_share = s
            p.abs_change = s - s0
            p.rel_change = (s - s0) / s0 if s0 > 0 else None
            p.perturbed_leader = _leader(ev.shares, order)
            p.leader_changed = p.perturbed_leader != report.baseline_leader
            report.perturbations.append(p)

    failed = [p for p in report.perturbations if p.status == "failed"]
    if failed:
        report.limitations.append(f"{len(failed)} perturbation(s) failed and were excluded")
    ok = [p for p in report.perturbations if p.status == "ok"]
    if not ok:
        report.status = "no_perturbations"
        report.limitations.append("no perturbation could be evaluated; fragility set to 1.0 (unknown)")
    report.fragility = fragility_score(s0, report.perturbations)

    # Worst direction per parameter, then rank by size of the drop.
    worst: Dict[str, Perturbation] = {}
    for p in ok:
        if p.abs_change < -MIN_RISK_DROP and (p.parameter not in worst or p.abs_change < worst[p.parameter].abs_change):
            worst[p.parameter] = p
    ranked = sorted(worst.values(), key=lambda p: (p.abs_change, list(PARAMETERS).index(p.parameter)))
    for p in ranked[:3]:
        report.risks.append({
            "key": p.parameter,
            "title": RISK_TITLES[(p.parameter, p.factor)],
            "assumption": p.assumption,
            "baseline_share": p.baseline_share,
            "perturbed_share": p.perturbed_share,
            "abs_change": p.abs_change,
            "rel_change": p.rel_change,
        })
    return report
