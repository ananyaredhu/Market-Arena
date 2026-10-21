import pytest

from backend.evidence import store
from backend.evidence.apply import apply_evidence
from backend.evidence.models import Economics, EvidenceSnapshot, Finding, TrendNote
from backend.population.packs import load_pack

URL = "https://example.com/pricing"


# ---------------------------------------------------------------- applying evidence
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


def seg(res, sid):
    return next(s for s in res.segments if s.id == sid)


def test_nothing_changes_without_evidence():
    for snap in (None, snapshot(status="off"), snapshot(status="failed"), snapshot(status="empty")):
        r = apply_evidence(PACK, snap)
        assert [s.model_dump() for s in r.segments] == [s.model_dump() for s in PACK.segments] and not r.applied


def test_the_pack_itself_is_never_mutated():
    before = [s.model_dump() for s in PACK.segments]
    apply_evidence(PACK, snapshot(findings=[f()]))
    assert [s.model_dump() for s in PACK.segments] == before


def test_sourced_budget_replaces_the_range_and_keeps_the_quote():
    r = apply_evidence(PACK, snapshot(findings=[f()]))
    s = seg(r, "budget")
    assert s.priors.budget == (4.0, 6.0) and s.evidence == "evidence"
    assert s.sources == [{"url": URL, "quote": f().quote, "retrieved_at": "2026-10-15T00:00:00+00:00"}]
    assert seg(r, "exam").evidence != "evidence"  # untouched segments keep their tag


def test_a_budget_figure_far_from_the_template_is_skipped_not_clamped():
    r = apply_evidence(PACK, snapshot(findings=[f(low=500.0, high=900.0, quote="x" * 25)]))
    assert seg(r, "budget").priors.budget == PACK.segments[0].priors.budget and not r.applied
    assert "not comparable" in r.skipped[0]


def test_a_budget_range_partly_outside_the_band_is_trimmed_to_it():
    t = PACK.segments[0].priors.budget  # (3, 9): band is 1.5 to 18
    r = apply_evidence(PACK, snapshot(findings=[f(low=10.0, high=40.0)]))
    assert seg(r, "budget").priors.budget == (10.0, t[1] * 2.0)


def test_other_currencies_are_skipped_not_guessed():
    r = apply_evidence(PACK, snapshot(findings=[f(currency="INR")]))
    assert seg(r, "budget").priors.budget == PACK.segments[0].priors.budget and "INR" in r.skipped[0]


def test_free_tool_adoption_moves_the_mix_but_only_so_far():
    t = PACK.segments[0].priors.incumbent
    old = t["free_tool"] / sum(t.values())
    r = apply_evidence(PACK, snapshot(findings=[f(kind="free_tool_adoption", subject="budget", value=0.99,
                                                  low=None, high=None, quote="99% rely on free study apps")]))
    inc = seg(r, "budget").priors.incumbent
    assert sum(inc.values()) == pytest.approx(1.0)
    assert inc["free_tool"] == pytest.approx(min(0.99, old + 0.25))


def test_free_tool_adoption_needs_the_quote_to_talk_about_free_use():
    # "86% use generative AI tools" is true but says nothing about free tools.
    r = apply_evidence(PACK, snapshot(findings=[f(kind="free_tool_adoption", subject="budget", value=0.86,
                                                  low=None, high=None,
                                                  quote="86% of students use generative AI tools")]))
    assert not r.applied and "free" in r.skipped[0]
    assert seg(r, "budget").priors.incumbent == PACK.segments[0].priors.incumbent


def test_competitor_prices_are_advisory_only():
    r = apply_evidence(PACK, snapshot(findings=[f(kind="competitor_price", subject="chain_app", low=None,
                                                  high=None, value=4.99)]))
    assert r.advisory and not r.applied
    assert [s.model_dump() for s in r.segments] == [s.model_dump() for s in PACK.segments]


def test_economics_scales_budgets_unless_a_sourced_budget_exists():
    e = Economics(country="India", iso="IN", gdp_pc_ppp=10000, year=2025, baseline_iso="SG",
                  baseline_gdp_pc_ppp=160000, budget_scale=0.5, source_url="https://api.worldbank.org/x")
    r = apply_evidence(PACK, snapshot(findings=[f()], economics=e))
    assert seg(r, "budget").priors.budget == (4.0, 6.0)  # sourced, not scaled again
    t = PACK.segments[1].priors.budget
    assert seg(r, "exam").priors.budget == (round(t[0] * 0.5, 2), round(t[1] * 0.5, 2))


