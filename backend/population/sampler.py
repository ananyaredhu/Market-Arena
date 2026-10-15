"""Numeric sampling of individual agents from segment priors (Person A). No LLM, fully seeded.

`sample_agents` returns plain dicts that match the `Agent` contract. The same seed and priors always give
the same agents, so a saved population is reproducible.
"""
from __future__ import annotations

import numpy as np

from backend.population.models import SegmentSpec


def segment_counts(shares: list[float], n: int) -> list[int]:
    """Split n agents across segments by share (largest remainder), so the counts always sum to n."""
    total = sum(shares)
    raw = [n * s / total for s in shares]
    counts = [int(x) for x in raw]
    # hand the leftover agents to the largest fractional parts (ties: earlier segment first)
    for i in sorted(range(len(raw)), key=lambda i: (-(raw[i] - counts[i]), i))[: n - sum(counts)]:
        counts[i] += 1
    return counts


def _uniform(rng: np.random.Generator, r: tuple[float, float], k: int) -> np.ndarray:
    return rng.uniform(r[0], r[1], size=k)


def sample_agents(
    segments: list[SegmentSpec],
    attributes: list[str],
    option_ids: list[str],
    outside_id: str,
    n: int,
    seed: int,
) -> list[dict]:
    """Sample `n` agents. `option_ids` are the product options (e.g. you, free_tool, chain_app), not outside."""
    rng = np.random.default_rng(seed)
    known = set(option_ids) | {outside_id}
    rows: list[dict] = []

    for seg, k in zip(segments, segment_counts([s.share for s in segments], n), strict=True):
        if k == 0:
            continue
        p = seg.priors
        budget = _uniform(rng, p.budget, k)
        alpha = _uniform(rng, p.alpha, k)
        w = np.column_stack([_uniform(rng, p.w[a], k) for a in attributes])
        switch = _uniform(rng, p.switch, k)
        risk = _uniform(rng, p.risk, k)
        out_u = _uniform(rng, p.outside_utility, k)
        tau = _uniform(rng, p.tau, k)
        brand = {oid: _uniform(rng, p.brand[oid], k) if oid in p.brand else np.zeros(k) for oid in option_ids}

        inc = {oid: wt for oid, wt in p.incumbent.items() if oid in known}
        if not inc or sum(inc.values()) <= 0:
            raise ValueError(f"segment '{seg.id}': no incumbent weight on a known option {sorted(known)}")
        inc_ids = list(inc)
        incumbent = rng.choice(inc_ids, size=k, p=np.array(list(inc.values())) / sum(inc.values()))

        for i in range(k):
            rows.append(
                {
                    "segment": seg.id,
                    "budget": round(float(budget[i]), 2),
                    "alpha": round(float(alpha[i]), 3),
                    "w": [round(float(x), 3) for x in w[i]],
                    "brand": {oid: round(float(brand[oid][i]), 3) for oid in option_ids},
                    "switch": round(float(switch[i]), 3),
                    "risk": round(float(risk[i]), 3),
                    "incumbent": str(incumbent[i]),
                    "outside_utility": round(float(out_u[i]), 3),
                    "tau": round(float(tau[i]), 3),
                }
            )

    # Interleave segments (so "the first 40 agents" is a fair sample), then number them.
    order = rng.permutation(len(rows))
    agents = []
    for new_id, idx in enumerate(order):
        agents.append({"id": f"a{new_id:03d}", **rows[idx]})
    return agents
