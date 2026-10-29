import pytest

from backend.evidence import resources, store
from backend.evidence.apply import apply_evidence
from backend.evidence.models import Economics, EvidenceSnapshot, Finding, PriceIndex, TrendNote
from backend.population.packs import load_pack

URL = "https://example.com/pricing"
WB_URL = "https://api.worldbank.org/x"


# ---------------------------------------------------------------- applying evidence: datasets only
PACK = load_pack("saas")


def snapshot(**kw) -> EvidenceSnapshot:
    base = dict(snapshot_id="ev_t", created_at="2026-10-15T00:00:00+00:00", pack="saas", geography="SG", status="ok")
    base.update(kw)
    return EvidenceSnapshot(**base)


def f(**kw):
    base = dict(kind="segment_budget", subject="budget", claim="students spend 4 to 6", low=4.0, high=6.0,
                currency="SGD", quote="students spend between 4 and 6 dollars", url=URL)
    base.update(kw)
    return Finding(**base)


def econ(scale=0.5):
    return Economics(country="India", iso="IN", gdp_pc_ppp=10000, year=2025, baseline_iso="SG",
                     baseline_gdp_pc_ppp=160000, budget_scale=scale, source_url=WB_URL)


def cpi(**values):
    series = {"2019": 92.0, "2020": 91.5, "2021": 92.5, "2022": 98.0, "2023": 100.0, "2024": 100.0, "2025": 100.9}
    series.update({k.lstrip("y"): v for k, v in values.items()})
    return PriceIndex(name="Consumer Price Index, all items (2024 = 100)", table_id="M213801",
                      url="https://tablebuilder.singstat.gov.sg/api/table/tabledata/M213801",
                      retrieved_at="2026-10-21T00:00:00+00:00", values=series)


def seg(res, sid):
    return next(s for s in res.segments if s.id == sid)


def unchanged(res) -> bool:
    return [s.model_dump() for s in res.segments] == [s.model_dump() for s in PACK.segments]


def test_nothing_changes_without_evidence():
    assert unchanged(apply_evidence(PACK, None))
    assert unchanged(apply_evidence(PACK, snapshot(status="off")))
    assert unchanged(apply_evidence(PACK, snapshot(status="failed")))


def test_the_dataset_adjustment_survives_a_failed_web_search():
    for status in ("off", "failed", "empty"):
        r = apply_evidence(PACK, snapshot(status=status, economics=econ(0.5)))
        assert not unchanged(r) and r.applied


def test_the_pack_itself_is_never_mutated():
    before = PACK.model_dump()
    apply_evidence(PACK, snapshot(economics=econ()))
    assert PACK.model_dump() == before


def test_surveys_news_and_competitor_pages_never_move_a_prior():
    notes = [TrendNote(note="cut", quote="Students are cutting back", url=URL, effect=e)
             for e in ("budget_down", "budget_up", "price_sensitivity_up", "price_sensitivity_down")]
    findings = [f(), f(kind="free_tool_adoption", subject="budget", value=0.99, low=None, high=None,
                       quote="99% rely on free study apps"),
                f(kind="competitor_price", subject="chain_app", value=4.99, low=None, high=None)]
    r = apply_evidence(PACK, snapshot(findings=findings, trend_notes=notes))
    assert unchanged(r) and not r.applied


def test_country_economics_scales_every_budget_and_keeps_the_source():
    r = apply_evidence(PACK, snapshot(economics=econ(0.5)))
    for before, after in zip(PACK.segments, r.segments):
        assert after.priors.budget == (round(before.priors.budget[0] * 0.5, 2), round(before.priors.budget[1] * 0.5, 2))
        assert after.evidence == "evidence" and after.sources[0]["url"] == WB_URL
        assert after.priors.alpha == before.priors.alpha and after.priors.incumbent == before.priors.incumbent
    assert "assumption" in r.applied[0]


def test_a_scale_of_one_changes_nothing():
    assert unchanged(apply_evidence(PACK, snapshot(economics=econ(1.0))))


