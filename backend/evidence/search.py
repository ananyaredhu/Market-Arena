"""Web search providers for the evidence researcher (Person A).

The researcher talks to a `SearchProvider`, so the engine can be swapped without touching the agent. The default is
SearXNG: free, open-source, no account and no API key. It is a metasearch engine you run yourself
(`make search-up` starts it in Docker on http://localhost:8888, see infra/searxng/) and it must have the JSON output
format enabled, which our settings.yml does. Set SEARXNG_URL in .env to enable live search.

With no SEARXNG_URL (or SEARCH_PROVIDER=none) the provider is `NullSearch` and the researcher reports "no search
available", so the original priors run unchanged.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

import httpx


class SearchError(RuntimeError):
    """The search call failed (bad key, quota used up, network). The researcher falls back, never crashes."""


@dataclass
class SearchHit:
    title: str
    url: str
    snippet: str  # the provider's extract of the page: treated as a source text the model may quote from


class SearchProvider(Protocol):
    name: str

    def search(self, query: str, max_results: int = 5) -> list[SearchHit]: ...


class NullSearch:
    name = "none"

    def search(self, query: str, max_results: int = 5) -> list[SearchHit]:
        return []


class SearxngSearch:
    """Queries a SearXNG instance: GET <base>/search?q=...&format=json -> {"results": [{title, url, content}]}."""

    name = "searxng"

    def __init__(self, base_url: str, client: httpx.Client | None = None, timeout: float = 20.0):
        self._base = base_url.rstrip("/")
        self._client = client
        self._timeout = timeout

    def search(self, query: str, max_results: int = 5) -> list[SearchHit]:
        limit = max(1, min(max_results, 10))
        client = self._client or httpx.Client(timeout=self._timeout)
        try:
            r = client.get(f"{self._base}/search", params={"q": query, "format": "json", "safesearch": 1})
        except httpx.HTTPError as e:
            raise SearchError(f"search is not reachable at {self._base} ({type(e).__name__}); is SearXNG running?") \
                from e
        finally:
            if self._client is None:
                client.close()
        if r.status_code == 403:
            raise SearchError("SearXNG refused the request: enable the json format in settings.yml (search.formats)")
        if r.status_code == 429:
            raise SearchError("SearXNG rate limit reached (limiter should be off for a local instance)")
        if r.status_code >= 400:
            raise SearchError(f"search failed with HTTP {r.status_code}")
        try:
            results = r.json().get("results", [])
        except ValueError as e:
            raise SearchError("search returned something that is not JSON") from e
        seen: set[str] = set()
        hits = []
        for x in results:
            url = x.get("url")
            if url and url not in seen:
                seen.add(url)
                hits.append(SearchHit(title=x.get("title", ""), url=url, snippet=x.get("content", "")))
        return hits[:limit]


def get_provider() -> SearchProvider:
    """SEARXNG_URL set (and SEARCH_PROVIDER not "none") -> SearXNG; otherwise no search."""
    url = os.getenv("SEARXNG_URL", "").strip()
    if os.getenv("SEARCH_PROVIDER", "searxng") == "none" or not url:
        return NullSearch()
    return SearxngSearch(url)
