"""Experiment Kit generator.

Builds a KitOutput from a CouncilOutput and pack content. Content is ordered
by the Council's risk ranking: hypotheses and ads that test the top risk come
first. Generation is deterministic templating; no LLM call is made.
"""
from __future__ import annotations

from typing import List, Optional

from backend.council.schemas import CouncilOutput, KitAssets, KitOffline, KitOutput, TrackingPlan
from backend.kit.packs import kit_content, load_pack, outside_label

ALT_PRICE_FACTOR = 0.8  # matches the Devil's Advocate -20% willingness-to-pay test
THRESHOLD_MARKER = "Proposed test threshold"
RISK_KEYWORDS = {
    "budget": ("willingness to pay", "higher budgets"),
    "alpha": ("price-sensitive", "price-driven"),
    "brand": ("rival brands",),
    "competitor": ("responds with",),
}


class KitValidationError(ValueError):
    pass


class _SafeDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def money(currency: str, value: float) -> str:
    return f"{currency}{value:.0f}" if float(value).is_integer() else f"{currency}{value:.2f}"


def risk_order(council: CouncilOutput) -> List[str]:
    keys: List[str] = []
    for risk in council.risks:
        title = risk.title.lower()
        for key, words in RISK_KEYWORDS.items():
            if any(w in title for w in words) and key not in keys:
                keys.append(key)
    return keys + [k for k in ("budget", "alpha", "brand", "competitor", "default") if k not in keys]


def _prioritise(items: List[dict], order: List[str]) -> List[dict]:
    rank = {k: n for n, k in enumerate(order)}
    return sorted(items, key=lambda it: rank.get(it.get("key", "default"), len(rank)))


def build_context(council: CouncilOutput, pack: str, product: dict, competitor_label: Optional[str] = None) -> dict:
    data = load_pack(pack)
    currency = data.get("currency", "S$")
    price = product.get("price")
    if not isinstance(price, (int, float)) or price < 0:
        raise KitValidationError(f"product price must be a non-negative number, got {price!r}")
    competitor = competitor_label
    if competitor is None and council.competitor_reaction:
        competitor = council.competitor_reaction.competitor_id.replace("_", " ")
    return {
        "product": product.get("label") or "your product",
        "price": money(currency, price),
        "price_low": money(currency, round(price * ALT_PRICE_FACTOR, 2)),
        "price_high": money(currency, round(price * 1.2, 2)),
        "currency": currency,
        "competitor": competitor or "your current option",
        "outside": outside_label(pack),
    }


def generate_kit(council: CouncilOutput, pack: str, product: dict, competitor_label: Optional[str] = None) -> KitOutput:
    content = kit_content(pack)
    ctx = _SafeDict(build_context(council, pack, product, competitor_label))
    fmt = lambda s: s.format_map(ctx).strip()
    order = risk_order(council)

    hypotheses = [fmt(h["text"]) for h in _prioritise(content["hypotheses"], order)][:5]
    landing = content["landing"]
    landing_copy = "\n".join(
        [f"# {fmt(landing['headline'])}", "", fmt(landing["subhead"]), "", "## Why switch"]
        + [f"- {fmt(b)}" for b in landing["benefits"]]
        + ["", "## Price positioning to test (proposed variants)"]
        + [f"- {fmt(p)}" for p in landing["price_positioning"]]
    )
    offline = content["offline"]
    tracking = content.get("tracking_plan")
    kit = KitOutput(
        hypotheses=hypotheses,
        assets=KitAssets(
            landing_copy=landing_copy,
            survey=[fmt(q) for q in content["survey"]],
            interview_script=[fmt(q) for q in content["interview_script"]],
            ad_variants=[fmt(a["text"]) for a in _prioritise(content["ad_variants"], order)],
            offline=KitOffline(
                flyer=fmt(offline["flyer"]),
                checklist=[fmt(c) for c in offline["checklist"]],
                price_board_test=[fmt(c) for c in offline.get("price_board_test", [])],
            ),
            telegram_variants=[fmt(t) for t in content["telegram_variants"]],
            tracking_plan=TrackingPlan(
                metrics=[fmt(m) for m in tracking["metrics"]], decision_rule=fmt(tracking["decision_rule"])
            ) if tracking else None,
        ),
    )
    validate_kit(kit)
    return kit


def validate_kit(kit: KitOutput) -> None:
    a = kit.assets
    problems = []
    if not 3 <= len(kit.hypotheses) <= 5:
        problems.append(f"expected 3-5 hypotheses, got {len(kit.hypotheses)}")
    if any(THRESHOLD_MARKER not in h for h in kit.hypotheses):
        problems.append("every hypothesis must state a proposed test threshold")
    if not 8 <= len(a.survey) <= 12:
        problems.append(f"expected 8-12 survey questions, got {len(a.survey)}")
    if len(a.ad_variants) < 2:
        problems.append("expected at least 2 ad variants")
    if len(a.telegram_variants) != 2:
        problems.append("expected exactly 2 Telegram variants")
    if a.offline is None:
        problems.append("offline kit assets are required for SaaS and café packs")
    elif not a.interview_script or not a.offline.checklist or not a.offline.flyer.strip() or not a.landing_copy.strip():
        problems.append("interview script, checklist, flyer and landing copy must be non-empty")
    price_board = list(getattr(a.offline, "price_board_test", None) or []) if a.offline else []
    texts = [a.landing_copy, *kit.hypotheses, *a.survey, *a.interview_script, *a.ad_variants, *a.telegram_variants]
    if a.offline:
        texts.extend([a.offline.flyer, *a.offline.checklist, *price_board])
    if any("{" in t and "}" in t for t in texts):
        problems.append("unfilled template placeholder in kit text")
    if problems:
        raise KitValidationError("; ".join(problems))
