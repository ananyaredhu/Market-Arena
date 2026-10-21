import json

import httpx
import pytest

from backend.evidence import resources, singstat
from backend.evidence.models import DatasetFact, EvidenceSnapshot


def col(key, value):
    return {"key": key, "value": value}


def cpi_table():
    def series(name, first, values):
        cells = [col(str(y), v) for y, v in zip(range(first, first + len(values)), values, strict=True)]
        return {"rowText": name, "uoM": "Index", "columns": cells}
    return {"title": "Consumer Price Index (CPI), 2024 As Base Year, Annual", "row": [
        series("All Items", 2018, [92.0, 92.5, 91.8, 95.0, 98.0, 100.0, 100.9]),
        series("Information & Communication", 2018, [105.0, 104.0, 103.0, 102.0, 101.0, 100.0, 98.1]),
        series("Education", 2018, [95.0, "na", 97.0, 98.0, 99.0, 100.0, 100.7]),
    ]}


def hes_table():
    def r(name, v):
        quintiles = {"key": "Expenditure Quintile 1/", "columns": []}
        return {"rowText": name, "uoM": "Dollar", "columns": [col("Total", v), quintiles]}
    return {"title": "Average Monthly Household Expenditure", "row": [
        r("Information and Communication", "270.2"), r("Education", "404.2"),
        r("Food and Beverage Serving Services 2/", "965.7"), r("Total", "5931")]}


def client(tables, calls=None):
    def handler(request):
        if calls is not None:
            calls.append(str(request.url))
        tid = str(request.url).rsplit("/", 1)[1]
        if tid in tables:
            return httpx.Response(200, json={"Data": tables[tid]})
        return httpx.Response(404)
    return httpx.Client(transport=httpx.MockTransport(handler))


TABLES = {singstat.CPI_TABLE: cpi_table(), singstat.HES_TABLE: hes_table()}


def test_cpi_facts_report_the_level_and_the_change_in_plain_words(tmp_path):
    facts = singstat.dataset_facts("saas", "SG", client(TABLES), tmp_path)
    cpi = {f.name: f for f in facts if f.table_id == singstat.CPI_TABLE}
    assert set(cpi) == {"Consumer prices: All Items", "Consumer prices: Information & Communication",
                        "Consumer prices: Education"}
    ic = cpi["Consumer prices: Information & Communication"]
    assert ic.period == "2024" and ic.value == 98.1
    assert ic.note == "-1.9% on 2023, -5.7% over 5 years"
    assert ic.quote == "Information & Communication, 2024: 98.1 (Index)"
    assert ic.url.endswith(singstat.CPI_TABLE)


def test_a_series_with_a_gap_still_reports_what_it_can(tmp_path):
    facts = singstat.dataset_facts("saas", "SG", client(TABLES), tmp_path)
    edu = next(f for f in facts if f.name.endswith("Education") and f.table_id == singstat.CPI_TABLE)
    assert edu.note == "+0.7% on 2023"  # 2019 is 'na', so there is no five-year change


def test_household_spending_is_labelled_as_per_household(tmp_path):
    every = singstat.dataset_facts("cafe", "SG", client(TABLES), tmp_path)
    facts = [f for f in every if f.table_id == singstat.HES_TABLE]
    assert [f.name for f in facts] == ["Household spending: Food and Beverage Serving Services"]
    f = facts[0]
    assert f.value == 965.7 and f.period == "2023" and "per resident household" in f.unit
    assert "not per student or per visit" in f.note and "16.3% of all household spending" in f.note


def test_only_singapore_has_official_figures(tmp_path):
    assert singstat.dataset_facts("saas", "IN", client(TABLES), tmp_path) == []
    assert singstat.dataset_facts("saas", "Singapore", client(TABLES), tmp_path)


def test_a_failed_or_malformed_table_gives_no_facts_not_an_error(tmp_path):
    assert singstat.dataset_facts("saas", "SG", client({}), tmp_path) == []
    assert singstat.fetch_table("M213801", client({"M213801": {"row": []}}), tmp_path) is None
    assert singstat.fetch_table("../etc/passwd", client(TABLES), tmp_path) is None


def test_tables_are_cached(tmp_path):
    calls = []
    c = client(TABLES, calls)
    singstat.dataset_facts("saas", "SG", c, tmp_path)
    singstat.dataset_facts("cafe", "SG", c, tmp_path)
    assert len(calls) == 2  # one fetch per table, the second run read the cache
    cached = json.loads((tmp_path / f"{singstat.CPI_TABLE}.json").read_text())
    assert cached["data"]["title"].startswith("Consumer Price Index")


def test_the_all_items_index_is_kept_whole_for_any_starting_year(tmp_path):
    pi = singstat.cpi_index("SG", client(TABLES), tmp_path)
    assert pi.table_id == singstat.CPI_TABLE and pi.values["2024"] == 100.9 and pi.values["2018"] == 92.0
    assert "2019" in pi.values and pi.url.endswith(singstat.CPI_TABLE)
    assert singstat.cpi_index("IN", client(TABLES), tmp_path) is None
    assert singstat.cpi_index("SG", client({}), tmp_path / "other") is None


def test_official_figures_land_in_the_resources_library(tmp_path):
    facts = singstat.dataset_facts("cafe", "SG", client(TABLES), tmp_path)
    snap = EvidenceSnapshot(snapshot_id="ev_x", created_at="2026-10-21T00:00:00+00:00", pack="cafe", geography="SG",
                            status="off", datasets=facts)
    items = resources.from_snapshot(snap)
    assert items and all(r.kind == "dataset" and r.topic == "official data" for r in items)
    assert all(r.domain == "tablebuilder.singstat.gov.sg" and r.quote for r in items)


def test_a_dataset_fact_is_plain_data():
    f = DatasetFact(name="n", source="s", table_id="T1", url="https://x.sg/a", period="2025", value=1.0, unit="u",
                    note="n", quote="q", retrieved_at="2026-10-21T00:00:00+00:00")
    assert DatasetFact.model_validate(f.model_dump()) == f


@pytest.mark.parametrize("bad", ["", "a b", "x" * 40])
def test_table_ids_are_checked(bad, tmp_path):
    assert singstat.fetch_table(bad, client(TABLES), tmp_path) is None
