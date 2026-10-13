"""Generate the engine-driven fixtures: options, population and two run results.

`python -m scripts.make_fixtures`

The population is sampled with a fixed seed from hand-written SaaS segment priors, so these
fixtures are reproducible. They are placeholders for Person A's real generator.
"""
import json
from pathlib import Path

import numpy as np

from backend.engine.engine_ref import run_scenario

OUT = Path(__file__).resolve().parent.parent / "fixtures"
ATTRS = ["ai_planning", "simplicity", "privacy", "integrations"]

OPTIONS = [
    {"id": "you", "label": "StudyFlow", "role": "you", "price": 7.0,
     "features": [0.8, 0.5, 0.6, 0.3], "novelty": 0.6},
    {"id": "free_tool", "label": "Free planner", "role": "competitor", "price": 0.0,
     "features": [0.1, 0.7, 0.3, 0.1], "novelty": 0.0},
    {"id": "chain_app", "label": "ChainApp", "role": "competitor", "price": 12.0,
     "features": [0.6, 0.6, 0.5, 0.8], "novelty": 0.2},
    {"id": "outside", "label": "Do nothing", "role": "outside"},
]

# name, share, budget range, alpha range, w ranges per attribute, incumbent weights, brand free_tool
SEGMENTS = [
    ("budget", "Budget-conscious students", 0.35, (3, 9), (0.15, 0.30),
     [(0.1, 0.5), (0.5, 0.9), (0.1, 0.4), (0.0, 0.2)], {"free_tool": 0.7, "outside": 0.3}, (0.2, 0.6)),
    ("exam", "Exam-focused students", 0.25, (6, 15), (0.05, 0.15),
     [(0.5, 0.9), (0.3, 0.7), (0.2, 0.5), (0.1, 0.4)],
     {"free_tool": 0.5, "chain_app": 0.3, "outside": 0.2}, (0.0, 0.3)),
    ("power", "Productivity enthusiasts", 0.15, (8, 25), (0.05, 0.10),
     [(0.3, 0.7), (0.2, 0.5), (0.4, 0.9), (0.5, 0.9)], {"chain_app": 0.6, "free_tool": 0.4}, (0.0, 0.2)),
    ("loyal", "Free-tool loyalists (hostile)", 0.25, (0, 4), (0.25, 0.30),
     [(0.0, 0.2), (0.6, 1.0), (0.1, 0.4), (0.0, 0.1)], {"free_tool": 0.85, "outside": 0.15}, (0.6, 1.0)),
]


def make_population(n: int = 80, seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)
    agents = []
    for sid, _name, share, bud, alpha, wr, inc, fb in SEGMENTS:
        for _ in range(round(n * share)):
            incumbent = rng.choice(list(inc), p=list(inc.values()))
            agents.append({
                "id": f"a{len(agents):03d}", "segment": sid,
                "budget": round(float(rng.uniform(*bud)), 2),
                "alpha": round(float(rng.uniform(*alpha)), 3),
                "w": [round(float(rng.uniform(*r)), 3) for r in wr],
                "brand": {"you": 0.0, "free_tool": round(float(rng.uniform(*fb)), 3),
                          "chain_app": round(float(rng.uniform(0.0, 0.3)), 3)},
                "switch": round(float(rng.uniform(0.1, 0.6)), 3),
                "risk": round(float(rng.uniform(0.1, 0.5)), 3),
                "incumbent": str(incumbent),
                "outside_utility": round(float(rng.uniform(0.1, 0.5)), 3),
                "tau": round(float(rng.uniform(0.6, 1.0)), 3),
            })
    return {
        "population_id": "pop_saas_1", "seed": seed, "pack": "saas", "attributes": ATTRS,
        "geography": "SG", "evidence_snapshot_id": None,
        "segments": [{"id": s[0], "name": s[1], "share": s[2], "evidence": "llm_assumption"}
                     for s in SEGMENTS],
        "agents": agents,
    }


def main() -> None:
    pop = make_population()
    base = run_scenario(pop["agents"], OPTIONS, seed=42, repeats=30)

    options_b = [dict(o) for o in OPTIONS]
    options_b[0]["price"] = 3.0  # scenario B: price cut
    after = run_scenario(pop["agents"], options_b, seed=42, repeats=30)
    prev = {c["agent_id"]: c["choice"] for c in base["choices"]}
    for c in after["choices"]:
        c["prev_choice"] = prev[c["agent_id"]]
    after["run_id"] = "run_42_price3"

    for name, data in [("options_saas", OPTIONS), ("population_saas", pop),
                       ("run_result", base), ("run_result_price3", after)]:
        (OUT / f"{name}.json").write_text(json.dumps(data, indent=2) + "\n")
    print("wrote", len(pop["agents"]), "agents;", {k: v["share"] for k, v in base["totals"].items()})


if __name__ == "__main__":
    main()
