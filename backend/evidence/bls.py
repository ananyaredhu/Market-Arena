"""US consumer prices from the Bureau of Labor Statistics (Person A). Free, no key.

BLS's own key-free API returns only the latest three years, so the history comes from the St. Louis Fed's FRED
download, which republishes the same BLS series (CPI for All Urban Consumers, not seasonally adjusted) with the full
history. The two agree on every month checked.

  * All-items CPI-U as a yearly average, kept whole in the snapshot (`price_index`). It moves every
    budget by the FULL measured change from a starting year to the latest year, as the other price indices do.
  * The categories that match the pack, with the change on last year and over five years, are shown as facts.

BLS's household spending tables (Consumer Expenditure Survey) are not read: they are not served through a key-free API,
and, like Singapore's, they are per household, so they would only ever be shown.
"""
from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from pathlib import Path

import httpx

from backend.evidence.datasources import cached_get
from backend.evidence.models import DatasetFact, PriceIndex

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv"
FRED_PAGE = "https://fred.stlouisfed.org/series/{series}"
ALL_ITEMS = "CPIAUCNS"  # CPI-U, all items, not seasonally adjusted (BLS series CUUR0000SA0)
CATEGORIES = {  # series id -> label, per pack
    "saas": {"CUUR0000SEEE": "Information technology, hardware and services"},
    "cafe": {"CUUR0000SEFV": "Food away from home"},
}
US = ("US", "USA")


def _annual(series: str, client, cache_dir) -> dict[str, float]:
    """Yearly average over the published months of years with at least 11 of 12.

    11 is allowed because BLS never collected October 2025 (the federal shutdown); its own 2025 annual average
    (321.943) is exactly the mean of the other 11 months, so this matches what BLS publishes.
    """
    text = cached_get(FRED_CSV, {"id": series, "cosd": "1990-01-01"}, "bls", client, cache_dir, as_json=False)
    if not isinstance(text, str):
        return {}
    months: dict[str, list[float]] = {}
    for row in csv.DictReader(io.StringIO(text)):
        try:
            months.setdefault(row["observation_date"][:4], []).append(float(row[series]))
        except (KeyError, ValueError):
            continue  # a blank month (".") or a malformed line is left out of its year
    return {y: round(sum(v) / len(v), 3) for y, v in months.items() if len(v) >= 11}


def _pct(new: float, old: float) -> float:
    return (new / old - 1) * 100


def cpi_index(geography: str, client: httpx.Client | None = None, cache_dir: Path | None = None) -> PriceIndex | None:
    if geography.strip().upper() not in US:
        return None
    values = _annual(ALL_ITEMS, client, cache_dir)
    if len(values) < 2:
        return None
    return PriceIndex(name="Consumer Price Index for All Urban Consumers, all items (1982-84 = 100)",
                      table_id=ALL_ITEMS, url=FRED_PAGE.format(series=ALL_ITEMS),
                      retrieved_at=datetime.now(UTC).isoformat(), values=values, source="US Bureau of Labor Statistics")


def dataset_facts(pack: str, geography: str, client: httpx.Client | None = None,
                  cache_dir: Path | None = None) -> list[DatasetFact]:
    if geography.strip().upper() not in US:
        return []
    now = datetime.now(UTC).isoformat()
    out = []
    for series, label in {ALL_ITEMS: "All items", **CATEGORIES.get(pack, {})}.items():
        values = _annual(series, client, cache_dir)
        if len(values) < 2:
            continue
        year = max(values, key=int)
        one, five = values.get(str(int(year) - 1)), values.get(str(int(year) - 5))
        parts = [f"{_pct(values[year], one):+.1f}% on {int(year) - 1}" if one else None,
                 f"{_pct(values[year], five):+.1f}% over 5 years" if five else None]
        out.append(DatasetFact(
            name=f"Consumer prices: {label}", source="US Bureau of Labor Statistics (CPI-U, via FRED)",
            table_id=series, url=FRED_PAGE.format(series=series), period=year, value=values[year],
            unit="index, yearly average", note=", ".join(p for p in parts if p) or "no earlier year to compare",
            quote=f"{label}, {year} yearly average: {values[year]} (index)", retrieved_at=now))
    return out
