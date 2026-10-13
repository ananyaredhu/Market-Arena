"""Reference decision engine (baseline for everyone until Person A ships engine.py).

Frozen signature:
    run_scenario(agents: list[dict], options: list[dict], seed: int, repeats: int = 1) -> dict

The returned dict matches the RunResult contract. Math decides, no LLM is involved.

    U_ij = brand_ij + sum_k(w_ik * f_jk) - alpha_i * p_j - switch_i * 1[j != incumbent_i]
           - risk_i * novelty_j
    P(choose j) = softmax(U_ij / tau_i) over affordable options plus the outside option

Notes
- Options with role "outside" are not scored as products; the outside option uses the agent's
  own `outside_utility`. Its id is taken from that option (default "outside").
- Affordability is a hard constraint: price > budget removes the option for that agent.
- `choices` come from repeat 0 (canonical seed). `totals` p10/p50/p90 are taken across repeats.
  This reference does not jitter parameters between repeats; engine.py will.
- `prev_choice` is left None here; the orchestrator fills it by diffing against a previous run.
"""
from __future__ import annotations

import numpy as np

COMPONENTS = ("brand", "feature", "price", "switch", "risk")


def _arrays(agents: list[dict], options: list[dict]):
    products = [o for o in options if o["role"] != "outside"]
    outside = next((o for o in options if o["role"] == "outside"), {"id": "outside"})
    ids = [o["id"] for o in products]
    n, m = len(agents), len(products)

    price = np.array([o["price"] for o in products], dtype=float)
    feats = np.array([o["features"] for o in products], dtype=float)
    novelty = np.array([o.get("novelty", 0.0) for o in products], dtype=float)

    budget = np.array([a["budget"] for a in agents], dtype=float)
    alpha = np.array([a["alpha"] for a in agents], dtype=float)
    w = np.array([a["w"] for a in agents], dtype=float)
    switch = np.array([a["switch"] for a in agents], dtype=float)
    risk = np.array([a["risk"] for a in agents], dtype=float)
    tau = np.array([a["tau"] for a in agents], dtype=float)
    out_u = np.array([a["outside_utility"] for a in agents], dtype=float)
    brand = np.array([[a["brand"].get(i, 0.0) for i in ids] for a in agents], dtype=float)
    incumbent = np.array(
        [[a["incumbent"] == i for i in ids] for a in agents], dtype=bool
    ).reshape(n, m)

    comp = {
        "brand": brand,
        "feature": w @ feats.T,
        "price": -alpha[:, None] * price[None, :],
        "switch": -switch[:, None] * (~incumbent),
        "risk": -risk[:, None] * novelty[None, :],
    }
    return ids, outside["id"], price, budget, tau, out_u, comp


def _probabilities(U: np.ndarray, tau: np.ndarray) -> np.ndarray:
    z = U / tau[:, None]
    z = z - np.max(z, axis=1, keepdims=True)  # -inf stays -inf, max is always finite (outside)
    P = np.exp(z)
    return P / P.sum(axis=1, keepdims=True)


def _draw(P: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Vectorised categorical draw: one uniform per agent against the cumulative probabilities."""
    u = rng.random(P.shape[0])
    idx = (np.cumsum(P, axis=1) < u[:, None]).sum(axis=1)
    return np.minimum(idx, P.shape[1] - 1)


def run_scenario(agents: list[dict], options: list[dict], seed: int, repeats: int = 1) -> dict:
    ids, outside_id, price, budget, tau, out_u, comp = _arrays(agents, options)
    n, m = len(agents), len(ids)
    all_ids = ids + [outside_id]

    U = sum(comp.values())
    U_all = np.hstack([U, out_u[:, None]])
    afford = np.hstack([price[None, :] <= budget[:, None], np.ones((n, 1), dtype=bool)])
    U_all = np.where(afford, U_all, -np.inf)
    P = _probabilities(U_all, tau)

    shares = []  # one row of per-option shares per repeat
    first_choice = None
    for r in range(max(1, repeats)):
        choice = _draw(P, np.random.default_rng(seed + r))
        if r == 0:
            first_choice = choice
        shares.append(np.bincount(choice, minlength=m + 1) / n)
    shares = np.array(shares)

    counts = np.bincount(first_choice, minlength=m + 1)
    totals = {}
    for j, oid in enumerate(all_ids):
        p10, p50, p90 = np.percentile(shares[:, j], [10, 50, 90])
        totals[oid] = {
            "count": int(counts[j]),
            "share": float(counts[j] / n),
            "p10": float(p10),
            "p50": float(p50),
            "p90": float(p90),
        }

    choices = []
    for i, a in enumerate(agents):
        c = int(first_choice[i])
        others = [(U_all[i, j], j) for j in range(m + 1) if j != c and np.isfinite(U_all[i, j])]
        runner = max(others)[1] if others else None
        comps = (
            {k: float(comp[k][i, c]) for k in COMPONENTS}
            if c < m
            else {k: 0.0 for k in COMPONENTS}
        )
        choices.append(
            {
                "agent_id": a["id"],
                "segment": a["segment"],
                "choice": all_ids[c],
                "prev_choice": None,
                "runner_up": all_ids[runner] if runner is not None else None,
                "gap": float(U_all[i, c] - U_all[i, runner]) if runner is not None else None,
                "components": comps,
            }
        )

    return {
        "run_id": f"run_{seed}",
        "seed": seed,
        "option_ids": all_ids,
        "totals": totals,
        "choices": choices,
    }
