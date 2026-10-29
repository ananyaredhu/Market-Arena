"""Suggest a selling price (Person A): run the market at a series of prices and show where your result peaks.

For each candidate price the SAME customers (after the project's saved overrides) and the same seed are simulated, so
the curve comes from the price alone. The suggestion is the price with the best result, plus the band of prices that
come within 5 percent of it:

  * no cost given   result = revenue index = median share x price x 100 customers (as in Scenario compare)
  * cost given      result = profit index  = median share x (price - cost) x 100 customers; the cost is also the
                    lowest price tried, because selling below cost is never suggested

Real prices found by the researcher (the Resources library) are listed next to the curve as reference. They are not
inputs: the market's rivals and customers come from the pack and the population, as everywhere else in the model.
The model cannot see your costs beyond the one you give, your marketing or your capacity, so the answer is where to
START testing a price for real, not a final price.
"""
from __future__ import annotations

import copy

from pydantic import BaseModel, Field

from backend.engine.engine import run_scenario
from backend.evidence import resources, store
from backend.glassbox.explain import money_symbol
from backend.scenarios.context import ScenarioContext
from backend.scenarios.overrides import OverrideStore, apply_overrides, get_store

NEAR_BEST = 0.95  # prices whose result is at least this share of the best one form the suggested band
HIGH_MARGIN = 1.25  # the sweep reaches 25 percent above the highest rival price or customer budget
CUSTOMERS = 100  # indexes are per 100 customers, as in Scenario compare


class PricingError(ValueError):
    """The request cannot be answered. The message says why."""


class PriceSuggestRequest(BaseModel):
    project_id: str = "proj_1"
    run_id: str | None = None
    cost: float | None = Field(default=None, ge=0, description="what one sale costs you, in the market's currency")
    min_price: float | None = Field(default=None, ge=0)
    max_price: float | None = Field(default=None, gt=0)
    steps: int = Field(default=14, ge=4, le=40)
    apply_overrides: bool = True
    seed: int | None = None
    repeats: int | None = Field(default=None, ge=1, le=200)


def _grid(low: float, high: float, steps: int, current: float) -> list[float]:
    points = {round(low + (high - low) * i / (steps - 1), 2) for i in range(steps)}
    if low <= current <= high:
        points.add(round(current, 2))
    return sorted(points)


def _reference_prices(pack: str | None) -> list[dict]:
    items = resources.list_resources(store.resources_dir(), pack=pack, topic="competitor prices")
    return [{"claim": r.claim, "quote": r.quote, "url": r.url, "domain": r.domain, "retrieved_at": r.retrieved_at}
            for r in items[:6]]


def suggest_price(ctx: ScenarioContext, req: PriceSuggestRequest, override_store: OverrideStore | None = None) -> dict:
    seed = ctx.seed if req.seed is None else req.seed
    repeats = ctx.repeats if req.repeats is None else req.repeats
    overrides = (override_store or get_store()).list(ctx.project_id) if req.apply_overrides else []
    applied = apply_overrides(ctx, overrides)
    if not applied.agents:
        raise PricingError("every customer is excluded; at least one must remain")

    you = ctx.you_id
    options = copy.deepcopy(ctx.options)
    current = next(o["price"] for o in options if o["id"] == you)
    rival_prices = [o["price"] for o in options if o.get("role") == "competitor" and o.get("price", 0) > 0]
    budgets = sorted(a["budget"] for a in applied.agents)
    top_budget = budgets[int(0.9 * (len(budgets) - 1))]

    high = req.max_price or max([current, top_budget, *rival_prices]) * HIGH_MARGIN
    low = req.min_price if req.min_price is not None else (req.cost or 0.0)
    if req.cost is not None:
        low = max(low, req.cost)  # never suggest selling below cost
    if low >= high:
        raise PricingError(f"the lowest price to try ({low:g}) is not below the highest ({high:g}); "
                           "lower the cost or the minimum price, or raise the maximum price")
    if req.cost is None and low == 0:
        low = round(high * 0.05, 2)  # a free product is never a revenue-maximising answer, so start just above zero

    rows = []
    for price in _grid(low, high, req.steps, current):
        trial = copy.deepcopy(options)
        next(o for o in trial if o["id"] == you)["price"] = price
        try:
            run = run_scenario(applied.agents, trial, seed, repeats, locks=applied.locks)
        except ValueError as e:  # e.g. a pinned customer cannot afford this price
            raise PricingError(f"the market cannot run at {price:g} with the saved overrides: {e}") from e
        t = run["totals"][you]
        row = {"price": price, "share_p10": t["p10"], "share_p50": t["p50"], "share_p90": t["p90"],
               "revenue_index": t["p50"] * price * CUSTOMERS, "is_current": abs(price - current) < 0.005}
        if req.cost is not None:
            row["profit_index"] = t["p50"] * (price - req.cost) * CUSTOMERS
        rows.append(row)

    key = "profit_index" if req.cost is not None else "revenue_index"
    best = max(rows, key=lambda r: (r[key], -r["price"]))  # ties go to the lower price, which wins more customers
    objective = "profit index" if req.cost is not None else "revenue index"
    money = money_symbol(ctx.currency)

    if best[key] <= 0:
        suggestion, band, notes = None, None, [
            f"At no price from {money}{rows[0]['price']:g} to {money}{rows[-1]['price']:g} does this market buy your "
            "product in a way that earns anything. Lower your cost, strengthen the product, or check who it is for."
        ]
    else:
        at = rows.index(best)
        first = last = at  # the band is the unbroken run of prices around the best one that stay near it
        while first > 0 and rows[first - 1][key] >= NEAR_BEST * best[key]:
            first -= 1
        while last < len(rows) - 1 and rows[last + 1][key] >= NEAR_BEST * best[key]:
            last += 1
        suggestion = {"price": best["price"], "share_p50": best["share_p50"], key: best[key], "objective": objective}
        band = {"low": rows[first]["price"], "high": rows[last]["price"],
                "within": f"{round((1 - NEAR_BEST) * 100)}% of the best {objective}"}
        notes = []
        edges = []
        if last == len(rows) - 1:
            edges.append("highest")
        if first == 0 and req.cost is None:  # with a cost, the lowest price is the cost itself, never to go below
            edges.append("lowest")
        if edges:
            notes.append(f"The best prices reach the {' and '.join(edges)} price tried, so the true best may lie "
                         "beyond it. Widen the range with min_price or max_price.")
    n = len(applied.agents)
    if n < 200:
        notes.append(f"Only {n} customers are simulated, so shares move in steps of {100 / n:.1f} points. "
                     "Small differences between prices are noise.")
    notes.append("The model cannot see your costs beyond the one you give, your marketing or your capacity. "
                 "Treat the suggestion as where to start testing a price for real.")

    return {
        "project_id": ctx.project_id,
        "you_id": you,
        "currency_symbol": money,
        "period": ctx.period,
        "objective": objective,
        "cost": req.cost,
        "current_price": current,
        "same_seed": seed,
        "overrides_applied": len(overrides),
        "customers": n,
        "curve": rows,
        "suggestion": suggestion,
        "band": band,
        "notes": notes,
        "reference_prices": _reference_prices(ctx.population.get("pack")),
        "reference_note": "Real prices the researcher found, for comparison only. They are not used in the curve.",
    }
