"""Devil's Advocate tests (Person B)."""
from __future__ import annotations

import copy

from council.advocate import FACTORS, PARAMETERS, check_availability, fragility_score, perturb, run_advocate
from council.engine_adapter import MockEngineAdapter, YOU_ID


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
    from council.advocate import Perturbation

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


def test_baseline_failed(stub_adapter, saas):
    class Boom:
        source = "engine"

        def evaluate(self, *args, **kwargs):
            raise RuntimeError("nope")

    report = run_advocate(saas["population"]["agents"], saas["options"], Boom(), seed=1)
    assert report.status == "baseline_failed"
    assert report.fragility == 1.0