def test_budgets_move_by_the_full_reported_price_change_from_the_starting_year():
    r = apply_evidence(PACK, snapshot(price_index=cpi()), 2024)
    for before, after in zip(PACK.segments, r.segments, strict=True):
        lo, hi = before.priors.budget
        scale = 100.9 / 100.0
        assert after.priors.budget == (round(lo * scale, 2), round(hi * scale, 2))
        assert after.evidence == "evidence" and "M213801" in after.sources[0]["url"]
    assert "+0.9% from 2024 to 2025" in r.applied[0]
    assert "assumes the pack's budgets are in 2024 prices" in r.applied[0]


def test_the_starting_year_is_editable_and_a_big_change_is_not_capped():
    r = apply_evidence(PACK, snapshot(price_index=cpi()), 2019)  # +9.7% over six years
    scale = 100.9 / 92.0
    assert seg(r, "budget").priors.budget[1] == round(PACK.segments[0].priors.budget[1] * scale, 2)
    huge = apply_evidence(PACK, snapshot(price_index=cpi(y2025=250.0)), 2024)  # +150%: reported, so applied
    assert seg(huge, "budget").priors.budget[1] == round(PACK.segments[0].priors.budget[1] * 2.5, 2)


def test_a_starting_year_the_series_cannot_answer_changes_nothing_and_says_why():
    for year, words in ((1950, "no 1950 value"), (2031, "before the starting year 2031")):
        r = apply_evidence(PACK, snapshot(price_index=cpi()), year)
        assert unchanged(r) and not r.applied and words in r.skipped[0]


def test_no_price_change_without_an_index_a_year_or_when_the_year_is_the_latest():
    assert unchanged(apply_evidence(PACK, snapshot(), 2024))
    assert unchanged(apply_evidence(PACK, snapshot(price_index=cpi()), None))
    assert unchanged(apply_evidence(PACK, snapshot(price_index=cpi()), 2025))


def test_income_scale_and_price_change_combine_and_survive_a_failed_search():
    r = apply_evidence(PACK, snapshot(status="failed", economics=econ(0.5), price_index=cpi()), 2024)
    expected = round(PACK.segments[0].priors.budget[1] * 0.5, 2)
    assert seg(r, "budget").priors.budget[1] == round(expected * 1.009, 2) or abs(
        seg(r, "budget").priors.budget[1] - expected * 1.009) < 0.02
    assert len(r.applied) == 2


# ---------------------------------------------------------------- store, council view and the Resources library
def test_store_round_trip_and_council_view(tmp_path):
    snap = snapshot(findings=[f()], trend_notes=[TrendNote(note="n", quote="Students are cutting back", url=URL,
                                                           effect="budget_down")])
    store.save(snap, tmp_path / "evidence")
    assert store.load("ev_t", [tmp_path / "evidence"]) == snap
    ctx = store.council_context(snap)
    assert ctx["evidence_snapshot_id"] == "ev_t" and ctx["research_notes"][0]["source_url"] == URL
    assert ctx["reference_only"] is True and ctx["trend_notes"][0]["effect"] is None


@pytest.mark.parametrize("bad", ["../secrets", "a/b", "", ".hidden", "x" * 200])
def test_snapshot_ids_cannot_escape_the_folder(tmp_path, bad):
    with pytest.raises(KeyError):
        store.load(bad, [tmp_path])


def test_missing_snapshot_is_a_keyerror(tmp_path):
    with pytest.raises(KeyError):
        store.load("ev_nope", [tmp_path])


def test_saving_a_snapshot_files_its_findings_in_the_library(tmp_path):
    snap = snapshot(findings=[f(), f(kind="competitor_price", claim="Taskade Pro is 10", quote="Pro $10/mo", url="https://www.taskade.com/a")],
                    trend_notes=[TrendNote(note="cutting back", quote="Students are cutting back", url=URL)])
    store.save(snap, tmp_path / "evidence")
    items = resources.list_resources(tmp_path / "resources")
    assert {r.topic for r in items} == {"spending", "competitor prices", "trends"}
    taskade = next(r for r in items if r.topic == "competitor prices")
    assert taskade.domain == "taskade.com" and taskade.quote == "Pro $10/mo" and taskade.retrieved_at == snap.created_at


