"""Official European statistics from Eurostat's dissemination API (Person A). Free, no key.

Two real datasets, for the EU countries (plus Norway, Iceland, Switzerland and the UK, which Eurostat also publishes):

  * Harmonised consumer prices (prc_hicp_aind, annual average index, all items). Kept whole in the snapshot
    (`price_index`) and moves every budget by the FULL measured change from a starting year to the latest year, exactly
    as the Singapore index does (see apply.py): no cap, no skipping.
  * ICT use by individuals (isoc_ec_ibgs): the share of individuals who paid for apps or software in the last three
    months. Shown only. It counts every individual of every age, not students, so setting a segment's budget or
    a free-tool share from it would be a guess presented as data.

A failed fetch returns nothing and nothing else changes.
"""
from __future__ import annotations

from datetime import UTC, datetime
from itertools import product
from pathlib import Path

import httpx

from backend.evidence.datasources import cached_get
from backend.evidence.models import DatasetFact, PriceIndex

BASE = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{dataset}"
PAGE = "https://ec.europa.eu/eurostat/databrowser/view/{dataset}/default/table"
HICP, ICT = "prc_hicp_aind", "isoc_ec_ibgs"

# ISO 3166 alpha-3 and alpha-2 to Eurostat's geo codes (Greece is EL, the UK is UK).
_ISO2 = ("AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE IS NO CH GB").split()
_ISO3 = ("AUT BEL BGR HRV CYP CZE DNK EST FIN FRA DEU GRC HUN IRL ITA LVA LTU LUX MLT NLD POL PRT ROU SVK SVN ESP "
         "SWE ISL NOR CHE GBR").split()
_GEO = {**dict(zip(_ISO2, _ISO2, strict=True)), **dict(zip(_ISO3, _ISO2, strict=True))}
_GEO.update({"GR": "EL", "GRC": "EL", "GB": "UK", "GBR": "UK"})

# What to show per pack: (indicator code, label). Only the app and software measures that match the SaaS pack.
ICT_ROWS = {
    "saas": [("I_BAPP2", "Paid subscription to other apps (for example language learning, travel, weather)"),
             ("I_BHLFTS2", "Paid subscription to a health or fitness app"),
             ("I_BSOFT2", "Software bought as a download")],
    "cafe": [],
}


def geo_code(geography: str) -> str | None:
    return _GEO.get(geography.strip().upper())


def _cells(d: dict) -> list[tuple[dict[str, str], float]]:
    """Every value of a JSON-stat result with the category code of each dimension, in the API's own order."""
    ids, sizes = d["id"], d["size"]
    cats = [sorted(d["dimension"][i]["category"]["index"], key=d["dimension"][i]["category"]["index"].get) for i in ids]
    out = []
    for flat, combo in enumerate(product(*[range(n) for n in sizes])):
        v = d.get("value", {}).get(str(flat))
        if v is not None:
            out.append(({i: cats[k][c] for k, (i, c) in enumerate(zip(ids, combo, strict=True))}, float(v)))
    return out


def _fetch(dataset: str, params: list[tuple[str, str]], client, cache_dir) -> dict | None:
    d = cached_get(BASE.format(dataset=dataset), [("format", "JSON"), ("lang", "EN"), *params], "eurostat",
                   client, cache_dir)
    return d if isinstance(d, dict) and "value" in d and "dimension" in d else None


def cpi_index(geography: str, client: httpx.Client | None = None, cache_dir: Path | None = None) -> PriceIndex | None:
    """The all-items harmonised consumer price index by year, as published."""
    geo = geo_code(geography)
    if geo is None:
        return None
    d = _fetch(HICP, [("unit", "INX_A_AVG"), ("coicop", "CP00"), ("geo", geo)], client, cache_dir)
    values = {c["time"]: v for c, v in _cells(d)} if d else {}
    if len(values) < 2:
        return None
    return PriceIndex(name="Harmonised consumer price index, all items (2015 = 100)", table_id=HICP,
                      url=PAGE.format(dataset=HICP), retrieved_at=datetime.now(UTC).isoformat(), values=values,
                      source="Eurostat")


def dataset_facts(pack: str, geography: str, client: httpx.Client | None = None,
                  cache_dir: Path | None = None) -> list[DatasetFact]:
    """App and software spending shares for this pack and country; anything unavailable is skipped."""
    geo, rows = geo_code(geography), ICT_ROWS.get(pack, [])
    if geo is None or not rows:
        return []
    d = _fetch(ICT, [("unit", "PC_IND"), ("ind_type", "IND_TOTAL"), ("geo", geo),
                     *[("indic_is", code) for code, _ in rows]], client, cache_dir)
    if not d:
        return []
    now = datetime.now(UTC).isoformat()
    out = []
    for code, label in rows:
        series = {c["time"]: v for c, v in _cells(d) if c["indic_is"] == code}
        if not series:
            continue
        year = max(series, key=int)
        out.append(DatasetFact(
            name=f"Paying for apps: {label}", source="Eurostat ICT use by individuals", table_id=ICT,
            url=PAGE.format(dataset=ICT), period=year, value=series[year], unit="% of individuals, last 3 months",
            note=f"Share of all individuals in {geo}, any age, not students; shown as reference, never used as a prior",
            quote=f"{code}, {geo}, {year}: {series[year]} (PC_IND)", retrieved_at=now))
    return out
