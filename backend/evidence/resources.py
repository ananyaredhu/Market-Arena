"""The Resources library: surveys, news and competitor pages the researcher read, kept for people to read (Person A).

Nothing in here changes a simulation prior (see apply.py: only the country-income dataset does). Each entry keeps the
verbatim quote that was verified against the page (or, for official statistics, the row as the API returned it), the
url, and when it was retrieved, so the user can check it and the Council can cite it as labelled reference. Entries
from every research run accumulate per pack and geography in data/resources/ and are deduplicated by (url, quote).
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse

from pydantic import BaseModel

from backend.evidence.models import EvidenceSnapshot

_SAFE = re.compile(r"[^A-Za-z0-9_-]+")

TOPIC_OF_KIND = {
    "competitor_price": "competitor prices",
    "segment_budget": "spending",
    "free_tool_adoption": "free alternatives",
    "market_size": "market size",
    "regulation": "regulation",
    "channel": "channels",
    "other": "general",
}


class Resource(BaseModel):
    id: str
    kind: str = "page"  # "page" (read from a web page by the researcher) or "dataset" (official statistics via an API)
    topic: str
    claim: str
    quote: str
    url: str
    domain: str
    pack: str
    geography: str
    retrieved_at: str
    snapshot_id: str
    value: float | None = None
    low: float | None = None
    high: float | None = None
    unit: str | None = None
    currency: str | None = None


def _domain(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _id(pack: str, geography: str, url: str, quote: str) -> str:
    """Stable id of a quote within a pack and geography: the same page can serve two packs, as two entries."""
    return hashlib.blake2b(f"{pack}\n{geography}\n{url}\n{quote}".encode(), digest_size=6).hexdigest()


def _file(directory: Path, pack: str, geography: str) -> Path:
    return directory / f"{_SAFE.sub('_', pack)}_{_SAFE.sub('_', geography)}.json"


def from_snapshot(snap: EvidenceSnapshot) -> list[Resource]:
    where = dict(pack=snap.pack, geography=snap.geography, snapshot_id=snap.snapshot_id)

    def key(url: str, quote: str) -> str:
        return _id(snap.pack, snap.geography, url, quote)

    items = [
        Resource(id=key(f.url, f.quote), topic=TOPIC_OF_KIND.get(f.kind, "general"), claim=f.claim, quote=f.quote,
                 url=f.url, domain=_domain(f.url), retrieved_at=snap.created_at, value=f.value, low=f.low,
                 high=f.high, unit=f.unit, currency=f.currency, **where)
        for f in snap.findings
    ]
    items += [
        Resource(id=key(d.url, d.quote), kind="dataset", topic="official data", claim=f"{d.name}: {d.note}",
                 quote=d.quote, url=d.url, domain=_domain(d.url), retrieved_at=d.retrieved_at, value=d.value,
                 unit=d.unit, **where)
        for d in snap.datasets
    ]
    items += [
        Resource(id=key(n.url, n.quote), topic="trends", claim=n.note, quote=n.quote, url=n.url,
                 domain=_domain(n.url), retrieved_at=snap.created_at, **where)
        for n in snap.trend_notes
    ]
    return items


def _read(path: Path) -> list[Resource]:
    try:
        return [Resource.model_validate(x) for x in json.loads(path.read_text())]
    except (OSError, ValueError):
        return []


def add(snap: EvidenceSnapshot, directory: Path) -> int:
    """Add a snapshot's findings and trend notes to the library. Returns how many were new."""
    new = from_snapshot(snap)
    if not new:
        return 0
    path = _file(directory, snap.pack, snap.geography)
    have = _read(path)
    seen = {r.id for r in have}
    fresh = [r for r in new if r.id not in seen and not seen.add(r.id)]
    if fresh:
        directory.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps([r.model_dump() for r in have + fresh], indent=2))
    return len(fresh)


def list_resources(directory: Path, pack: str | None = None, geography: str | None = None,
                   topic: str | None = None, q: str | None = None) -> list[Resource]:
    """Newest first. `q` matches the claim, quote or website."""
    out: list[Resource] = []
    for path in sorted(directory.glob("*.json")) if directory.is_dir() else []:
        out += [r for r in _read(path)
                if (pack is None or r.pack == pack) and (geography is None or r.geography == geography)
                and (topic is None or r.topic == topic)]
    if q:
        needle = q.lower()
        out = [r for r in out if needle in f"{r.claim} {r.quote} {r.domain}".lower()]
    return sorted(out, key=lambda r: r.retrieved_at, reverse=True)
