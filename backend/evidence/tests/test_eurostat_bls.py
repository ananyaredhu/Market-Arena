import httpx

from backend.evidence import bls, eurostat
from backend.evidence.apply import apply_evidence
from backend.evidence.models import EvidenceSnapshot
from backend.population.packs import load_pack


def jsonstat(dims: dict[str, list[str]], values: dict[int, float]) -> dict:
    return {"id": list(dims), "size": [len(v) for v in dims.values()],
            "dimension": {k: {"category": {"index": {c: i for i, c in enumerate(v)}}} for k, v in dims.items()},
            "value": {str(k): v for k, v in values.items()}}


HICP = jsonstat({"freq": ["A"], "unit": ["INX_A_AVG"], "coicop": ["CP00"], "geo": ["DE"],
                 "time": ["2022", "2023", "2024", "2025"]}, {0: 117.0, 1: 125.9, 2: 129.0, 3: 131.9})
# two indicators x two years; the last year of one indicator is missing and must be skipped, not guessed
ICT = jsonstat({"freq": ["A"], "ind_type": ["IND_TOTAL"], "indic_is": ["I_BAPP2", "I_BHLFTS2", "I_BSOFT2"],
                "unit": ["PC_IND"], "geo": ["DE"], "time": ["2024", "2025"]},
               {0: 8.0, 1: 9.69, 2: 6.0, 4: 11.0, 5: 12.71})


def eu_client(calls=None):
    def handler(request):
        if calls is not None:
            calls.append(str(request.url))
        if "prc_hicp_aind" in str(request.url):
            return httpx.Response(200, json=HICP)
        if "isoc_ec_ibgs" in str(request.url):
            return httpx.Response(200, json=ICT)
        return httpx.Response(404)
    return httpx.Client(transport=httpx.MockTransport(handler))


def months(year, value, skip=()):
    return [f"{year}-{m:02d}-01,{'' if m in skip else value}" for m in range(1, 13)]


def fred_text(series, spec):
    return "\n".join([f"observation_date,{series}", *[line for y, v, skip in spec for line in months(y, v, skip)]])


def fred_client(texts, calls=None):
    def handler(request):
        if calls is not None:
            calls.append(str(request.url))
        sid = request.url.params.get("id")
        return httpx.Response(200, text=texts[sid]) if sid in texts else httpx.Response(404)
    return httpx.Client(transport=httpx.MockTransport(handler))


# ------------------------------------------------------------------------------------------------ Eurostat
def test_eurostat_price_index_is_kept_whole_by_year(tmp_path):
    pi = eurostat.cpi_index("DE", eu_client(), tmp_path)
    assert pi.source == "Eurostat" and pi.values == {"2022": 117.0, "2023": 125.9, "2024": 129.0, "2025": 131.9}
    assert pi.table_id == "prc_hicp_aind"


def test_eurostat_accepts_two_and_three_letter_codes_and_only_europe(tmp_path):
    assert eurostat.geo_code("DEU") == "DE" and eurostat.geo_code("gr") == "EL" and eurostat.geo_code("GBR") == "UK"
    assert eurostat.cpi_index("SG", eu_client(), tmp_path) is None
    assert eurostat.dataset_facts("saas", "US", eu_client(), tmp_path) == []


def test_eurostat_app_spending_is_shown_as_reference_and_skips_what_is_missing(tmp_path):
    facts = eurostat.dataset_facts("saas", "DE", eu_client(), tmp_path)
    by = {f.quote.split(",")[0]: f for f in facts}
    assert by["I_BAPP2"].value == 9.69 and by["I_BAPP2"].period == "2025"
    assert by["I_BHLFTS2"].value == 6.0 and by["I_BHLFTS2"].period == "2024"  # its 2025 cell is absent
    assert "not students" in by["I_BAPP2"].note and "never used as a prior" in by["I_BAPP2"].note
    assert eurostat.dataset_facts("cafe", "DE", eu_client(), tmp_path / "c") == []  # no app measure for the cafe pack


def test_eurostat_failures_give_nothing_not_an_error(tmp_path):
    down = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500)))
    assert eurostat.cpi_index("DE", down, tmp_path) is None
    assert eurostat.dataset_facts("saas", "DE", down, tmp_path) == []


def test_eurostat_responses_are_cached(tmp_path):
    calls = []
    c = eu_client(calls)
    eurostat.cpi_index("DE", c, tmp_path)
    eurostat.cpi_index("DE", c, tmp_path)
    assert len(calls) == 1


# ------------------------------------------------------------------------------------------------ BLS
TEXTS = {bls.ALL_ITEMS: fred_text(bls.ALL_ITEMS, [(2023, 100.0, ()), (2024, 110.0, ()), (2025, 121.0, (10,)),
                                                    (2026, 130.0, tuple(range(4, 13)))]),
         "CUUR0000SEEE": fred_text("CUUR0000SEEE", [(2023, 100.0, ()), (2024, 98.0, ()), (2025, 95.0, ())])}


def test_bls_yearly_average_uses_published_months_and_skips_a_year_still_in_progress(tmp_path):
    pi = bls.cpi_index("US", fred_client(TEXTS), tmp_path)
    assert pi.values == {"2023": 100.0, "2024": 110.0, "2025": 121.0}  # 2025 has 11 months (October never collected)
    assert "2026" not in pi.values and pi.source == "US Bureau of Labor Statistics"


def test_bls_facts_say_the_change_in_plain_words(tmp_path):
    facts = bls.dataset_facts("saas", "USA", fred_client(TEXTS), tmp_path)
    allitems = next(f for f in facts if f.name.endswith("All items"))
    assert allitems.period == "2025" and allitems.value == 121.0 and allitems.note.startswith("+10.0% on 2024")
    assert any("Information technology" in f.name for f in facts)
    assert bls.dataset_facts("saas", "SG", fred_client(TEXTS), tmp_path) == []


def test_bls_failure_gives_nothing(tmp_path):
    assert bls.cpi_index("US", fred_client({}), tmp_path) is None


# ------------------------------------------------------------------------------------------------ in the simulation
def snap(pi):
    return EvidenceSnapshot(snapshot_id="ev_t", created_at="2026-10-29T00:00:00+00:00", pack="saas", geography="DE",
                            status="off", price_index=pi)


def test_a_european_price_index_moves_budgets_by_the_full_change_and_names_its_source(tmp_path):
    pack = load_pack("saas")
    res = apply_evidence(pack, snap(eurostat.cpi_index("DE", eu_client(), tmp_path)), price_base_year=2023)
    scale = 131.9 / 125.9
    assert res.applied and "Eurostat" in res.applied[0] and f"x{scale:.3f}" in res.applied[0]
    for before, after in zip(pack.segments, res.segments, strict=True):
        assert after.priors.budget[1] == round(before.priors.budget[1] * scale, 2)


def test_a_us_price_index_moves_budgets_too(tmp_path):
    pack = load_pack("saas")
    res = apply_evidence(pack, snap(bls.cpi_index("US", fred_client(TEXTS), tmp_path)), price_base_year=2024)
    assert "US Bureau of Labor Statistics" in res.applied[0] and "x1.100" in res.applied[0]
