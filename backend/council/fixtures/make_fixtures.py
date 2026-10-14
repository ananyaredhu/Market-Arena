"""Regenerate Person B's local fixtures (MOCK data, not engine output).

    cd backend && ../.venv/bin/python -m council.fixtures.make_fixtures

Populations are sampled uniformly from illustrative priors (SaaS priors live
here; café priors come from packs/cafe.yaml). RunResults are produced by
sampling from the mock adapter's utility form so the Council can be developed
without Person A's engine or Person C's orchestrator. Every file carries
``"meta": {"source": "mock_fixture"}``.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import yaml

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
FRONTEND_FIXTURES = REPO / "frontend" / "components" / "council" / "fixtures"
SEED = 42
REPEATS = 30

SAAS = {
    "pack": "saas",
    "attributes": ["ai_planning", "simplicity", "privacy", "integrations"],
    "options": [
        {"id": "you", "label": "StudyFlow", "role": "you", "price": 9.0,
         "features": [0.85, 0.8, 0.8, 0.4], "novelty": 0.6},
        {"id": "free_tool", "label": "Free Planner", "role": "competitor", "price": 0.0,
         "features": [0.1, 0.7, 0.4, 0.6], "novelty": 0.0},
        {"id": "chain_app", "label": "PlanPro AI", "role": "competitor", "price": 12.0,
         "features": [0.9, 0.5, 0.4, 0.8], "novelty": 0.2},
        {"id": "outside", "label": "Do nothing / free tool", "role": "outside", "price": 0.0,
         "features": [0.0, 0.0, 0.0, 0.0], "novelty": 0.0},
    ],
    "segments": [
        {"id": "budget", "name": "Budget-conscious students", "share": 0.4, "evidence": "llm_assumption",
         "priors": {
             "budget": [6, 14], "alpha": [0.06, 0.14],
             "w": {
                 "ai_planning": [1.0, 1.8], "simplicity": [0.8, 1.4],
                 "privacy": [0.3, 0.8], "integrations": [0.2, 0.6],
             },
             "switch": [0.1, 0.4], "risk": [0.1, 0.4],
             "outside_utility": [-0.2, 0.6], "tau": [0.5, 0.9],
             "brand": {"free_tool": [0.1, 0.4], "chain_app": [0.0, 0.2]},
             "incumbent": {"free_tool": 0.7, "outside": 0.3},
         }},
        {"id": "power", "name": "Power planners", "share": 0.3, "evidence": "llm_assumption",
         "priors": {
             "budget": [10, 25], "alpha": [0.05, 0.12],
             "w": {
                 "ai_planning": [1.2, 2.0], "simplicity": [0.4, 0.9],
                 "privacy": [0.6, 1.2], "integrations": [0.8, 1.4],
             },
             "switch": [0.2, 0.5], "risk": [0.1, 0.3],
             "outside_utility": [-0.5, 0.2], "tau": [0.5, 0.9],
             "brand": {"chain_app": [0.2, 0.5], "free_tool": [0.0, 0.2]},
             "incumbent": {"chain_app": 0.5, "free_tool": 0.5},
         }},
        {"id": "loyalist", "name": "Free-tool loyalists", "share": 0.3, "evidence": "llm_assumption",
         "priors": {
             "budget": [0, 5], "alpha": [0.3, 0.6],
             "w": {
                 "ai_planning": [0.1, 0.5], "simplicity": [0.8, 1.4],
                 "privacy": [0.2, 0.6], "integrations": [0.4, 0.9],
             },
             "switch": [0.5, 1.0], "risk": [0.4, 0.8],
             "outside_utility": [0.0, 0.6], "tau": [0.5, 0.9],
             "brand": {"free_tool": [0.5, 1.0]},
             "incumbent": {"free_tool": 1.0},
         }},
    ],
}


def cafe_spec() -> dict:
    pack = yaml.safe_load((REPO / "packs" / "cafe.yaml").read_text())
    outside = pack.get("outside_option") or {}
    n = len(pack["attributes"])
    keys = ("id", "label", "role", "price", "features", "novelty")
    rivals = [{k: a[k] for k in keys} for a in pack["competitor_archetypes"]]
    options = [pack["demo_product"]] + rivals + [{
        "id": outside.get("id", "outside"),
        "label": outside.get("label", "Make coffee at home or skip"),
        "role": "outside",
        "price": 0.0,
        "features": [0.0] * n,
        "novelty": 0.0,
    }]
    return {"pack": "cafe", "attributes": pack["attributes"], "options": options, "segments": pack["segments"]}


def sample_population(spec: dict, n: int, seed: int) -> dict:
    rng = np.random.default_rng(seed)
    attrs = spec["attributes"]
    counts = [int(round(s["share"] * n)) for s in spec["segments"]]
    counts[-1] = n - sum(counts[:-1])
    agents = []
    def u(lo_hi):
        return float(round(rng.uniform(*lo_hi), 4))
    for seg, count in zip(spec["segments"], counts):
        p = seg["priors"]
        inc_ids, inc_p = zip(*p["incumbent"].items())
        for _ in range(count):
            agents.append({
                "id": f"a{len(agents) + 1}", "segment": seg["id"],
                "budget": u(p["budget"]), "alpha": u(p["alpha"]),
                "w": [u(p["w"][a]) for a in attrs],
                "brand": {"you": 0.0, **{k: u(v) for k, v in p.get("brand", {}).items()}},
                "switch": u(p["switch"]), "risk": u(p["risk"]),
                "incumbent": str(rng.choice(inc_ids, p=np.array(inc_p) / sum(inc_p))),
                "outside_utility": u(p["outside_utility"]), "tau": u(p["tau"]),
            })
    segments = [{"id": s["id"], "name": s["name"], "share": s["share"], "evidence": s.get("evidence", "llm_assumption")}
                for s in spec["segments"]]
    return {"population_id": f"pop_{spec['pack']}_fixture", "seed": seed, "pack": spec["pack"],
            "attributes": attrs, "segments": segments, "agents": agents, "meta": {"source": "mock_fixture"}}


def _utilities(agent: dict, options: list):
    ids = [o["id"] for o in options] + ["outside"]
    comps = []
    for o in options:
        comps.append({
            "brand": float(agent["brand"].get(o["id"], 0.0)),
            "feature": float(np.dot(agent["w"], o["features"])),
            "price": -agent["alpha"] * o["price"],
            "switch": -agent["switch"] * float(o["id"] != agent["incumbent"]),
            "risk": -agent["risk"] * o["novelty"],
        })
    comps.append({"outside": agent["outside_utility"]})
    util = np.array([sum(c.values()) for c in comps])
    afford = np.array([o["price"] <= agent["budget"] for o in options] + [True])
    util = np.where(afford, util, -np.inf)
    return ids, comps, util


def sample_run(pop: dict, options: list, seed: int) -> dict:
    ids = [o["id"] for o in options] + ["outside"]
    prepared = [_utilities(a, options) for a in pop["agents"]]

    def draw(s):
        rng = np.random.default_rng(s)
        picks = []
        for a, (_, _, util) in zip(pop["agents"], prepared):
            z = util / a["tau"]
            z = z - z.max()
            p = np.exp(z) / np.exp(z).sum()
            picks.append(int(rng.choice(len(ids), p=p)))
        return picks

    main = draw(seed)
    reps = np.array([[np.mean(np.array(draw(seed + r)) == j) for j in range(len(ids))] for r in range(REPEATS)])
    totals = {}
    for j, oid in enumerate(ids):
        count = int(sum(1 for c in main if c == j))
        totals[oid] = {"count": count, "share": round(count / len(main), 4),
                       "p10": round(float(np.percentile(reps[:, j], 10)), 4),
                       "p50": round(float(np.percentile(reps[:, j], 50)), 4),
                       "p90": round(float(np.percentile(reps[:, j], 90)), 4)}
    choices = []
    for a, (_, comps, util), c in zip(pop["agents"], prepared, main):
        order = [j for j in np.argsort(-util) if j != c and np.isfinite(util[j])]
        r = int(order[0]) if order else None
        choices.append({
            "agent_id": a["id"], "segment": a["segment"], "choice": ids[c], "prev_choice": a["incumbent"],
            "runner_up": ids[r] if r is not None else None,
            "gap": round(float(util[c] - util[r]), 4) if r is not None else None,
            "components": {k: round(v, 4) for k, v in comps[c].items()},
        })
    return {"run_id": f"run_{pop['pack']}_fixture", "seed": seed, "option_ids": ids,
            "totals": totals, "choices": choices, "meta": {"source": "mock_fixture"}}


def write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def main() -> None:
    from backend.council.service import run_council, run_kit

    for spec, n in ((SAAS, 300), (cafe_spec(), 300)):
        pack = spec["pack"]
        pop = sample_population(spec, n, SEED)
        options = spec["options"]
        rr = sample_run(pop, options, SEED)
        write(HERE / f"population_{pack}.json", pop)
        write(HERE / f"options_{pack}.json", options)
        write(HERE / f"run_result_{pack}.json", rr)
        result = run_council(rr, pop, options, pack)
        kit = run_kit(result["council"], pack, options)
        for target in (HERE, FRONTEND_FIXTURES):
            write(target / f"council_{pack}.json", result["council"].model_dump())
            write(target / f"kit_{pack}.json", kit.model_dump())
        totals = {k: v["p50"] for k, v in rr["totals"].items()}
        print(pack, "p50 shares:", totals, "| fragility", result["council"].fragility,
              "| reaction", result["council"].competitor_reaction)


if __name__ == "__main__":
    main()
