"""Official Singapore statistics from SingStat's Table Builder API (Person A). Free, no key.

Two real datasets:

  * Consumer Price Index (annual time series since 1961). The all-items series is kept whole in the snapshot
    (`price_index`) and moves every budget by the FULL measured change from a starting year to the latest year (see
    apply.py); no cap and no skipping, because it is the reported figure. The categories that match the pack, with the
    change on last year and over five years, are shown as facts.
  * Household Expenditure Survey 2023: average monthly spending per resident HOUSEHOLD on the matching categories.
    Shown only: it is per household, not per student or per visit, so using it to set a budget would be a guess
    presented as data.

Facts are in the snapshot, in the Resources library as "official data", and available to the Council as labelled
reference.

Tables are cached on disk for 30 days. A failed fetch returns no facts and nothing else changes.
"""
from __future__ import annotations

import json
import re
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

from backend.common import llm
from backend.evidence.models import DatasetFact, PriceIndex

BASE_URL = "https://tablebuilder.singstat.gov.sg/api/table/tabledata/{table_id}"
USER_AGENT = "MarketArenaResearchBot/0.1 (student project; evidence research)"
CACHE_TTL = 30 * 24 * 3600
CPI_TABLE = "M213801"  # Consumer Price Index, 2024 as base year, annual
HES_TABLE = "18005"  # Household Expenditure Survey 2023, by type of goods and services and expenditure quintile
HES_YEAR = "2023"
_ID = re.compile(r"^[A-Za-z0-9]{3,12}$")

# Which categories matter for which pack. Only the names SingStat uses; a missing row is skipped, not guessed.
CPI_ROWS = {"saas": ["Information & Communication", "Education"], "cafe": ["Food & Beverage Serving Services"]}
HES_ROWS = {"saas": ["Information and Communication", "Education"], "cafe": ["Food and Beverage Serving Services 2/"]}
SINGAPORE = ("SG", "SGP", "SINGAPORE")


def _cache_file(table_id: str, cache_dir: Path | None) -> Path:
    return (cache_dir or (llm.CACHE_DIR / "evidence" / "singstat")) / f"{table_id}.json"


def fetch_table(table_id: str, client: httpx.Client | None = None, cache_dir: Path | None = None) -> dict | None:
    """The table's `Data` object (title, row list), or None if unavailable. Cached 30 days."""
    if not _ID.match(table_id):
        return None
    f = _cache_file(table_id, cache_dir)
    if f.exists():
        cached = json.loads(f.read_text())
        if time.time() - cached["fetched_at"] < CACHE_TTL:
            return cached["data"]
    own = client is None
    client = client or httpx.Client(timeout=30.0, headers={"User-Agent": USER_AGENT})
    try:
        r = client.get(BASE_URL.format(table_id=table_id))
        if r.status_code != 200:
            return None
        data = r.json()["Data"]
        if not isinstance(data.get("row"), list) or not data["row"]:
            return None
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        return None
    finally:
        if own:
            client.close()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"fetched_at": time.time(), "data": data}))
    return data


def _number(text) -> float | None:
    try:
        return float(str(text).replace(",", ""))
    except ValueError:
        return None


def _row(data: dict, name: str) -> dict | None:
    return next((r for r in data["row"] if r.get("rowText", "").strip() == name), None)


def _series(row: dict) -> dict[str, float]:
    """period -> value for a time-series row. Cells without a number (n.a., blank) are left out."""
    out = {}
    for c in row.get("columns", []):
        v = _number(c.get("value"))
        if v is not None:
            out[str(c.get("key"))] = v
    return out


def _pct(new: float, old: float) -> float:
    return (new / old - 1) * 100


def cpi_facts(pack: str, data: dict, retrieved_at: str) -> list[DatasetFact]:
    url = BASE_URL.format(table_id=CPI_TABLE)
    overall = _row(data, "All Items")
    if overall is None:
        return []
    base = _series(overall)
    year = max(base, key=int)

    def change(series: dict[str, float], years: int) -> float | None:
        past = str(int(year) - years)
        return _pct(series[year], series[past]) if year in series and past in series else None

    out = []
    for name in ["All Items", *CPI_ROWS.get(pack, [])]:
        row = _row(data, name)
        series = _series(row) if row else {}
        if year not in series:
            continue
        one, five = change(series, 1), change(series, 5)
        parts = [f"{one:+.1f}% on {int(year) - 1}" if one is not None else None,
                 f"{five:+.1f}% over 5 years" if five is not None else None]
        out.append(DatasetFact(
            name=f"Consumer prices: {name}", source="SingStat Table Builder", table_id=CPI_TABLE, url=url,
            period=year, value=round(series[year], 3), unit="index (2024 = 100)",
            note=", ".join(p for p in parts if p) or "no earlier year to compare",
            quote=f"{name}, {year}: {series[year]} (Index)", retrieved_at=retrieved_at))
    return out


def hes_facts(pack: str, data: dict, retrieved_at: str) -> list[DatasetFact]:
    url = BASE_URL.format(table_id=HES_TABLE)
    total = _row(data, "Total")
    out = []
    for name in HES_ROWS.get(pack, []):
        row = _row(data, name)
        value = _number(row["columns"][0].get("value")) if row and row.get("columns") else None
        if value is None:
            continue
        share = ""
        whole = _number(total["columns"][0].get("value")) if total and total.get("columns") else None
        if whole:
            share = f" ({value / whole * 100:.1f}% of all household spending)"
        label = name.rstrip(" 0123456789/")
        out.append(DatasetFact(
            name=f"Household spending: {label}", source="SingStat Household Expenditure Survey", table_id=HES_TABLE,
            url=url, period=HES_YEAR, value=value, unit="S$ per resident household per month",
            note="Average over all resident households, not per student or per visit" + share,
            quote=f"{name}, {HES_YEAR}: {value} ({row.get('uoM', 'Dollar')})", retrieved_at=retrieved_at))
    return out


def cpi_index(geography: str, client: httpx.Client | None = None, cache_dir: Path | None = None,
              ) -> PriceIndex | None:
    """The all-items consumer price index by year, as published. Singapore only."""
    if geography.strip().upper() not in SINGAPORE:
        return None
    data = fetch_table(CPI_TABLE, client, cache_dir)
    row = _row(data, "All Items") if data else None
    values = _series(row) if row else {}
    if len(values) < 2:
        return None
    return PriceIndex(name="Consumer Price Index, all items (2024 = 100)", table_id=CPI_TABLE,
                      url=BASE_URL.format(table_id=CPI_TABLE), retrieved_at=datetime.now(UTC).isoformat(),
                      values=values, source="SingStat")


def dataset_facts(pack: str, geography: str, client: httpx.Client | None = None,
                  cache_dir: Path | None = None) -> list[DatasetFact]:
    """Official facts for this pack. Singapore only (SingStat covers nothing else); anything unavailable is skipped."""
    if geography.strip().upper() not in SINGAPORE:
        return []
    now = datetime.now(UTC).isoformat()
    facts: list[DatasetFact] = []
    cpi = fetch_table(CPI_TABLE, client, cache_dir)
    if cpi:
        facts += cpi_facts(pack, cpi, now)
    hes = fetch_table(HES_TABLE, client, cache_dir)
    if hes:
        facts += hes_facts(pack, hes, now)
    return facts
