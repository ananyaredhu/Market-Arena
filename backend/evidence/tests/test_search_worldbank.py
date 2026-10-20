
import httpx
import pytest

from backend.evidence.search import NullSearch, SearchError, SearxngSearch, get_provider
from backend.evidence.worldbank import budget_scale, country_economics, fetch_gdp


def mock(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


# ---------------------------------------------------------------- SearXNG
def test_searxng_request_and_parsing():
    seen = {}

    def h(request: httpx.Request):
        seen["url"], seen["params"] = request.url.path, dict(request.url.params)
        return httpx.Response(200, json={"results": [
            {"title": "Pricing", "url": "https://a.com/p", "content": "Premium is $4.99"},
            {"title": "dup", "url": "https://a.com/p", "content": "again"},
            {"title": "no url", "content": "x"},
            {"title": "Other", "url": "https://b.com/q", "content": "y"}]})
    hits = SearxngSearch("http://localhost:8888/", client=mock(h)).search("studyflow pricing", max_results=5)
    assert seen["url"] == "/search" and seen["params"]["q"] == "studyflow pricing"
    assert seen["params"]["format"] == "json"
    assert [(x.title, x.url, x.snippet) for x in hits] == [
        ("Pricing", "https://a.com/p", "Premium is $4.99"), ("Other", "https://b.com/q", "y")]


@pytest.mark.parametrize("status,fragment", [(403, "json format"), (429, "rate limit"), (500, "HTTP 500")])
def test_searxng_errors_are_clean(status, fragment):
    with pytest.raises(SearchError, match=fragment):
        SearxngSearch("http://x", client=mock(lambda r: httpx.Response(status))).search("q")


def test_searxng_unreachable_and_bad_json_are_clean():
    def boom(request):
        raise httpx.ConnectError("refused")
    with pytest.raises(SearchError, match="is SearXNG running"):
        SearxngSearch("http://x", client=mock(boom)).search("q")
    with pytest.raises(SearchError, match="not JSON"):
        SearxngSearch("http://x", client=mock(lambda r: httpx.Response(200, text="<html>"))).search("q")


def test_max_results_is_bounded():
    rows = [{"title": str(i), "url": f"https://a.com/{i}", "content": ""} for i in range(30)]
    s = SearxngSearch("http://x", client=mock(lambda r: httpx.Response(200, json={"results": rows})))
    assert len(s.search("q", max_results=500)) == 10 and len(s.search("q", max_results=0)) == 1


def test_provider_selection(monkeypatch):
    monkeypatch.delenv("SEARXNG_URL", raising=False)
    assert isinstance(get_provider(), NullSearch) and NullSearch().search("x") == []
    monkeypatch.setenv("SEARXNG_URL", "http://localhost:8888")
    assert get_provider().name == "searxng"
    monkeypatch.setenv("SEARCH_PROVIDER", "none")
    assert isinstance(get_provider(), NullSearch)


# ---------------------------------------------------------------- World Bank
def wb_handler(values: dict[str, float]):
    def h(request: httpx.Request):
        iso = request.url.path.split("/")[3]
        if iso not in values:
            return httpx.Response(200, json=[{"message": [{"id": "120", "key": "Invalid value"}]}])
        return httpx.Response(200, json=[{"page": 1}, [{"country": {"value": iso + "land"}, "date": "2025",
                                                       "value": values[iso]}]])
    return h


def test_country_economics_scales_budgets(tmp_path):
    c = mock(wb_handler({"SG": 160000.0, "IN": 10000.0}))
    e = country_economics("in", client=c, cache_dir=tmp_path)
    assert e.iso == "IN" and e.baseline_iso == "SG" and e.year == 2025
    assert e.budget_scale == pytest.approx(0.25, abs=0.001)  # sqrt(10000/160000) = 0.25
    assert "worldbank.org" in e.source_url


def test_the_baseline_country_scales_by_one(tmp_path):
    assert country_economics("SG", client=mock(wb_handler({"SG": 160000.0})), cache_dir=tmp_path).budget_scale == 1.0


def test_scale_is_bounded_both_ways():
    assert budget_scale(1, 1_000_000) == 0.25 and budget_scale(1_000_000, 1) == 2.0
    assert budget_scale(0, 100) == 1.0 and budget_scale(100, 0) == 1.0


def test_unknown_country_or_outage_returns_none_not_an_error(tmp_path):
    assert country_economics("ZZ", client=mock(wb_handler({"SG": 1.0})), cache_dir=tmp_path) is None
    assert fetch_gdp("US", client=mock(lambda r: httpx.Response(503)), cache_dir=tmp_path) is None

    def boom(request):
        raise httpx.ConnectError("down")
    assert fetch_gdp("US", client=mock(boom), cache_dir=tmp_path) is None
    assert fetch_gdp("not-a-code", client=mock(wb_handler({})), cache_dir=tmp_path) is None


def test_results_are_cached_so_a_repeat_needs_no_network(tmp_path):
    fetch_gdp("SG", client=mock(wb_handler({"SG": 160000.0})), cache_dir=tmp_path)
    again = fetch_gdp("SG", client=mock(lambda r: httpx.Response(500)), cache_dir=tmp_path)
    assert again["value"] == 160000.0
