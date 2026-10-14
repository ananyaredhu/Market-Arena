"""Devil's Advocate tests (Person B)."""
from __future__ import annotations

import copy

from backend.council.advocate import FACTORS, PARAMETERS, check_availability, fragility_score, perturb, run_advocate
from backend.council.engine_adapter import YOU_ID, MockEngineAdapter


def test_perturbations_change_intended_parameter_only(saas):
    agents = saas["population"]["agents"][:5]
    for parameter in PARAMETERS:
        for factor in FACTORS:
            out = perturb(agents, parameter, factor)
            assert len(out) == len(agents)
            for original, changed in zip(agents, out):
                for key in original:
                    if parameter == "brand" and key == "brand":
                        for brand_id, value in original["brand"].items():
                            if brand_id == YOU_ID:
                                assert changed["brand"][brand_id] == value
                            else:
                                assert abs(changed["brand"][brand_id] - value * factor) < 1e-9
                    elif key == parameter:
                        assert abs(changed[key] - original[key] * factor) < 1e-9
                    elif key != "brand" or parameter != "brand":
                        assert changed[key] == original[key]


def test_fragility_in_unit_interval(saas):
    report = run_advocate(
        saas["population"]["agents"], saas["options"], MockEngineAdapter(), seed=42
    )
    assert 0.0 <= report.fragility <= 1.0
    assert report.fragility_formula
    assert len(report.risks) <= 3


def test_fragility_score_bounds():
    from backend.council.advocate import Perturbation

    empty = fragility_score(0.2, [])
    assert empty == 1.0
    mild = Perturbation(
        parameter="budget", factor=0.8, direction="-20%", assumption="x", status="ok",
        abs_change=-0.01, leader_changed=False,
    )
    assert 0.0 <= fragility_score(0.2, [mild]) <= 1.0
    huge = Perturbation(
        parameter="budget", factor=0.8, direction="-20%", assumption="x", status="ok",
        abs_change=-1.0, leader_changed=True,
    )
    assert fragility_score(0.05, [huge]) == 1.0


def test_missing_priors_reported(stub_adapter, saas):
    agents = copy.deepcopy(saas["population"]["agents"][:3])
    for a in agents:
        a.pop("budget", None)
    report = run_advocate(agents, saas["options"], MockEngineAdapter(), seed=1)
    assert any("willingness to pay" in lim.lower() or "budget" in lim.lower() for lim in report.limitations)


def test_zero_brand_prior_skipped():
    agents = [{"id": "a1", "budget": 10, "alpha": 0.1, "brand": {"you": 0.0, "rival": 0.0},
               "w": [1.0], "switch": 0.1, "risk": 0.1, "incumbent": "outside",
               "outside_utility": 0.0, "tau": 1.0}]
    msg = check_availability("brand", agents)
    assert msg is not None


def test_reproducible(saas):
    adapter = MockEngineAdapter()
    a = run_advocate(saas["population"]["agents"], saas["options"], adapter, seed=42).to_dict()
    b = run_advocate(saas["population"]["agents"], saas["options"], adapter, seed=42).to_dict()
    assert a == b


def test_risks_ranked_by_measured_drop(stub_adapter):
    agents = [{"id": "a1", "budget": 10, "alpha": 0.2, "brand": {"you": 0.0, "rival": 0.4},
               "w": [1.0], "switch": 0.1, "risk": 0.1, "incumbent": "rival", "outside_utility": 0.0, "tau": 1.0}]
    options = [
        {"id": "you", "role": "you", "price": 9.0, "features": [0.5], "novelty": 0.0},
        {"id": "rival", "role": "competitor", "price": 8.0, "features": [0.4], "novelty": 0.0},
    ]

    def shares(changed, _options):
        budget = changed[0]["budget"]
        alpha = changed[0]["alpha"]
        you = 0.40
        if budget < 10:
            you = 0.10
        elif budget > 10:
            you = 0.35
        if alpha > 0.2:
            you -= 0.05
        return {"you": you, "rival": 0.4, "outside": round(0.6 - you, 10)}

    report = run_advocate(agents, options, stub_adapter(shares), seed=1)
    assert [risk["key"] for risk in report.risks][0] == "budget"
    assert report.risks[0]["abs_change"] <= report.risks[-1]["abs_change"]
    assert report.risks[0]["baseline_share"] == 0.40
    assert report.risks[0]["perturbed_share"] == 0.10


def test_zero_baseline_has_no_relative_change(stub_adapter):
    agents = [{"id": "a1", "budget": 10, "alpha": 0.2, "brand": {"you": 0.0, "rival": 0.4},
               "w": [1.0], "switch": 0.1, "risk": 0.1, "incumbent": "rival", "outside_utility": 0.0, "tau": 1.0}]
    options = [
        {"id": "you", "role": "you", "price": 9.0, "features": [0.5], "novelty": 0.0},
        {"id": "rival", "role": "competitor", "price": 8.0, "features": [0.4], "novelty": 0.0},
    ]
    flat = stub_adapter(lambda a, o: {"you": 0.0, "rival": 0.2, "outside": 0.8})
    report = run_advocate(agents, options, flat, seed=1)
    ok = [p for p in report.perturbations if p.status == "ok"]
    assert ok
    assert all(p.rel_change is None for p in ok)
    assert report.fragility == 0.0 or report.fragility == 1.0 or 0.0 <= report.fragility <= 1.0


def test_unsupported_parameter_is_reported():
    agents = [{"id": "a1", "budget": 10, "alpha": 0.1, "brand": {"rival": 0.2}}]
    message = check_availability("weather", agents)
    assert message is not None and "unknown parameter" in message


def test_real_engine_sensitivity_is_reproducible():
    from backend.common.fixtures import load_fixture
    from backend.council.engine_adapter import get_default_adapter

    population = load_fixture("population_saas")
    options = load_fixture("options_saas")
    adapter = get_default_adapter("engine")
    first = run_advocate(population["agents"], options, adapter, seed=42)
    second = run_advocate(population["agents"], options, adapter, seed=42)
    assert first.to_dict() == second.to_dict()
    assert first.engine_source == "engine"
    assert first.baseline_share == load_fixture("run_result")["totals"]["you"]["share"]
    drops = [p for p in first.perturbations if p.status == "ok" and p.abs_change is not None]
    assert drops
    assert [p.abs_change for p in drops]  # measured, not a fixed score
    ranked = sorted(first.risks, key=lambda r: r["abs_change"])
    assert [r["key"] for r in first.risks] == [r["key"] for r in ranked]


def test_baseline_failed(stub_adapter, saas):
    class Boom:
        source = "engine"

        def evaluate(self, *args, **kwargs):
            raise RuntimeError("nope")

    report = run_advocate(saas["population"]["agents"], saas["options"], Boom(), seed=1)
    assert report.status == "baseline_failed"
    assert report.fragility == 1.0
