"""Country economics from the World Bank API (Person A). Free, no key, fetched on demand for ANY country.

We read one indicator, GDP per capita at purchasing-power parity (NY.GDP.PCAP.PP.CD), for the user's country and for
the baseline country the pack's priors were written for (Singapore). The ratio, softened by a square root and bounded,
scales every segment's budget range: a market with lower incomes gets lower budgets. This scaling is an
ASSUMPTION (income is not spending on this product), so it is recorded as such and never presented as measured.

Results are cached per country on disk, so repeats are instant and the demo works offline once a country was seen.
A failed fetch returns None and the original priors are used unchanged.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

from backend.common import llm
from backend.evidence.models import Economics

INDICATOR = "NY.GDP.PCAP.PP.CD"
BASE_URL = "https://api.worldbank.org/v2/country/{iso}/indicator/" + INDICATOR + "?format=json&mrnev=1"
CACHE_TTL = 30 * 24 * 3600
SCALE_EXPONENT = 0.5  # budget scales with the square root of the income ratio: spending rises slower than income
SCALE_BOUNDS = (0.25, 2.0)


def budget_scale(gdp: float, baseline_gdp: float) -> float:
    if gdp <= 0 or baseline_gdp <= 0:
        return 1.0
    lo, hi = SCALE_BOUNDS
    return max(lo, min(hi, (gdp / baseline_gdp) ** SCALE_EXPONENT))


def _cache_file(iso: str, cache_dir: Path | None) -> Path:
    return (cache_dir or (llm.CACHE_DIR / "evidence" / "worldbank")) / f"{iso.upper()}.json"


def fetch_gdp(iso: str, client: httpx.Client | None = None, cache_dir: Path | None = None) -> dict | None:
    """{"country", "year", "value", "url"} for one country, or None if unavailable. Cached 30 days."""
    iso = iso.strip().upper()
    f = _cache_file(iso, cache_dir)
    if f.exists():
        d = json.loads(f.read_text())
        if time.time() - d["fetched_at"] < CACHE_TTL:
            return d
    if not (len(iso) in (2, 3) and iso.isalpha()):
        return None
    url = BASE_URL.format(iso=iso)
    own = client is None
    client = client or httpx.Client(timeout=15.0)
    try:
        r = client.get(url)
        if r.status_code != 200:
            return None
        body = r.json()
        rows = body[1] if isinstance(body, list) and len(body) > 1 and body[1] else None
        if not rows or rows[0].get("value") is None:
            return None  # an invalid country code returns an error list with no rows
        row = rows[0]
        out = {"country": row["country"]["value"], "year": int(row["date"]), "value": float(row["value"]),
               "url": url, "fetched_at": time.time()}
    except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError):
        return None
    finally:
        if own:
            client.close()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(out))
    return out


def country_economics(iso: str, baseline: str = "SG", client: httpx.Client | None = None,
                      cache_dir: Path | None = None) -> Economics | None:
    """The country's income level and the budget multiplier it implies, or None (original priors then apply)."""
    here = fetch_gdp(iso, client, cache_dir)
    base = fetch_gdp(baseline, client, cache_dir)
    if not here or not base:
        return None
    return Economics(country=here["country"], iso=iso.upper(), gdp_pc_ppp=here["value"], year=here["year"],
                     baseline_iso=baseline.upper(), baseline_gdp_pc_ppp=base["value"],
                     budget_scale=round(budget_scale(here["value"], base["value"]), 3), source_url=here["url"])