def test_the_library_accumulates_runs_without_duplicates(tmp_path):
    one = snapshot(snapshot_id="ev_1", findings=[f()])
    two = snapshot(snapshot_id="ev_2", created_at="2026-10-16T00:00:00+00:00",
                   findings=[f(), f(claim="another", quote="a different quote", url="https://other.org/x")])
    store.save(one, tmp_path / "evidence")
    store.save(two, tmp_path / "evidence")
    items = resources.list_resources(tmp_path / "resources")
    assert len(items) == 2
    assert next(r for r in items if r.url == URL).snapshot_id == "ev_1"  # the first sighting is kept
    assert items[0].retrieved_at >= items[1].retrieved_at  # newest first


def test_ids_are_unique_across_packs_even_for_the_same_page_and_quote(tmp_path):
    store.save(snapshot(snapshot_id="ev_a", findings=[f()]), tmp_path / "evidence")
    store.save(snapshot(snapshot_id="ev_b", pack="cafe", findings=[f()]), tmp_path / "evidence")
    items = resources.list_resources(tmp_path / "resources")
    assert len(items) == 2 and len({r.id for r in items}) == 2


def test_library_filters(tmp_path):
    store.save(snapshot(findings=[f(), f(kind="market_size", claim="big market", quote="a big market", url="https://x.org/")]),
               tmp_path / "evidence")
    store.save(snapshot(snapshot_id="ev_cafe", pack="cafe", findings=[f(quote="cafe quote")]), tmp_path / "evidence")
    d = tmp_path / "resources"
    assert len(resources.list_resources(d)) == 3
    assert len(resources.list_resources(d, pack="cafe")) == 1
    assert [r.topic for r in resources.list_resources(d, topic="market size")] == ["market size"]
    assert len(resources.list_resources(d, q="X.ORG")) == 1
    assert resources.list_resources(tmp_path / "missing") == []


# ---------------------------------------------------------------- generator and routes
def test_generator_applies_country_economics_from_a_saved_snapshot(tmp_path, monkeypatch):
    from backend.population.generator import generate_population
    from backend.population.models import PopulationRequest
    monkeypatch.setattr(store, "RUN_DIR", tmp_path)
    store.save(snapshot(snapshot_id="ev_gen", economics=econ(0.5)))
    pop = generate_population(PopulationRequest(n_agents=60, evidence_snapshot_id="ev_gen"))
    assert pop["evidence_snapshot_id"] == "ev_gen"
    seg_b = next(s for s in pop["segments"] if s["id"] == "budget")
    assert seg_b["evidence"] == "evidence" and seg_b["sources"][0]["url"] == WB_URL
    ev = pop["generation"]["evidence"]
    assert ev["used"] and ev["applied"]
    top = PACK.segments[0].priors.budget[1] * 0.5
    assert max(a["budget"] for a in pop["agents"] if a["segment"] == "budget") <= top


def test_generator_moves_budgets_with_prices_from_the_chosen_year(tmp_path, monkeypatch):
    from backend.population.generator import generate_population
    from backend.population.models import PopulationRequest
    monkeypatch.setattr(store, "RUN_DIR", tmp_path)
    store.save(snapshot(snapshot_id="ev_cpi", price_index=cpi(y2025=120.0)))
    top = PACK.segments[0].priors.budget[1]
    pop = generate_population(PopulationRequest(n_agents=300, evidence_snapshot_id="ev_cpi", price_base_year=2024))
    ev = pop["generation"]["evidence"]
    assert ev["used"] and "+20.0% from 2024 to 2025" in ev["applied"][0] and ev["price_base_year"] == 2024
    assert max(a["budget"] for a in pop["agents"] if a["segment"] == "budget") > top  # moved past the old top
    old = generate_population(PopulationRequest(n_agents=300, evidence_snapshot_id="ev_cpi", price_base_year=2025))
    assert not old["generation"]["evidence"]["used"]  # starting at the latest year: no change to apply


def test_generator_keeps_page_findings_as_reference_only(tmp_path, monkeypatch):
    from backend.population.generator import generate_population
    from backend.population.models import PopulationRequest
    monkeypatch.setattr(store, "RUN_DIR", tmp_path)
    store.save(snapshot(snapshot_id="ev_pages", findings=[f()],
                        trend_notes=[TrendNote(note="n", quote="q", url=URL, effect="budget_down")]))
    pop = generate_population(PopulationRequest(n_agents=60, evidence_snapshot_id="ev_pages"))
    ev = pop["generation"]["evidence"]
    assert not ev["used"] and ev["applied"] == [] and ev["reference_items"] == 2
    assert all(s["evidence"] != "evidence" for s in pop["segments"])


