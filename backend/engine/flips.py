"""Closed-form "what would flip me" for the Glass-Box (Person A). Pure maths on the engine's own utilities.

Definition. For a customer and a target option (normally the founder's product "you"):
    gap = U(best other affordable option) - U(target)       (positive: somebody else beats you)
A "flip" is the smallest change that closes the gap, i.e. makes the target this customer's highest-utility option:
    price drop      d >= gap / alpha            and the price must also fall to within the customer's budget
    feature boost   b >= gap / w_k              and the feature cannot go above 1
    switch credit   worth gap / alpha in price  and it cannot exceed the customer's switching cost
If a lever cannot close the gap it is reported as None (never a nonsense number) and the reason goes in `note`.
Customers who already prefer the target get `price_rise`: how far the price could rise before they leave.

The draw in the engine is random, so "top choice by utility" is what a flip changes, not a guaranteed purchase.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from backend.engine.engine_ref import _arrays

EPS = 1e-9


@dataclass
class UtilityTable:
    ids: list[str]  # option ids, products then outside (last)
    agent_ids: list[str]
    segments: list[str]
    U_raw: np.ndarray  # (n, m+1) utility ignoring affordability
    afford: np.ndarray  # (n, m+1) bool
    comp: dict[str, np.ndarray]  # term -> (n, m) component of each product option
    price: np.ndarray  # (m,)
    features: np.ndarray  # (m, K)
    attributes: list[str]
    budget: np.ndarray  # (n,)
    alpha: np.ndarray  # (n,)
    w: np.ndarray  # (n, K)
    switch: np.ndarray  # (n,)
    incumbent: list[str]


def build_table(agents: list[dict], options: list[dict], attributes: list[str]) -> UtilityTable:
    ids, outside_id, price, budget, _tau, out_u, comp = _arrays(agents, options)
    products = [o for o in options if o["role"] != "outside"]
    U = sum(comp.values())
    n = len(agents)
    return UtilityTable(
        ids=ids + [outside_id],
        agent_ids=[a["id"] for a in agents],
        segments=[a["segment"] for a in agents],
        U_raw=np.hstack([U, out_u[:, None]]),
        afford=np.hstack([price[None, :] <= budget[:, None], np.ones((n, 1), dtype=bool)]),
        comp=comp,
        price=price,
        features=np.array([o["features"] for o in products], dtype=float),
        attributes=list(attributes),
        budget=budget,
        alpha=np.array([a["alpha"] for a in agents], dtype=float),
        w=np.array([a["w"] for a in agents], dtype=float),
        switch=np.array([a["switch"] for a in agents], dtype=float),
        incumbent=[a["incumbent"] for a in agents],
    )


def _up(x: float) -> float:
    """Round UP to 2 decimals so the stated change really does close the gap."""
    return math.ceil(x * 100 - 1e-9) / 100


def _best_other(t: UtilityTable, i: int, j: int) -> tuple[int, float]:
    others = [k for k in range(len(t.ids)) if k != j and t.afford[i, k]]
    best = max(others, key=lambda k: t.U_raw[i, k])
    return best, float(t.U_raw[i, best])


def flip_for_agent(t: UtilityTable, i: int, target: str = "you", money: str = "S$") -> dict:
    """Flip levers for customer index `i`. Keys: price_drop, feature_boost, switch_incentive, price_rise, note,
    plus gap, beaten_by, already_top (internal facts used by the narration)."""
    j = t.ids.index(target)
    best, u_best = _best_other(t, i, j)
    gap = u_best - float(t.U_raw[i, j])
    alpha = float(t.alpha[i])
    price_t = float(t.price[j])
    affordable = bool(t.afford[i, j])
    out = {"price_drop": None, "feature_boost": None, "switch_incentive": None, "price_rise": None, "note": None,
           "gap": gap, "beaten_by": t.ids[best], "already_top": affordable and gap < 0, "price_unreachable": False}

    if out["already_top"]:
        out["price_rise"] = _up(-gap / alpha) if alpha > EPS else None
        out["note"] = "Already prefers this option; the price rise shown is how far it could go before they leave."
        return out

    # price drop: close the utility gap AND get the price within budget
    need_util = gap / alpha if alpha > EPS else math.inf
    need_budget = max(0.0, price_t - float(t.budget[i]))
    need = max(need_util, need_budget)
    if need <= price_t + EPS:
        out["price_drop"] = _up(need)
    else:
        out["price_unreachable"] = True
        out["note"] = (
            f"A price cut of {money}{_up(need):.2f} would be needed, which is more than the {money}{price_t:.2f} "
            "price, so price alone cannot flip this customer."
        )

    if not affordable:
        extra = f"The price is above this customer's budget of {money}{float(t.budget[i]):.2f}."
        out["note"] = f"{extra} {out['note']}" if out["note"] else extra
        return out  # features and credits cannot fix affordability

    # feature boost: cheapest feasible attribute
    best_boost = None
    for k, attr in enumerate(t.attributes):
        wk = float(t.w[i, k])
        if wk <= EPS:
            continue
        amount = gap / wk
        if t.features[j, k] + amount <= 1 + EPS and (best_boost is None or amount < best_boost[1]):
            best_boost = (attr, amount)
    if best_boost:
        out["feature_boost"] = {"attr": best_boost[0], "amount": _up(best_boost[1])}

    # switching credit: cannot remove more than the switching cost the customer actually has
    if t.incumbent[i] != target and t.switch[i] > EPS and gap <= float(t.switch[i]) + EPS and alpha > EPS:
        out["switch_incentive"] = _up(gap / alpha)
    return out


def default_price_cut(price: float) -> float:
    return max(1.0, float(round(price * 0.25)))


def flip_summary(
    t: UtilityTable,
    target: str = "you",
    price_cut: float | None = None,
    feature_boost: float = 0.3,
    min_pct: float = 0.01,
    top: int = 6,
) -> list[dict]:
    """Founder-level lines: how many customers of each segment would flip to `target` under a standard
    price cut or feature boost. `pct` is the share of the WHOLE segment (not only of those who said no)."""
    j = t.ids.index(target)
    price_t = float(t.price[j])
    cut = default_price_cut(price_t) if price_cut is None else price_cut
    n = len(t.agent_ids)

    gap = np.empty(n)
    for i in range(n):
        gap[i] = _best_other(t, i, j)[1] - t.U_raw[i, j]
    affordable = t.afford[:, j]
    not_top = ~(affordable & (gap < 0))

    levers: list[tuple[str, str | None, float, np.ndarray]] = []
    new_price_ok = (price_t - cut) <= t.budget + EPS
    levers.append(("price_cut", None, cut, not_top & new_price_ok & (gap - t.alpha * cut <= EPS)))
    for k, attr in enumerate(t.attributes):
        room = max(0.0, 1.0 - float(t.features[j, k]))
        gain = min(feature_boost, room)
        levers.append(("feature", attr, feature_boost, not_top & affordable & (gap - t.w[:, k] * gain <= EPS)))

    rows = []
    for seg in dict.fromkeys(t.segments):
        in_seg = np.array([s == seg for s in t.segments])
        size = int(in_seg.sum())
        for lever, attr, amount, flips in levers:
            count = int((flips & in_seg).sum())
            if size and count / size >= min_pct:
                rows.append({"segment": seg, "lever": lever, "attr": attr, "amount": amount,
                             "pct": count / size, "n_flipped": count, "n_segment": size})
    rows.sort(key=lambda r: -r["pct"])
    return rows[:top]
