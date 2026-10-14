"""Decision engine (Person A). Same math as engine_ref.py, plus overrides, prev_choice and honest ranges.

    run_scenario(agents, options, seed, repeats=1, *, locks=None, prev=None, jitter=0.10) -> dict

The result matches the RunResult contract. Math decides; no LLM is involved.

What is new compared with engine_ref
- locks: pin a customer or a whole segment to an option (a human override, marked `locked`).
    {"agents": {agent_id: option_id}, "segments": {segment_id: option_id}}   (agent beats segment)
  A lock naming an unknown agent/option, or an option the agent cannot afford, raises ValueError:
  affordability is a hard rule, so we fail loudly instead of silently breaking it.
- prev: the previous RunResult; fills `prev_choice` so the Arena can animate who moved.
- jitter: repeat 0 is the canonical run (no jitter, same draw as engine_ref, drives `choices` and
  `count`/`share`). Repeats 1..R-1 scale each SEGMENT's budget, price sensitivity and brand by a factor in
  [1 - jitter, 1 + jitter] (one shared shock per segment and parameter), so p10/p50/p90 reflect uncertainty
  in the assumptions, not just dice rolls. Shared shocks matter: independent per-agent noise averages out
  across hundreds of agents and leaves the ranges unchanged.
- choices also carry `p_choice` (model probability of the chosen option) and `locked`.
"""
from __future__ import annotations

import numpy as np

from backend.engine.engine_ref import _arrays, _draw, _probabilities

COMPONENTS = ("brand", "feature", "price", "switch", "risk")


def _resolve_locks(locks: dict | None, agents: list[dict], all_ids: list[str]) -> np.ndarray:
    """Return an (n,) array of option indices to force, -1 where the agent is not locked."""
    lock_idx = np.full(len(agents), -1, dtype=int)
    if not locks:
        return lock_idx
    pos = {oid: j for j, oid in enumerate(all_ids)}
    by_agent = locks.get("agents", {})
    by_segment = locks.get("segments", {})
    unknown = set(by_agent) - {a["id"] for a in agents}
    if unknown:
        raise ValueError(f"lock names unknown agent(s): {sorted(unknown)}")
    for i, a in enumerate(agents):
        target = by_agent.get(a["id"], by_segment.get(a["segment"]))
        if target is None:
            continue
        if target not in pos:
            raise ValueError(f"lock for {a['id']} names unknown option '{target}'")
        lock_idx[i] = pos[target]
    return lock_idx


def _utilities(comp, price, budget, out_u, factors=None):
    """Utility matrix (n, m+1) with unaffordable options at -inf, plus the affordability mask."""
    brand, price_term = comp["brand"], comp["price"]
    if factors is not None:  # per-agent multipliers: columns are brand, alpha, budget
        brand = brand * factors[:, 0:1]
        price_term = price_term * factors[:, 1:2]
        budget = budget * factors[:, 2]
    U = brand + comp["feature"] + price_term + comp["switch"] + comp["risk"]
    U_all = np.hstack([U, out_u[:, None]])
    afford = np.hstack([price[None, :] <= budget[:, None], np.ones((len(budget), 1), dtype=bool)])
    return np.where(afford, U_all, -np.inf), afford


def run_scenario(
    agents: list[dict],
    options: list[dict],
    seed: int,
    repeats: int = 1,
    *,
    locks: dict | None = None,
    prev: dict | None = None,
    jitter: float = 0.10,
) -> dict:
    ids, outside_id, price, budget, tau, out_u, comp = _arrays(agents, options)
    n, m = len(agents), len(ids)
    all_ids = ids + [outside_id]
    lock_idx = _resolve_locks(locks, agents, all_ids)
    locked = lock_idx >= 0
    rows = np.arange(n)
    seg_names = sorted({a["segment"] for a in agents})
    seg_idx = np.array([seg_names.index(a["segment"]) for a in agents])

    # Repeat 0: canonical, unjittered. Its probabilities, choices and utilities feed the explanations.
    U0, afford0 = _utilities(comp, price, budget, out_u)
    bad = locked & ~afford0[rows, np.where(locked, lock_idx, 0)]
    if bad.any():
        raise ValueError(f"lock to an unaffordable option for agent(s): {[agents[i]['id'] for i in np.where(bad)[0]]}")
    P0 = _probabilities(U0, tau)

    shares = []  # one row of per-option shares per repeat
    choice0 = None
    for r in range(max(1, repeats)):
        if r == 0:
            P = P0
        else:
            # One shock per segment and parameter, shared by every agent in the segment: "this whole segment
            # is 8% more price sensitive than assumed". Independent per-agent noise would average out.
            seg_factors = np.random.default_rng([seed, r, 1]).uniform(1 - jitter, 1 + jitter, size=(len(seg_names), 3))
            U_r, _ = _utilities(comp, price, budget, out_u, seg_factors[seg_idx])
            P = _probabilities(U_r, tau)
        choice = _draw(P, np.random.default_rng(seed + r))
        choice = np.where(locked, lock_idx, choice)
        if r == 0:
            choice0 = choice
        shares.append(np.bincount(choice, minlength=m + 1) / n)
    shares = np.array(shares)

    counts = np.bincount(choice0, minlength=m + 1)
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

    prev_choice = {c["agent_id"]: c["choice"] for c in prev["choices"]} if prev else {}
    choices = []
    for i, a in enumerate(agents):
        c = int(choice0[i])
        others = [(U0[i, j], j) for j in range(m + 1) if j != c and np.isfinite(U0[i, j])]
        runner = max(others)[1] if others else None
        comps = {k: float(comp[k][i, c]) for k in COMPONENTS} if c < m else dict.fromkeys(COMPONENTS, 0.0)
        choices.append(
            {
                "agent_id": a["id"],
                "segment": a["segment"],
                "choice": all_ids[c],
                "prev_choice": prev_choice.get(a["id"]),
                "runner_up": all_ids[runner] if runner is not None else None,
                "gap": float(U0[i, c] - U0[i, runner]) if runner is not None else None,
                "components": comps,
                "p_choice": float(P0[i, c]),
                "locked": bool(locked[i]),
            }
        )

    return {
        "run_id": f"run_{seed}",
        "seed": seed,
        "option_ids": all_ids,
        "totals": totals,
        "choices": choices,
    }
