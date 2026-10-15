import copy
from collections import Counter

import pytest
from fastapi.testclient import TestClient

from backend.common.contracts import Agent, Population
from backend.common.llm import LLMError
from backend.engine.engine import run_scenario
from backend.main import app
from backend.population import generator
from backend.population.generator import generate_population
from backend.population.models import PackSpec, PopulationRequest, PriorsProposal
from backend.population.packs import PackError, load_pack
from backend.population.sampler import sample_agents, segment_counts
from backend.population.validators import validate_population

PACKS = ["saas", "cafe"]


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "mock")


def make_pop(pack_name="saas", n=300, seed=42) -> tuple[dict, PackSpec]:
    p = load_pack(pack_name)
    ids = ["you"] + [c["id"] for c in p.competitors]
    agents = sample_agents(p.segments, p.attributes, ids, p.outside_id, n, seed)
    pop = {
        "attributes": p.attributes,
        "agents": agents,
        "segments": [{"id": s.id, "name": s.name, "share": s.share, "hostile": s.hostile} for s in p.segments],
    }
    return pop, p


def codes(issues):
    return {i.code for i in issues}


# ---------------------------------------------------------------- packs
@pytest.mark.parametrize("name", PACKS)
def test_packs_load(name):
    p = load_pack(name)
    assert len(p.segments) >= 3 and p.competitors and p.demo_product


def test_unknown_pack_raises():
    with pytest.raises(PackError, match="unknown pack"):
        load_pack("nope")


def test_pack_with_bad_shares_is_rejected():
    raw = load_pack("saas").model_dump()
    raw["segments"][0]["share"] = 0.9
    with pytest.raises(ValueError, match="shares sum"):
        PackSpec.model_validate(raw)


def test_pack_with_wrong_attribute_keys_is_rejected():
    raw = load_pack("saas").model_dump()
    raw["segments"][0]["priors"]["w"].pop("privacy")
    with pytest.raises(ValueError, match="do not match attributes"):
        PackSpec.model_validate(raw)


# ---------------------------------------------------------------- sampler
def test_segment_counts_sum_to_n_and_follow_shares():
    assert segment_counts([0.5, 0.3, 0.2], 7) == [4, 2, 1]
    assert sum(segment_counts([1 / 3] * 3, 10)) == 10


@pytest.mark.parametrize("name", PACKS)
def test_sampler_is_deterministic_and_contract_valid(name):
    a, _ = make_pop(name, n=120, seed=5)
    b, _ = make_pop(name, n=120, seed=5)
    c, _ = make_pop(name, n=120, seed=6)
    assert a["agents"] == b["agents"] != c["agents"]
    for agent in a["agents"]:
        Agent.model_validate(agent)


def test_sampler_respects_shares_and_ranges():
    pop, p = make_pop("saas", n=400)
    counts = Counter(a["segment"] for a in pop["agents"])
    for s in p.segments:
        assert counts[s.id] == round(400 * s.share)
        lo, hi = s.priors.budget
        assert all(lo - 0.01 <= a["budget"] <= hi + 0.01 for a in pop["agents"] if a["segment"] == s.id)


# ---------------------------------------------------------------- validators
@pytest.mark.parametrize("name", PACKS)
def test_template_populations_pass(name):
    pop, p = make_pop(name)
    assert validate_population(pop, p) == []


def test_rejects_population_without_hostile_segment():
    pop, p = make_pop("saas")
    for a in pop["agents"]:
        a["switch"] = 0.1
    for s in pop["segments"]:
        s["hostile"] = False
    assert "hostile" in codes(validate_population(pop, p))


@pytest.mark.parametrize("name", PACKS)
@pytest.mark.parametrize("n", [40, 150, 300])
def test_template_fallback_never_fails_validation(name, n):
    """Regression: a narrow-but-legit range (saas 'loyal' alpha 0.25-0.30) once failed a strict variance check
    on seed 42 / n=150, so the fallback itself crashed. The fallback must pass for any seed and size."""
    for seed in range(25):
        pop, p = make_pop(name, n=n, seed=seed)
        assert validate_population(pop, p) == [], f"{name} n={n} seed={seed}"


def test_narrow_but_real_range_is_not_flagged_as_clones():
    pop, p = make_pop("saas", n=150, seed=42)  # the exact case that used to fail
    assert "diversity" not in codes(validate_population(pop, p))


def test_rejects_inflated_willingness_to_pay():
    pop, p = make_pop("saas")
    for a in pop["agents"]:
        a["budget"] *= 5
    assert "wtp_bound" in codes(validate_population(pop, p))


def test_rejects_clones():
    pop, p = make_pop("saas")
    first = {s: next(a for a in pop["agents"] if a["segment"] == s) for s in {a["segment"] for a in pop["agents"]}}
    pop["agents"] = [dict(first[a["segment"]], id=a["id"]) for a in pop["agents"]]
    assert "diversity" in codes(validate_population(pop, p))


def test_rejects_shares_that_do_not_match_agents():
    pop, p = make_pop("saas")
    pop["agents"] = [a for a in pop["agents"] if a["segment"] != "budget"]
    assert "shares" in codes(validate_population(pop, p))


