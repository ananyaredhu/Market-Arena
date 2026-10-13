"""Competitor Strategist tests (Person B)."""
from __future__ import annotations

import copy

import pytest

from council.engine_adapter import MockEngineAdapter, YOU_ID
from council.strategist import MOVES, apply_move, run_strategist


def _you_share(agents, options):
    # Scripted: our share falls with rival price and rises with rival feature.
    rival = next(o for o in options if o["role"] == "competitor")
    you = next(o for o in options if o["id"] == YOU_ID)
    share = 0.30 - 0.01 * max(0.0, 10.0 - rival["price"]) - 0.05 * (rival["features"][0] - 0.5)
    # Promo is modelled as brand boost on agents; detect via brand.
    for a in agents:
        if a.get("brand", {}).get(rival["id"], 0) > 0.5:
            share -= 0.03
            break
    share = max(0.01, min(0.9, share))
    return {YOU_ID: share, rival["id"]: 1 - share - 0.1, "outside": 0.1}


def test_all_four_moves_evaluated(stub_adapter):
    agents = [{"id": "a1", "brand": {"rival": 0.2}, "budget": 20, "alpha": 0.1, "w": [1.0],
               "switch": 0.1, "risk": 0.1, "incumbent": "rival", "outside_utility": 0.0, "tau": 1.0}]
    options = [
        {"id": "you", "label": "You", "role": "you", "price": 9.0, "features": [0.8], "novelty": 0.5},
        {"id": "rival", "label": "Rival", "role": "competitor", "price": 10.0, "features": [0.5], "novelty": 0.0},
    ]
    report = run_strategist(agents, options, stub_adapter(_you_share), seed=7)
    assert report.status == "ok"
    moves = [(c.competitor_id, c.move) for c in report.candidates]
    assert moves == [("rival", m) for m in MOVES]
    assert all(c.status == "ok" for c in report.candidates)


def test_worst_move_selected(stub_adapter):
    agents = [{"id": "a1", "brand": {"rival": 0.2}, "budget": 20, "alpha": 0.1, "w": [1.0],
               "switch": 0.1, "risk": 0.1, "incumbent": "rival", "outside_utility": 0.0, "tau": 1.0}]
    options = [
        {"id": "you", "label": "You", "role": "you", "price": 9.0, "features": [0.8], "novelty": 0.5},
        {"id": "rival", "label": "Rival", "role": "competitor", "price": 10.0, "features": [0.5], "novelty": 0.0},
    ]
    report = run_strategist(agents, options, stub_adapter(_you_share), seed=7)
    assert report.selected is not None
    # price_cut_20 lowers rival from 10 to 8 → biggest scripted drop among price cuts;
    # add_feature also hurts. Assert selected is the most negative.
    ok = [c for c in report.candidates if c.status == "ok"]
    best = min(ok, key=lambda c: c.share_change)
    assert report.selected["move"] == best.move
    assert report.selected["share_change"] == best.share_change
    assert report.selected["share_change"] < 0


def test_ties_resolved_deterministically(stub_adapter):
    def flat(agents, options):
        return {"you": 0.25, "rival_a": 0.25, "rival_b": 0.25, "outside": 0.25}

    agents = [{"id": "a1", "brand": {}, "budget": 20, "alpha": 0.1, "w": [1.0],
               "switch": 0.1, "risk": 0.1, "incumbent": "outside", "outside_utility": 0.0, "tau": 1.0}]
    options = [
        {"id": "you", "label": "You", "role": "you", "price": 9.0, "features": [0.5], "novelty": 0.0},
        {"id": "rival_a", "label": "A", "role": "competitor", "price": 9.0, "features": [0.5], "novelty": 0.0},
        {"id": "rival_b", "label": "B", "role": "competitor", "price": 9.0, "features": [0.5], "novelty": 0.0},
    ]
    r1 = run_strategist(agents, options, stub_adapter(flat), seed=1)
    r2 = run_strategist(agents, options, stub_adapter(flat), seed=99)
    # Flat shares → no move reduces our share → selected is None; still deterministic.
    assert r1.selected is None and r2.selected is None
    assert r1.per_competitor_best == r2.per_competitor_best

    # Force identical drops for every candidate; tie-break prefers earlier competitor then earlier move.
    state = {"n": 0}

    def always_drop(agents, options):
        state["n"] += 1
        # Call 1 = baseline; later calls = candidates. Same candidate share for all moves.
        you = 0.30 if state["n"] == 1 else 0.10
        return {"you": you, "rival_a": 0.30, "rival_b": 0.30, "outside": 0.10}

    report = run_strategist(agents, options, stub_adapter(always_drop), seed=1)
    assert report.selected is not None
    assert report.selected["competitor_id"] == "rival_a"
    assert report.selected["move"] == MOVES[0]