def test_trends_nudge_and_can_be_switched_off():
    n = TrendNote(note="cutting back", quote="Students are cutting back", url=URL, effect="budget_down")
    on = apply_evidence(PACK, snapshot(trend_notes=[n]))
    off = apply_evidence(PACK, snapshot(trend_notes=[n]), use_trends=False)
    t = PACK.segments[0].priors.budget
    assert seg(on, "budget").priors.budget[1] == pytest.approx(t[1] * 0.9, abs=0.01)
    assert seg(off, "budget").priors.budget == t and not off.applied


def test_a_trend_naming_unknown_segments_changes_nothing_and_says_so():
    n = TrendNote(note="youths cut back", quote="Students are cutting back", url=URL, effect="budget_down",
                  segments=["youths", "AI users"])
    r = apply_evidence(PACK, snapshot(trend_notes=[n]))
    assert not r.applied and "do not exist" in r.skipped[0]
    assert [s.model_dump() for s in r.segments] == [s.model_dump() for s in PACK.segments]


def test_repeated_trends_cannot_drift_past_the_bound():
    notes = [TrendNote(note=f"cut {i}", quote="Students are cutting back", url=f"https://site{i}.com/a",
                       effect="budget_down") for i in range(10)]
    r = apply_evidence(PACK, snapshot(trend_notes=notes))
    t = PACK.segments[0].priors.budget
    assert seg(r, "budget").priors.budget[1] >= t[1] * 0.8 - 0.01


def test_only_one_trend_per_website_counts():
    a = TrendNote(note="google free", quote="Students are cutting back", url="https://www.news.com/a",
                  effect="budget_down")
    b = TrendNote(note="google free again", quote="Students are cutting back", url="https://news.com/b",
                  effect="budget_down")
    one = apply_evidence(PACK, snapshot(trend_notes=[a]))
    two = apply_evidence(PACK, snapshot(trend_notes=[a, b]))
    assert seg(two, "budget").priors.budget == seg(one, "budget").priors.budget
    assert len(two.applied) == 1 and "news.com" in two.skipped[0]


def test_trend_can_target_named_segments():
    n = TrendNote(note="exam crunch", quote="Exam students spend more", url=URL, effect="budget_up",
                  segments=["exam"])
    r = apply_evidence(PACK, snapshot(trend_notes=[n]))
    assert seg(r, "budget").priors.budget == PACK.segments[0].priors.budget
    assert seg(r, "exam").priors.budget[1] > PACK.segments[1].priors.budget[1]


# ---------------------------------------------------------------- store
def test_store_round_trip_and_council_view(tmp_path):
    snap = snapshot(findings=[f()], trend_notes=[TrendNote(note="n", quote="Students are cutting back", url=URL,
                                                           effect="budget_down")])
    store.save(snap, tmp_path)
    assert store.load("ev_t", [tmp_path]) == snap
    ctx = store.council_context(snap)
    assert ctx["evidence_snapshot_id"] == "ev_t" and ctx["research_notes"][0]["source_url"] == URL
    assert ctx["trend_notes"][0]["effect"] == "budget -10%"


@pytest.mark.parametrize("bad", ["../secrets", "a/b", "", ".hidden", "x" * 200])
def test_snapshot_ids_cannot_escape_the_folder(tmp_path, bad):
    with pytest.raises(KeyError):
        store.load(bad, [tmp_path])


def test_missing_snapshot_is_a_keyerror(tmp_path):
    with pytest.raises(KeyError):
        store.load("ev_nope", [tmp_path])


# ---------------------------------------------------------------- generator and routes
def test_generator_uses_a_saved_snapshot_and_records_it(tmp_path, monkeypatch):
    from backend.population.generator import generate_population
    from backend.population.models import PopulationRequest
    monkeypatch.setattr(store, "RUN_DIR", tmp_path)
    store.save(snapshot(snapshot_id="ev_gen", findings=[f()]))
    pop = generate_population(PopulationRequest(n_agents=60, evidence_snapshot_id="ev_gen"))
    assert pop["evidence_snapshot_id"] == "ev_gen"
    seg_b = next(s for s in pop["segments"] if s["id"] == "budget")
    assert seg_b["evidence"] == "evidence" and seg_b["sources"][0]["url"] == URL
    ev = pop["generation"]["evidence"]
    assert ev["used"] and ev["applied"]
    assert max(a["budget"] for a in pop["agents"] if a["segment"] == "budget") <= 6.0


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
