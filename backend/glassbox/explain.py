"""Glass-Box explain service (Person A): one customer's decision, with numbers first and language second.

    explain_agent(run_result, population, options, agent_id) -> dict       (matches the AgentExplain contract)
    summarize_flips(population, options)                      -> list[dict]  (the founder-level flip lines)

Order of work, always: (1) rebuild the customer's utilities from the engine's own maths, (2) compute drivers and
flips, (3) freeze them into `Facts`, (4) only then phrase them (template, or LLM verified against the Facts).
"""
from __future__ import annotations

import numpy as np

from backend.common.contracts import AgentExplain
from backend.engine.flips import build_table, default_price_cut, flip_for_agent, flip_summary
from backend.glassbox.narration import Driver, Facts, narrate

TERMS = ("brand", "feature", "price", "switch", "risk")
MONEY = {"SGD": "S$", "USD": "$", "EUR": "€", "GBP": "£", "S$": "S$"}
MIN_DRIVER = 0.05  # ignore terms that barely moved the decision
MAX_DRIVERS = 3


class AgentNotFound(KeyError):
    pass


def money_symbol(currency: str) -> str:
    return MONEY.get(currency, f"{currency} ")


def _labels(options: list[dict]) -> dict[str, str]:
    return {o["id"]: o.get("label", o["id"]) for o in options}


def _your_id(options: list[dict]) -> str:
    return next((o["id"] for o in options if o.get("role") == "you"), "you")


def drivers_for(
    t, c: int, r: int | None, *, limit: int | None = MAX_DRIVERS, min_abs: float = MIN_DRIVER
) -> list[tuple[str, float]]:
    """(term, chosen minus runner-up) pairs; with no limit and min_abs=0 they add up to U(chosen) - U(runner-up).
    The outside option has no component breakdown, only a constant value, reported as the term "outside"."""
    out_idx = len(t.ids) - 1

    def comp(k: int, term: str) -> float:
        return 0.0 if k == out_idx else float(t.comp[term][0, k])

    deltas = {term: comp(c, term) - (comp(r, term) if r is not None else 0.0) for term in TERMS}
    if r is not None:
        out_u = float(t.U_raw[0, out_idx])
        if c == out_idx:
            deltas["outside"] = out_u
        elif r == out_idx:
            deltas["outside"] = -out_u
    ranked = sorted(deltas.items(), key=lambda kv: -abs(kv[1]))
    kept = [(k, v) for k, v in ranked if abs(v) >= min_abs]
    return kept if limit is None else kept[:limit]


def explain_agent(
    run_result: dict, population: dict, options: list[dict], agent_id: str, *, currency: str = "SGD"
) -> dict:
    choice = next((c for c in run_result["choices"] if c["agent_id"] == agent_id), None)
    agent = next((a for a in population["agents"] if a["id"] == agent_id), None)
    if choice is None or agent is None:
        raise AgentNotFound(agent_id)

    money = money_symbol(currency)
    labels = _labels(options)
    you = _your_id(options)
    t = build_table([agent], options, population["attributes"])
    pos = {oid: k for k, oid in enumerate(t.ids)}
    c = pos[choice["choice"]]
    r = pos.get(choice.get("runner_up") or "")

    # ---- (1) and (2): all numbers, by code
    drivers = drivers_for(t, c, r)
    f = flip_for_agent(t, 0, target=you, money=money)
    affordable_u = np.where(t.afford[0], t.U_raw[0], -np.inf)
    top = int(np.argmax(affordable_u))
    against_odds = c != top
    chose_you = choice["choice"] == you
    if chose_you and not f["already_top"]:
        # They already chose your product (a random draw or a manual pin), so "what would win them" makes no sense.
        f = {**f, "price_drop": None, "feature_boost": None, "switch_incentive": None, "price_unreachable": False,
             "note": f"This customer chose your product, but by the numbers they would prefer {labels[t.ids[top]]}."}

    # ---- (3): freeze the facts exactly as they may be quoted
    fb = f["feature_boost"]
    # One rounding (2 decimals) shared by the contract, the narration and the UI labels, so they cannot disagree.
    shown = [Driver(k, round(v, 2)) for k, v in drivers if round(v, 2) != 0]
    facts = Facts(
        chosen=labels.get(choice["choice"], choice["choice"]),
        runner_up=labels.get(choice["runner_up"], choice["runner_up"]) if choice.get("runner_up") else None,
        your_product=labels.get(you, you),
        option_labels=tuple(labels.values()),
        drivers=tuple(shown),
        p_choice_pct=round(100 * choice["p_choice"]) if choice.get("p_choice") is not None else None,
        against_odds=against_odds,
        locked=bool(choice.get("locked")),
        money=money,
        already_top=f["already_top"],
        chose_you=chose_you,
        preferred=labels[t.ids[top]] if (chose_you and against_odds) else None,
        price_drop=f["price_drop"],
        price_rise=f["price_rise"],
        feature_attr=fb["attr"] if fb else None,
        feature_amount=fb["amount"] if fb else None,
        switch_incentive=f["switch_incentive"],
        price_unreachable=f["price_unreachable"],
    )

    # ---- (4): language
    narration, source = narrate(facts)

    explain = {
        "agent_id": agent_id,
        "segment": choice["segment"],
        "choice": choice["choice"],
        "runner_up": choice.get("runner_up"),
        "top_drivers": [{"term": d.term, "delta": d.delta} for d in shown],
        "narration": narration,
        "narration_source": source,
        "flip": {
            "price_drop": f["price_drop"],
            "feature_boost": fb,
            "note": f["note"],
            "switch_incentive": f["switch_incentive"],
            "price_rise": f["price_rise"],
        },
    }
    return AgentExplain.model_validate(explain).model_dump(mode="json")


# ---------------------------------------------------------------- aggregate
def summarize_flips(population: dict, options: list[dict], *, currency: str = "SGD", top: int = 6) -> list[dict]:
    """Rows like {"segment","segment_name","lever","attr","amount","pct","n_flipped","n_segment","text"}."""
    money = money_symbol(currency)
    you = _your_id(options)
    t = build_table(population["agents"], options, population["attributes"])
    price = float(next(o["price"] for o in options if o["id"] == you))
    names = {s["id"]: s.get("name", s["id"]) for s in population.get("segments", [])}
    rows = flip_summary(t, target=you, price_cut=default_price_cut(price), top=top)
    for r in rows:
        name = names.get(r["segment"], r["segment"])
        pct = f"{round(100 * r['pct'])}%"
        if r["lever"] == "price_cut":
            r["text"] = f"{pct} of {name} flip to you with a {money}{r['amount']:.0f} price cut."
        else:
            attr = r["attr"].replace("_", " ")
            r["text"] = f"{pct} of {name} flip to you if you improve {attr} by {r['amount']:.1f}."
        r["segment_name"] = name
    return rows