def test_same_seed_same_result(saas):
    adapter = MockEngineAdapter()
    agents, options = saas["population"]["agents"], saas["options"]
    a = run_strategist(agents, options, adapter, seed=42).to_dict()
    b = run_strategist(agents, options, adapter, seed=42).to_dict()
    assert a == b


def test_invalid_competitor_skipped(stub_adapter):
    agents = [{"id": "a1", "brand": {}, "budget": 20, "alpha": 0.1, "w": [1.0],
               "switch": 0.1, "risk": 0.1, "incumbent": "outside", "outside_utility": 0.0, "tau": 1.0}]
    options = [
        {"id": "you", "label": "You", "role": "you", "price": 9.0, "features": [0.5], "novelty": 0.0},
        {"id": "broken", "label": "Broken", "role": "competitor", "price": -1, "features": [0.5], "novelty": 0.0},
    ]
    report = run_strategist(agents, options, stub_adapter(lambda a, o: {"you": 0.5, "broken": 0.5}), seed=1)
    assert all(c.status == "invalid_input" for c in report.candidates)
    assert report.selected is None
    assert any("skipped" in lim for lim in report.limitations)


def test_failed_evaluation_not_fabricated():
    from council.engine_adapter import EngineEvaluation

    class Boom:
        source = "engine"

        def evaluate(self, agents, options, seed):
            rival = next(o for o in options if o["id"] == "rival")
            if rival["price"] < 10:
                raise RuntimeError("engine blew up")
            return EngineEvaluation(shares={"you": 0.3, "rival": 0.6, "outside": 0.1}, source=self.source)

    agents = [{"id": "a1", "brand": {}, "budget": 20, "alpha": 0.1, "w": [1.0],
               "switch": 0.1, "risk": 0.1, "incumbent": "outside", "outside_utility": 0.0, "tau": 1.0}]
    options = [
        {"id": "you", "label": "You", "role": "you", "price": 9.0, "features": [0.5], "novelty": 0.0},
        {"id": "rival", "label": "Rival", "role": "competitor", "price": 10.0, "features": [0.5], "novelty": 0.0},
    ]
    # Baseline succeeds; price cuts fail → those candidates are "failed", never fabricated.
    report = run_strategist(agents, options, Boom(), seed=1)
    failed = [c for c in report.candidates if c.move in ("price_cut_10", "price_cut_20")]
    assert all(c.status == "failed" and c.candidate_share is None for c in failed)


def test_apply_move_does_not_mutate_inputs():
    agents = [{"id": "a1", "brand": {"rival": 0.1}, "budget": 10, "alpha": 0.1, "w": [1.0],
               "switch": 0.1, "risk": 0.1, "incumbent": "rival", "outside_utility": 0.0, "tau": 1.0}]
    options = [
        {"id": "you", "role": "you", "price": 9.0, "features": [0.8], "novelty": 0.0},
        {"id": "rival", "role": "competitor", "price": 10.0, "features": [0.4], "novelty": 0.0},
    ]
    before_a, before_o = copy.deepcopy(agents), copy.deepcopy(options)
    apply_move("price_cut_20", "rival", agents, options)
    apply_move("add_feature", "rival", agents, options)
    apply_move("promo", "rival", agents, options)
    assert agents == before_a and options == before_o


def test_no_competitors(stub_adapter):
    agents = [{"id": "a1", "brand": {}, "budget": 20, "alpha": 0.1, "w": [1.0],
               "switch": 0.1, "risk": 0.1, "incumbent": "outside", "outside_utility": 0.0, "tau": 1.0}]
    options = [{"id": "you", "role": "you", "price": 9.0, "features": [0.5], "novelty": 0.0}]
    report = run_strategist(agents, options, stub_adapter(lambda a, o: {"you": 1.0}), seed=1)
    assert report.status == "no_competitors"
    assert report.selected is None
