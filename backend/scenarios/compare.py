"""Scenario compare (Person A): run the market twice, change your strategy in B, and show exactly what moved.

Both scenarios use the SAME customers (after the project's saved overrides) and the SAME random seed, so the
difference between A and B comes from the change you made, not from dice rolls. B's run carries `prev_choice` from
A, so the Arena can animate who switched.
"""
from __future__ import annotations

import copy

from pydantic import BaseModel, Field

from backend.engine.engine import run_scenario
from backend.glassbox.explain import money_symbol, summarize_flips
from backend.scenarios.context import ScenarioContext
from backend.scenarios.overrides import OverrideStore, apply_overrides, get_store


class CompareError(ValueError):
    """The requested change is invalid, or the engine cannot run it. The message says why."""


class OptionChange(BaseModel):
    price: float | None = Field(default=None, ge=0)
    # either a full list in the pack's attribute order, or {attribute: value} to change just some
    features: list[float] | dict[str, float] | None = None
    novelty: float | None = Field(default=None, ge=0, le=1)


class CompareRequest(BaseModel):
    project_id: str = "proj_1"
    run_id: str | None = None  # compare from a stored run's market instead of the fixtures
    changes: dict[str, OptionChange] = Field(default_factory=lambda: {"you": OptionChange(price=3.0)})
    label_a: str = "Baseline"
    label_b: str | None = None
    apply_overrides: bool = True  # include the project's saved human overrides in BOTH scenarios
    seed: int | None = None
    repeats: int | None = Field(default=None, ge=1, le=200)


def _check_unit(name: str, v: float) -> None:
    if not 0.0 <= v <= 1.0:
        raise CompareError(f"{name} must be between 0 and 1, got {v}")


def apply_changes(ctx: ScenarioContext, changes: dict[str, OptionChange]) -> list[dict]:
    """Return a copy of the options with the changes applied (validated)."""
    options = copy.deepcopy(ctx.options)
    by_id = {o["id"]: o for o in options}
    attrs = ctx.population["attributes"]
    if not changes:
        raise CompareError("no changes given: scenario B would equal scenario A")
    for oid, ch in changes.items():
        o = by_id.get(oid)
        if o is None:
            raise CompareError(f"unknown option '{oid}' (known: {sorted(by_id)})")
        if o.get("role") == "outside":
            raise CompareError("the outside option cannot be changed")
        if ch.price is not None:
            o["price"] = ch.price
        if ch.novelty is not None:
            o["novelty"] = ch.novelty
        if isinstance(ch.features, list):
            if len(ch.features) != len(attrs):
                raise CompareError(f"features needs {len(attrs)} values ({attrs}), got {len(ch.features)}")
            for a, v in zip(attrs, ch.features, strict=True):
                _check_unit(f"feature {a}", v)
            o["features"] = list(ch.features)
        elif isinstance(ch.features, dict):
            for a, v in ch.features.items():
                if a not in attrs:
                    raise CompareError(f"unknown feature '{a}' (known: {attrs})")
                _check_unit(f"feature {a}", v)
                o["features"][attrs.index(a)] = v
    return options


def _summary(before: list[dict], after: list[dict], attrs: list[str], money: str) -> list[str]:
    out = []
    for b, a in zip(before, after, strict=True):
        label = a.get("label", a["id"])
        if a.get("role") == "outside":
            continue
        if a.get("price") != b.get("price"):
            out.append(f"{label} price {money}{b['price']:.2f} → {money}{a['price']:.2f}")
        for k, name in enumerate(attrs):
            if abs(a["features"][k] - b["features"][k]) > 1e-9:
                out.append(f"{label} {name.replace('_', ' ')} {b['features'][k]:.2f} → {a['features'][k]:.2f}")
        if a.get("novelty") != b.get("novelty"):
            out.append(f"{label} novelty {b['novelty']:.2f} → {a['novelty']:.2f}")
    return out


def compare(ctx: ScenarioContext, req: CompareRequest, store: OverrideStore | None = None) -> dict:
    seed = ctx.seed if req.seed is None else req.seed
    repeats = ctx.repeats if req.repeats is None else req.repeats
    money = money_symbol(ctx.currency)
    attrs = ctx.population["attributes"]

    options_a = copy.deepcopy(ctx.options)
    options_b = apply_changes(ctx, req.changes)
    overrides = (store or get_store()).list(ctx.project_id) if req.apply_overrides else []
    applied = apply_overrides(ctx, overrides)
    if not applied.agents:
        raise CompareError("every customer is excluded; at least one must remain")

    try:
        run_a = run_scenario(applied.agents, options_a, seed, repeats, locks=applied.locks)
        run_b = run_scenario(applied.agents, options_b, seed, repeats, locks=applied.locks, prev=run_a)
    except ValueError as e:  # e.g. a pinned customer cannot afford B's new price
        raise CompareError(f"scenario cannot run with the saved overrides: {e}") from e

    you = ctx.you_id
    labels = {o["id"]: o.get("label", o["id"]) for o in options_a}
    deltas = []
    for oid in run_a["option_ids"]:
        ta, tb = run_a["totals"][oid], run_b["totals"][oid]
        deltas.append({
            "option_id": oid, "label": labels.get(oid, oid),
            "share_a": ta["share"], "share_b": tb["share"],
            "p50_a": ta["p50"], "p50_b": tb["p50"], "delta_p50": tb["p50"] - ta["p50"],
        })
    ya, yb = run_a["totals"][you], run_b["totals"][you]
    price_a = next(o["price"] for o in options_a if o["id"] == you)
    price_b = next(o["price"] for o in options_b if o["id"] == you)
    rev_a, rev_b = ya["p50"] * price_a * 100, yb["p50"] * price_b * 100  # revenue index per 100 customers

    flip_population = {**ctx.population, "agents": applied.agents}
    return {
        "project_id": ctx.project_id,
        "a": run_a,
        "b": run_b,
        "you_id": you,
        "currency_symbol": money,
        "period": ctx.period,
        "same_seed": seed,
        "overrides_applied": len(overrides),
        "scenarios": {
            "a": {"label": req.label_a, "you_price": price_a, "summary": []},
            "b": {"label": req.label_b or "Scenario B", "you_price": price_b,
                  "summary": _summary(options_a, options_b, attrs, money)},
        },
        "deltas": deltas,
        "headline": {
            "delta_p50": yb["p50"] - ya["p50"],
            # conservative interval: worst case B's p10 minus A's p90, best case B's p90 minus A's p10
            "range_low": yb["p10"] - ya["p90"],
            "range_high": yb["p90"] - ya["p10"],
        },
        "revenue": {
            "revenue_a": rev_a, "revenue_b": rev_b,
            "change_pct": (rev_b / rev_a - 1) if rev_a > 0 else None,
            "note": "Revenue index = median share x price x 100 customers, in this simulation only.",
        },
        "flip_summary_b": summarize_flips(flip_population, options_b, currency=ctx.currency),
    }