def test_generator_without_evidence_is_unchanged():
    from backend.population.generator import generate_population
    from backend.population.models import PopulationRequest
    pop = generate_population(PopulationRequest(n_agents=60))
    assert pop["evidence_snapshot_id"] is None and "evidence" not in pop["generation"]


def test_missing_snapshot_falls_back_with_a_reason():
    from backend.population.generator import generate_population
    from backend.population.models import PopulationRequest
    pop = generate_population(PopulationRequest(n_agents=60, evidence_snapshot_id="ev_missing"))
    ev = pop["generation"]["evidence"]
    assert not ev["used"] and "not found" in ev["note"] and pop["evidence_snapshot_id"] is None


def test_research_with_nothing_available_still_returns_a_valid_population(monkeypatch):
    from backend.population.generator import generate_population
    from backend.population.models import PopulationRequest
    monkeypatch.delenv("SEARXNG_URL", raising=False)
    pop = generate_population(PopulationRequest(n_agents=60, research=True))
    ev = pop["generation"]["evidence"]
    assert ev["status"] == "off" and not ev["used"] and "SEARXNG_URL" in ev["note"]


def test_routes(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from backend.main import app
    monkeypatch.setattr(store, "RUN_DIR", tmp_path)
    monkeypatch.setenv("MOCK", "0")
    monkeypatch.delenv("SEARXNG_URL", raising=False)
    c = TestClient(app)
    r = c.post("/evidence/research", json={"pack": "saas", "geography": "SG"})
    assert r.status_code == 200 and r.json()["status"] == "off"
    sid = r.json()["snapshot_id"]
    assert c.get(f"/evidence/{sid}").json()["snapshot_id"] == sid
    assert "research_notes" in c.get(f"/evidence/{sid}?view=council").json()
    assert c.get("/evidence/nope").status_code == 404
    assert c.get("/evidence/..%2Fsecrets").status_code in (404, 422)


def test_resources_route(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from backend import sim_routes
    from backend.main import app
    monkeypatch.setattr(store, "RUN_DIR", tmp_path / "evidence")
    monkeypatch.setattr(sim_routes, "SEED_RESOURCES_DIR", tmp_path / "no_seed")
    monkeypatch.setenv("MOCK", "0")
    c = TestClient(app)
    empty = c.get("/resources").json()
    assert empty["count"] == 0 and empty["reference_only"] is True
    store.save(snapshot(findings=[f(), f(kind="market_size", claim="big", quote="a big market", url="https://x.org/")]))
    body = c.get("/resources").json()
    assert body["count"] == 2 and body["topics"] == {"spending": 1, "market size": 1}
    assert body["items"][0]["url"] and body["items"][0]["quote"]
    assert c.get("/resources", params={"topic": "market size"}).json()["count"] == 1
    assert c.get("/resources", params={"pack": "cafe"}).json()["count"] == 0


def test_a_fresh_clone_still_has_the_committed_demo_resources(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from backend.main import app
    monkeypatch.setattr(store, "RUN_DIR", tmp_path / "evidence")  # an empty runtime library
    monkeypatch.setenv("MOCK", "0")
    body = TestClient(app).get("/resources").json()
    assert body["count"] > 0 and body["reference_only"] is True
    assert {"saas", "cafe"} <= {i["pack"] for i in body["items"]}
    assert all(i["quote"] and i["url"].startswith("https://") and i["retrieved_at"] for i in body["items"])
    sensitivity = [i for i in body["items"] if i["topic"] == "price sensitivity"]
    assert sensitivity and all(i["pack"] == "saas" and i["geography"] == "global" for i in sensitivity)


def test_a_runtime_entry_is_not_listed_twice_when_the_demo_copy_has_it(tmp_path):
    seed = tmp_path / "seed"
    resources.add(snapshot(findings=[f()]), seed)
    resources.add(snapshot(findings=[f()]), tmp_path / "run")
    assert len(resources.list_resources([tmp_path / "run", seed])) == 1
