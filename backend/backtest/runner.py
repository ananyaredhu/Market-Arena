"""Turn a backtest case into a prediction by running the simulator (Person A).

Protocol (what makes the backtest honest):
  * One frozen set of priors for every case: the pack's template priors. Nothing is tuned per case.
  * No LLM is involved: populations come from `template_population`, so a result cannot depend on a model's mood.
  * The prediction rule is fixed in code, not chosen after seeing the outcome.
  * Several independent populations (seeds) are run; the prediction is the majority and the agreement is reported.
"""
from __future__ import annotations

import copy
import hashlib
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean, pstdev

from backend.backtest.case import Case
from backend.engine.engine import run_scenario
from backend.population.generator import template_population
from backend.population.models import PopulationRequest
from backend.population.packs import PACKS_DIR, load_pack

REPEATS = 15
# Second prediction rule, declared on 2026-10-29 after the first SaaS case (a product with a 1.6% share moved to 1.5%,
# under the 1-point floor of the original rule). Reported ALONGSIDE the original, never instead of it. A change of at
# least this fraction of the product's own starting share counts as up/down. Cases written before that date were seen
# before the rule existed, so their relative result is retrospective and is labelled so in the report.
RELATIVE_EFFECT = 0.05


class CaseError(ValueError):
    """The case cannot be run as written. The message says what to fix."""


@dataclass
class SeedResult:
    seed: int
    share_before: float
    share_after: float | None
    prediction: str
    relative_prediction: str | None = None


@dataclass
class Prediction:
    outcome: str
    agreement: float  # share of seeds that agree with the majority outcome
    relative_outcome: str | None = None  # the same question under the relative rule (direction cases only)
    seeds: list[SeedResult] = field(default_factory=list)
    mean_before: float = 0.0
    mean_after: float | None = None
    mean_delta: float | None = None
    sd_delta: float | None = None


def pack_fingerprint(pack: str) -> str:
    """Short hash of the pack file, recorded in the report so a result can be tied to the exact priors used."""
    return hashlib.sha256((PACKS_DIR / f"{pack}.yaml").read_bytes()).hexdigest()[:12]


def build_options(case: Case, products: list[dict]) -> list[dict]:
    pack = load_pack(case.pack)
    options = copy.deepcopy(products)
    for o in options:
        for key in ("id", "role", "price", "features"):
            if key not in o:
                raise CaseError(f"{case.case_id}: product {o.get('id', '?')} is missing '{key}'")
        if len(o["features"]) != len(pack.attributes):
            raise CaseError(
                f"{case.case_id}: product '{o['id']}' needs {len(pack.attributes)} feature values "
                f"in the order {pack.attributes}, got {len(o['features'])}"
            )
        o.setdefault("novelty", 0.0)
        o.setdefault("label", o["id"])
    if not any(o["role"] == "outside" for o in options):
        options.append({"id": pack.outside_id, "label": "Do nothing", "role": "outside"})
    if case.subject not in {o["id"] for o in options}:
        raise CaseError(f"{case.case_id}: subject '{case.subject}' is not among the products")
    return options


def _share(agents: list[dict], options: list[dict], seed: int, subject: str) -> float:
    return run_scenario(agents, options, seed, repeats=REPEATS)["totals"][subject]["p50"]


def direction_rule(delta: float, min_effect: float) -> str:
    return "up" if delta >= min_effect else "down" if delta <= -min_effect else "flat"


def relative_rule(share_before: float, share_after: float, min_relative: float = RELATIVE_EFFECT) -> str:
    """Up/down when the share moved by at least `min_relative` of where it started; a zero start only counts as flat."""
    if share_before <= 0:
        return "flat"
    change = (share_after - share_before) / share_before
    return "up" if change >= min_relative else "down" if change <= -min_relative else "flat"


def predict(case: Case) -> Prediction:
    before = build_options(case, case.scenario_before.products)
    after = build_options(case, case.scenario_after.products) if case.question_type == "direction" else None
    results: list[SeedResult] = []
    for seed in case.seeds:
        pop = template_population(PopulationRequest(pack=case.pack, n_agents=case.n_agents, seed=seed,
                                                    geography=case.geography))
        s_before = _share(pop["agents"], before, seed, case.subject)
        if case.question_type == "direction":
            s_after = _share(pop["agents"], after, seed, case.subject)
            pred = direction_rule(s_after - s_before, case.min_effect)
            rel = relative_rule(s_before, s_after)
        else:
            s_after = rel = None
            pred = "success" if s_before >= case.success.threshold else "fail"
        results.append(SeedResult(seed, s_before, s_after, pred, rel))

    votes = Counter(r.prediction for r in results)
    top = max(votes.values())
    tied = [o for o in case.outcomes if votes.get(o, 0) == top]
    if len(tied) == 1:
        outcome = tied[0]
    elif case.question_type == "direction":  # tie: follow the sign of the average change
        outcome = direction_rule(mean(r.share_after - r.share_before for r in results), case.min_effect)
    else:  # tie: follow the average share against the threshold
        outcome = "success" if mean(r.share_before for r in results) >= case.success.threshold else "fail"

    pred = Prediction(outcome=outcome, agreement=votes[outcome] / len(results), seeds=results,
                      mean_before=mean(r.share_before for r in results))
    if case.question_type == "direction":
        rel_votes = Counter(r.relative_prediction for r in results)
        rel_top = max(rel_votes.values())
        rel_tied = [o for o in case.outcomes if rel_votes.get(o, 0) == rel_top]
        pred.relative_outcome = rel_tied[0] if len(rel_tied) == 1 else relative_rule(
            pred.mean_before, mean(r.share_after for r in results))
        deltas = [r.share_after - r.share_before for r in results]
        pred.mean_after = mean(r.share_after for r in results)
        pred.mean_delta, pred.sd_delta = mean(deltas), pstdev(deltas)
    return pred


def default_case_paths(root: Path | None = None) -> list[Path]:
    base = root or Path(__file__).resolve().parents[2]
    return sorted([*base.glob("backtest/cases/*.yaml"), *base.glob("backend/council/backtest/*.yaml")])