def test_rejects_too_few_non_buyers():
    pop, p = make_pop("saas")
    for a in pop["agents"]:
        a["outside_utility"] = -9.0
        a["incumbent"] = "free_tool"
    assert "outside_share" in codes(validate_population(pop, p))


def test_rejects_malformed_agent():
    pop, p = make_pop("saas")
    pop["agents"][0]["tau"] = 0
    assert "structure" in codes(validate_population(pop, p))


# ---------------------------------------------------------------- generator
@pytest.mark.parametrize("name", PACKS)
def test_generate_offline_returns_valid_population(name):
    pop = generate_population(PopulationRequest(pack=name, n_agents=150, seed=3))
    Population.model_validate(pop)
    assert pop["generation"]["source"] == "template" and len(pop["agents"]) == 150
    assert pop == generate_population(PopulationRequest(pack=name, n_agents=150, seed=3))  # reproducible


def test_generated_population_runs_through_the_engine():
    pop = generate_population(PopulationRequest(n_agents=200))
    p = load_pack("saas")
    outside = {"id": "outside", "label": "Do nothing", "role": "outside"}
    options = [dict(p.demo_product)] + [dict(c) for c in p.competitors] + [outside]
    r = run_scenario(pop["agents"], options, seed=1, repeats=5)
    assert abs(sum(t["share"] for t in r["totals"].values()) - 1) < 1e-9
    assert r["totals"]["outside"]["share"] >= p.min_outside_share


def _proposal(edit) -> PriorsProposal:
    segs = copy.deepcopy(load_pack("saas").model_dump()["segments"])
    edit(segs)
    return PriorsProposal.model_validate({"segments": segs})


def test_good_llm_proposal_is_used(monkeypatch):
    def shrink(segs):
        for s in segs:
            s["priors"]["budget"] = [s["priors"]["budget"][0] * 0.9, s["priors"]["budget"][1] * 0.9]

    monkeypatch.setattr(generator, "complete_json", lambda *a, **k: _proposal(shrink))
    pop = generate_population(PopulationRequest(n_agents=200))
    assert pop["generation"]["source"] == "llm" and pop["generation"]["fallback_reason"] is None


def test_live_model_echoing_the_template_is_reported_as_llm_but_unchanged(monkeypatch):
    """Found with a real 3B model (qwen2.5:3b): valid JSON, but it copied the template back."""
    monkeypatch.setenv("LLM_MODE", "live")
    monkeypatch.setattr(generator, "complete_json", lambda *a, **k: _proposal(lambda segs: None))
    g = generate_population(PopulationRequest(n_agents=100))["generation"]
    assert g["source"] == "llm" and g["unchanged_from_template"] is True


def test_offline_mode_reports_template_not_llm():
    g = generate_population(PopulationRequest(n_agents=100))["generation"]
    assert g["source"] == "template" and g["unchanged_from_template"] is False


def test_optimistic_llm_proposal_falls_back_to_template(monkeypatch):
    def optimistic(segs):
        for s in segs:
            s["hostile"] = False
            s["priors"]["switch"] = [0.0, 0.1]
            s["priors"]["budget"] = [60, 90]

    monkeypatch.setattr(generator, "complete_json", lambda *a, **k: _proposal(optimistic))
    pop = generate_population(PopulationRequest(n_agents=200))
    assert pop["generation"]["source"] == "template"
    assert "validation failed" in pop["generation"]["fallback_reason"]


def test_proposal_with_unknown_option_id_is_rejected(monkeypatch):
    def invent(segs):
        segs[0]["priors"]["incumbent"] = {"made_up_rival": 1.0}

    monkeypatch.setattr(generator, "complete_json", lambda *a, **k: _proposal(invent))
    pop = generate_population(PopulationRequest(n_agents=100))
    assert pop["generation"]["source"] == "template" and "unknown option" in pop["generation"]["fallback_reason"]


def test_llm_failure_falls_back_to_template(monkeypatch):
    def boom(*a, **k):
        raise LLMError("all providers failed")

    monkeypatch.setattr(generator, "complete_json", boom)
    pop = generate_population(PopulationRequest(n_agents=100))
    assert pop["generation"]["source"] == "template" and "all providers failed" in pop["generation"]["fallback_reason"]


# ---------------------------------------------------------------- route
client = TestClient(app)


def test_route_returns_fixture_when_mock_on(monkeypatch):
    monkeypatch.setenv("MOCK", "1")
    assert client.post("/population/generate").json()["population_id"] == "pop_saas_1"


def test_route_runs_real_generator_when_mock_off(monkeypatch):
    monkeypatch.setenv("MOCK", "0")
    r = client.post("/population/generate", json={"pack": "cafe", "n_agents": 120, "seed": 9})
    assert r.status_code == 200
    Population.model_validate(r.json())
    assert r.json()["pack"] == "cafe" and len(r.json()["agents"]) == 120


def test_route_empty_body_uses_defaults(monkeypatch):
    monkeypatch.setenv("MOCK", "0")
    r = client.post("/population/generate")
    assert r.status_code == 200 and len(r.json()["agents"]) == 300


def test_route_unknown_pack_is_404(monkeypatch):
    monkeypatch.setenv("MOCK", "0")
    assert client.post("/population/generate", json={"pack": "nope"}).status_code == 404
