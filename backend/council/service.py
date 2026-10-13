"""Entry points that compose Strategist, Advocate, Moderator and Kit."""
from __future__ import annotations

from typing import List, Optional

from backend.council.advocate import run_advocate
from backend.council.engine_adapter import YOU_ID, EngineAdapter, get_default_adapter
from backend.council.moderator import build_council
from backend.council.schemas import CouncilOutput, KitOutput, RunResult
from backend.council.strategist import run_strategist
from backend.council.wording import Wording
from backend.kit.generator import ALT_PRICE_FACTOR, generate_kit, money
from backend.kit.packs import kit_content, load_pack, outside_label


def _product(options: List[dict]) -> dict:
    you = next((o for o in options if o.get("id") == YOU_ID), None)
    return you or {"id": YOU_ID, "label": "your product", "price": 0.0}


def competitor_label(council: CouncilOutput, options: List[dict]) -> Optional[str]:
    if not council.competitor_reaction:
        return None
    cid = council.competitor_reaction.competitor_id
    return next((o.get("label", cid) for o in options if o.get("id") == cid), cid)


def run_council(
    run_result, population: dict, options: List[dict], pack: str, *,
    adapter: Optional[EngineAdapter] = None, wording: Optional[Wording] = None, seed: Optional[int] = None,
) -> dict:
    rr = run_result if isinstance(run_result, RunResult) else RunResult(**run_result)
    adapter = adapter or get_default_adapter()
    seed = rr.seed if seed is None else seed
    agents = population.get("agents", [])
    strategist = run_strategist(agents, options, adapter, seed)
    advocate = run_advocate(agents, options, adapter, seed)

    product = _product(options)
    context = {"outside": outside_label(pack)}
    price = product.get("price")
    if isinstance(price, (int, float)) and price >= 0:
        currency = load_pack(pack).get("currency", "S$")
        context.update(price=money(currency, price), price_low=money(currency, round(price * ALT_PRICE_FACTOR, 2)))

    council = build_council(
        rr, strategist, advocate, population=population, options=options,
        experiment_library=kit_content(pack)["experiment_library"], context=context, wording=wording,
    )
    return {"council": council, "strategist": strategist.to_dict(), "advocate": advocate.to_dict()}


def run_kit(council: CouncilOutput, pack: str, options: List[dict]) -> KitOutput:
    return generate_kit(council, pack, _product(options), competitor_label(council, options))
