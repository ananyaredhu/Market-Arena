"""Safe page fetching for the evidence researcher (Person A).

The model chooses which pages to open, and page text is untrusted, so every fetch goes through these guards:
  * only http/https on the standard ports, no credentials in the URL
  * the host must resolve to PUBLIC addresses only (no localhost, private ranges, link-local/cloud metadata)
  * redirects are followed by hand (at most 3) and every hop is checked again
  * robots.txt is obeyed, with an identifying User-Agent
  * response size is capped; only text-like content types are read
  * results are cached on disk, so repeats are fast and a demo can run from cache
The caller (agent.py) adds one more rule: only URLs that appeared in search results may be opened at all.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import socket
import time
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib import robotparser

import httpx

from backend.common import llm

USER_AGENT = "MarketArenaResearchBot/0.1 (student project; evidence research; respects robots.txt)"
ALLOWED_PORTS = (None, 80, 443)
TEXT_TYPES = ("text/html", "application/xhtml+xml", "text/plain", "application/json")
MAX_REDIRECTS = 3
CACHE_TTL = 7 * 24 * 3600

Resolver = type(socket.getaddrinfo)


class FetchError(RuntimeError):
    """The page was not fetched. The message says why (blocked, too large, wrong type, network ...)."""


@dataclass
class Page:
    url: str
    title: str
    text: str
    fetched_at: float
    from_cache: bool = False


# ---------------------------------------------------------------- URL safety
def assert_public_url(url: str, resolve=socket.getaddrinfo) -> httpx.URL:
    """Raise FetchError unless `url` is a plain http(s) URL whose host resolves only to public addresses."""
    try:
        u = httpx.URL(url)
    except Exception as e:  # noqa: BLE001
        raise FetchError(f"not a valid URL: {url[:80]}") from e
    if u.scheme not in ("http", "https"):
        raise FetchError(f"blocked scheme '{u.scheme}' (only http and https are allowed)")
    if not u.host:
        raise FetchError("URL has no host")
    if u.userinfo:
        raise FetchError("blocked: credentials in the URL")
    if u.port not in ALLOWED_PORTS:
        raise FetchError(f"blocked port {u.port} (only 80 and 443 are allowed)")
    try:
        ips = {info[4][0] for info in resolve(u.host, None)}
    except OSError as e:
        raise FetchError(f"could not resolve {u.host}") from e
    if not ips:
        raise FetchError(f"could not resolve {u.host}")
    for raw in ips:
        ip = ipaddress.ip_address(raw.split("%")[0])
        ip = getattr(ip, "ipv4_mapped", None) or ip  # ::ffff:127.0.0.1 is still loopback
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved
                or ip.is_unspecified):
            raise FetchError(f"blocked: {u.host} resolves to a non-public address ({ip})")
    return u


# ---------------------------------------------------------------- html to text
class _Extract(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "template", "head"}
    BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "table",
             "ul", "ol", "header", "footer"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.title = ""
        self._skip = 0
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        if tag in self.SKIP and tag != "head":
            self._skip += 1
        if tag in self.BLOCK:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag in self.SKIP and tag != "head" and self._skip:
            self._skip -= 1
        if tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        elif not self._skip:
            self.parts.append(data)


def html_to_text(html: str) -> tuple[str, str]:
    p = _Extract()
    p.feed(html)
    text = "\n".join(line.strip() for line in "".join(p.parts).splitlines() if line.strip())
    return p.title.strip(), text


# ---------------------------------------------------------------- cache
def _cache_file(url: str, cache_dir: Path | None) -> Path:
    base = cache_dir or (llm.CACHE_DIR / "evidence" / "pages")
    return base / f"{hashlib.sha256(url.encode()).hexdigest()[:24]}.json"


def _read_cache(url: str, cache_dir: Path | None) -> Page | None:
    f = _cache_file(url, cache_dir)
    if not f.exists():
        return None
    d = json.loads(f.read_text())
    if time.time() - d["fetched_at"] > CACHE_TTL:
        return None
    return Page(d["url"], d["title"], d["text"], d["fetched_at"], from_cache=True)


def _write_cache(page: Page, cache_dir: Path | None) -> None:
    f = _cache_file(page.url, cache_dir)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"url": page.url, "title": page.title, "text": page.text, "fetched_at": page.fetched_at}))


# ---------------------------------------------------------------- fetching
def _get(client: httpx.Client, url: str, resolve, max_bytes: int) -> tuple[httpx.Response, bytes]:
    """GET with manual, re-validated redirects and a hard size cap."""
    for _hop in range(MAX_REDIRECTS + 1):
        assert_public_url(url, resolve)
        with client.stream("GET", url, headers={"User-Agent": USER_AGENT}) as r:
            if r.is_redirect and r.headers.get("location"):
                url = str(httpx.URL(url).join(r.headers["location"]))
                continue
            body = b""
            for chunk in r.iter_bytes():
                body += chunk
                if len(body) >= max_bytes:
                    body = body[:max_bytes]  # too large: use the beginning, never the whole file
                    break
            return r, body
    raise FetchError("too many redirects")


_robots_cache: dict[str, robotparser.RobotFileParser | None] = {}


def _robots_allow(client: httpx.Client, url: str, resolve) -> bool:
    u = httpx.URL(url)
    origin = f"{u.scheme}://{u.host}"
    if origin not in _robots_cache:
        rp = robotparser.RobotFileParser()
        try:
            r, body = _get(client, f"{origin}/robots.txt", resolve, 100_000)
        except FetchError:
            raise
        except httpx.HTTPError as e:
            raise FetchError(f"could not read robots.txt for {u.host}: {type(e).__name__}") from e
        if r.status_code >= 500:
            _robots_cache[origin] = None  # server trouble: be cautious, do not fetch
        elif r.status_code >= 400:
            rp.parse([])  # no robots.txt: everything allowed
            _robots_cache[origin] = rp
        else:
            rp.parse(body.decode("utf-8", errors="replace").splitlines())
            _robots_cache[origin] = rp
    rp = _robots_cache[origin]
    return bool(rp and rp.can_fetch(USER_AGENT, url))


def fetch_page(
    url: str,
    *,
    client: httpx.Client | None = None,
    resolve=socket.getaddrinfo,
    cache_dir: Path | None = None,
    max_bytes: int = 1_500_000,
    max_chars: int = 30_000,
    timeout: float = 10.0,
    use_robots: bool = True,
) -> Page:
    cached = _read_cache(url, cache_dir)
    if cached:
        return cached
    own = client is None
    client = client or httpx.Client(timeout=timeout, follow_redirects=False)
    try:
        assert_public_url(url, resolve)
        if use_robots and not _robots_allow(client, url, resolve):
            raise FetchError("blocked by robots.txt")
        try:
            r, body = _get(client, url, resolve, max_bytes)
        except httpx.HTTPError as e:
            raise FetchError(f"network error: {type(e).__name__}") from e
        if r.status_code >= 400:
            raise FetchError(f"HTTP {r.status_code}")
        ctype = r.headers.get("content-type", "").split(";")[0].strip().lower()
        if ctype not in TEXT_TYPES:
            raise FetchError(f"unsupported content type '{ctype or 'unknown'}'")
        html = body.decode(r.encoding or "utf-8", errors="replace")
        title, text = html_to_text(html) if ctype != "text/plain" and ctype != "application/json" else ("", html)
        page = Page(url, title, text[:max_chars], time.time())
        _write_cache(page, cache_dir)
        return page
    finally:
        if own:
            client.close()
