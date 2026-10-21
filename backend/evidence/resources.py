"""The Resources library: surveys, news and competitor pages the researcher read, kept for people to read (Person A).

Nothing in here ever changes a simulation prior (see apply.py: only real datasets do). Each entry keeps the verbatim
quote that was verified against the page, the url, and when it was retrieved, so the user can check it and the
Council can cite it as labelled reference. Entries from every research run accumulate per pack and geography in
data/resources/ and are deduplicated by (url, quote).
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


def _id(url: str, quote: str) -> str:
    return hashlib.blake2b(f"{url}\n{quote}".encode(), digest_size=6).hexdigest()


def _file(directory: Path, pack: str, geography: str) -> Path:
    return directory / f"{_SAFE.sub('_', pack)}_{_SAFE.sub('_', geography)}.json"


def from_snapshot(snap: EvidenceSnapshot) -> list[Resource]:
    items = [
        Resource(id=_id(f.url, f.quote), topic=TOPIC_OF_KIND.get(f.kind, "general"), claim=f.claim, quote=f.quote,
                 url=f.url, domain=_domain(f.url), pack=snap.pack, geography=snap.geography,
                 retrieved_at=snap.created_at, snapshot_id=snap.snapshot_id, value=f.value, low=f.low, high=f.high,
                 unit=f.unit, currency=f.currency)
        for f in snap.findings
    ]
    items += [
        Resource(id=_id(n.url, n.quote), topic="trends", claim=n.note, quote=n.quote, url=n.url,
                 domain=_domain(n.url), pack=snap.pack, geography=snap.geography, retrieved_at=snap.created_at,
                 snapshot_id=snap.snapshot_id)
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
