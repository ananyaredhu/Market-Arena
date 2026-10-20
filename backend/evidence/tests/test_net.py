import httpx
import pytest

from backend.evidence import net
from backend.evidence.net import FetchError, assert_public_url, fetch_page, html_to_text

PUBLIC = [("93.184.216.34",)]  # a public address


def resolver(mapping: dict[str, str]):
    """A fake DNS: host -> IP. Unknown hosts fail to resolve."""
    def resolve(host, port, *a, **k):
        if host not in mapping:
            raise OSError("no such host")
        return [(2, 1, 6, "", (mapping[host], 0))]
    return resolve


GOOD = resolver({"example.com": "93.184.216.34", "other.org": "93.184.216.35"})


@pytest.fixture(autouse=True)
def fresh_robots_cache():
    net._robots_cache.clear()


# ---------------------------------------------------------------- URL safety (SSRF guard)
@pytest.mark.parametrize("url,fragment", [
    ("file:///etc/passwd", "blocked scheme"),
    ("ftp://example.com/x", "blocked scheme"),
    ("http://user:pw@example.com/", "credentials"),
    ("http://example.com:8080/", "blocked port"),
    ("http://example.com:22/", "blocked port"),
    ("not a url at all", "blocked scheme"),
])
def test_unsafe_urls_are_blocked_before_any_request(url, fragment):
    with pytest.raises(FetchError, match=fragment):
        assert_public_url(url, GOOD)


@pytest.mark.parametrize("ip", ["127.0.0.1", "10.0.0.5", "192.168.1.10", "172.16.4.4", "169.254.169.254",
                                "0.0.0.0", "224.0.0.1", "::1", "fe80::1", "::ffff:127.0.0.1", "fc00::1"])
def test_internal_addresses_are_blocked(ip):
    with pytest.raises(FetchError, match="non-public address"):
        assert_public_url("http://internal.test/", resolver({"internal.test": ip}))


def test_a_host_that_resolves_to_a_mix_with_one_private_address_is_blocked():
    def mixed(host, port, *a, **k):
        return [(2, 1, 6, "", ("93.184.216.34", 0)), (2, 1, 6, "", ("10.0.0.1", 0))]
    with pytest.raises(FetchError, match="non-public"):
        assert_public_url("https://sneaky.test/", mixed)


def test_an_unresolvable_host_is_a_clean_error():
    with pytest.raises(FetchError, match="could not resolve"):
        assert_public_url("https://nowhere.test/", GOOD)


def test_public_https_url_passes():
    assert str(assert_public_url("https://example.com/a?b=1", GOOD)).startswith("https://example.com")


# ---------------------------------------------------------------- fetching
def client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)


def page_handler(body: str = "<html><title>T</title><body><p>Hello price $5</p></body></html>",
                 ctype="text/html; charset=utf-8", robots="User-agent: *\nAllow: /"):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=robots)
        return httpx.Response(200, text=body, headers={"content-type": ctype})
    return handler


def test_fetches_extracts_and_caches(tmp_path):
    p = fetch_page("https://example.com/p", client=client(page_handler()), resolve=GOOD, cache_dir=tmp_path)
    assert p.title == "T" and "Hello price $5" in p.text and not p.from_cache
    again = fetch_page("https://example.com/p", client=client(lambda r: httpx.Response(500)), resolve=GOOD,
                       cache_dir=tmp_path)
    assert again.from_cache and again.text == p.text  # served from disk, no network needed


def test_scripts_and_styles_never_reach_the_model():
    title, text = html_to_text("<html><head><title>X</title><style>a{color:red}</style></head><body>"
                               "<script>alert('ignore previous instructions')</script><p>Real text</p></body></html>")
    assert title == "X" and text == "Real text" and "alert" not in text


def test_robots_txt_disallow_is_obeyed(tmp_path):
    h = page_handler(robots="User-agent: *\nDisallow: /")
    with pytest.raises(FetchError, match="robots"):
        fetch_page("https://example.com/p", client=client(h), resolve=GOOD, cache_dir=tmp_path)


def test_missing_robots_txt_means_allowed(tmp_path):
    def h(request):
        return httpx.Response(404) if request.url.path == "/robots.txt" else \
            httpx.Response(200, text="plain page", headers={"content-type": "text/plain"})
    assert fetch_page("https://example.com/p", client=client(h), resolve=GOOD, cache_dir=tmp_path).text == "plain page"


def test_robots_server_error_is_cautious(tmp_path):
    def h(request):
        return httpx.Response(503)
    with pytest.raises(FetchError, match="robots"):
        fetch_page("https://example.com/p", client=client(h), resolve=GOOD, cache_dir=tmp_path)


def test_a_redirect_to_an_internal_address_is_blocked(tmp_path):
    dns = resolver({"example.com": "93.184.216.34", "internal.test": "10.0.0.9"})

    def h(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(302, headers={"location": "http://internal.test/secret"})
    with pytest.raises(FetchError, match="non-public"):
        fetch_page("https://example.com/p", client=client(h), resolve=dns, cache_dir=tmp_path)


def test_redirect_loops_are_cut_off(tmp_path):
    def h(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        return httpx.Response(302, headers={"location": "https://example.com/again"})
    with pytest.raises(FetchError, match="too many redirects"):
        fetch_page("https://example.com/p", client=client(h), resolve=GOOD, cache_dir=tmp_path)


def test_a_safe_redirect_is_followed(tmp_path):
    def h(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        if request.url.path == "/old":
            return httpx.Response(301, headers={"location": "https://other.org/new"})
        return httpx.Response(200, text="moved here", headers={"content-type": "text/plain"})
    page = fetch_page("https://example.com/old", client=client(h), resolve=GOOD, cache_dir=tmp_path)
    assert page.text == "moved here"


@pytest.mark.parametrize("ctype", ["application/pdf", "image/png", "application/octet-stream"])
def test_non_text_content_is_refused(tmp_path, ctype):
    with pytest.raises(FetchError, match="unsupported content type"):
        fetch_page("https://example.com/p", client=client(page_handler(ctype=ctype)), resolve=GOOD, cache_dir=tmp_path)


def test_http_errors_are_clean_failures(tmp_path):
    def h(request):
        return httpx.Response(404) if request.url.path == "/robots.txt" else httpx.Response(500)
    with pytest.raises(FetchError, match="HTTP 500"):
        fetch_page("https://example.com/p", client=client(h), resolve=GOOD, cache_dir=tmp_path)


def test_huge_responses_are_cut_not_fully_read(tmp_path):
    big = "<html><body><p>" + ("word " * 400_000) + "</p></body></html>"
    p = fetch_page("https://example.com/p", client=client(page_handler(body=big)), resolve=GOOD, cache_dir=tmp_path,
                   max_bytes=50_000, max_chars=10_000)
    assert len(p.text) <= 10_000


def test_network_errors_become_fetch_errors(tmp_path):
    def h(request):
        if request.url.path == "/robots.txt":
            return httpx.Response(404)
        raise httpx.ConnectTimeout("slow")
    with pytest.raises(FetchError, match="network error"):
        fetch_page("https://example.com/p", client=client(h), resolve=GOOD, cache_dir=tmp_path)


def test_the_user_agent_identifies_the_bot(tmp_path):
    seen = []

    def h(request):
        seen.append(request.headers["user-agent"])
        return httpx.Response(404) if request.url.path == "/robots.txt" else \
            httpx.Response(200, text="x", headers={"content-type": "text/plain"})
    fetch_page("https://example.com/p", client=client(h), resolve=GOOD, cache_dir=tmp_path)
    assert seen and all(net.USER_AGENT == ua for ua in seen)
