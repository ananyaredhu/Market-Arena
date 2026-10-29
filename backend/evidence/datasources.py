"""Small shared helper for the official-statistics connectors (Person A): fetch once, cache on disk for 30 days.

A failed fetch returns None and the caller carries on without that dataset; nothing here ever invents a value.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import httpx

from backend.common import llm

USER_AGENT = "MarketArenaResearchBot/0.1 (student project; evidence research)"
CACHE_TTL = 30 * 24 * 3600


def cached_get(url: str, params: dict | list[tuple[str, str]] | None, folder: str, client: httpx.Client | None = None,
               cache_dir: Path | None = None, as_json: bool = True):
    """The response body (parsed JSON, or text), or None when unavailable. Cached 30 days per url and parameters."""
    key = hashlib.blake2b(json.dumps([url, params], sort_keys=True, default=str).encode(), digest_size=8).hexdigest()
    f = (cache_dir or (llm.CACHE_DIR / "evidence" / folder)) / f"{key}.json"
    if f.exists():
        cached = json.loads(f.read_text())
        if time.time() - cached["fetched_at"] < CACHE_TTL:
            return cached["body"]
    own = client is None
    client = client or httpx.Client(timeout=30.0, headers={"User-Agent": USER_AGENT})
    try:
        r = client.get(url, params=params)
        if r.status_code != 200:
            return None
        body = r.json() if as_json else r.text
    except (httpx.HTTPError, ValueError):
        return None
    finally:
        if own:
            client.close()
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"fetched_at": time.time(), "body": body}))
    return body
