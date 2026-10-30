"""Put a pack's money assumptions into the founder's currency (Person A). The founder's own price is never touched.

The packs are written in one currency (Singapore dollars): budgets, rivals' prices and price sensitivity per unit of
money. If a founder prices a product in rupees, the engine would compare 500 with budgets of 3 to 25. So the pack's own
money assumptions are re-expressed in the founder's currency by ONE factor, taken from real data: the World Bank's
purchasing-power-parity conversion factor (local currency units that buy what one international dollar buys), as a ratio
to the pack's own country. It is a price-level factor from a published dataset, not a market exchange rate.

  budgets x factor, rivals' and the demo product's prices x factor, price sensitivity (per unit of money) / factor

Said so in plain words in the population's `generation.currency`. If the data is missing for the currency's country, the
pack is left as written and the note says that, so the gap is visible instead of silent.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import httpx

from backend.evidence import worldbank
from backend.intake.currency import reference_country
from backend.population.models import PackSpec

BASELINE_COUNTRY = "SG"  # the country the packs' money assumptions were written for


@dataclass
class Localisation:
    code: str  # the currency the market is simulated in
    scale: float  # multiplier applied to the pack's money assumptions (1.0 = none)
    scaled: bool
    note: str
    source_url: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


def money_scale(pack_currency: str, currency: str | None, geography: str | None,
                client: httpx.Client | None = None, cache_dir=None) -> Localisation:
    if not currency or currency == pack_currency:
        return Localisation(pack_currency, 1.0, False, f"market simulated in {pack_currency}, the pack's own currency")
    country = reference_country(currency, geography)
    missing = Localisation(pack_currency, 1.0, False, (
        f"no purchasing-power data found for {currency}, so the pack's money assumptions stay in {pack_currency} "
        f"and a {currency} price would be compared with {pack_currency} budgets"))
    if country is None:
        return missing
    here = worldbank.ppp_factor(country, client, cache_dir)
    base = worldbank.ppp_factor(BASELINE_COUNTRY, client, cache_dir)
    if not here or not base or here["value"] <= 0 or base["value"] <= 0:
        return missing
    scale = here["value"] / base["value"]
    return Localisation(currency, scale, True, (
        f"the pack's {pack_currency} budgets, rival prices and price sensitivity were re-expressed in {currency} "
        f"(x{scale:.3f}), using the World Bank purchasing-power factor {here['value']:.3f} {currency} per "
        f"international dollar in {here['country']} vs {base['value']:.3f} {pack_currency} in {base['country']} "
        f"({here['year']}); a price-level factor, not an exchange rate. Your own price is not converted."),
        here["url"])


def localise_pack(pack: PackSpec, loc: Localisation) -> PackSpec:
    if not loc.scaled:
        return pack
    k = loc.scale
    spec = pack.model_copy(deep=True)
    spec.currency = loc.code
    for s in spec.segments:
        s.priors.budget = (round(s.priors.budget[0] * k, 2), round(s.priors.budget[1] * k, 2))
        s.priors.alpha = (s.priors.alpha[0] / k, s.priors.alpha[1] / k)
    for c in spec.competitors:
        c["price"] = round(c.get("price", 0.0) * k, 2)
    if spec.demo_product:
        spec.demo_product = {**spec.demo_product, "price": round(spec.demo_product.get("price", 0.0) * k, 2)}
    if spec.max_avg_budget:
        spec.max_avg_budget = spec.max_avg_budget * k
    return spec


def localised(pack: PackSpec, currency: str | None, geography: str | None,
              client: httpx.Client | None = None, cache_dir=None) -> tuple[PackSpec, Localisation]:
    loc = money_scale(pack.currency, currency, geography, client, cache_dir)
    return localise_pack(pack, loc), loc
