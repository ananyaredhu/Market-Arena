"""The Gumbel draw must (1) sample exactly the softmax probabilities, (2) be a pure function of
(seed, repeat, customer id, option id) and (3) move only customers whose winning option got worse."""
import copy

import numpy as np
import pytest

from backend.common.fixtures import load_fixture
from backend.engine.engine import run_scenario
from backend.engine.engine_ref import _probabilities
from backend.engine.sampling import draw_choices, gumbel_noise, noise_keys

POP = load_fixture("population_saas")["agents"]
OPTIONS = load_fixture("options_saas")


# ---------------------------------------------------------------- 1. the odds are unchanged
def test_draw_frequencies_match_the_softmax_probabilities():
    """40,000 customers with identical parameters but different ids: empirical shares must equal softmax(U/tau)."""
    U = np.array([[0.4, 1.1, -0.3, 0.6]])
    tau = np.array([0.8])
    P = _probabilities(U, tau)[0]
    n = 40_000
    logits = np.repeat(U / tau[:, None], n, axis=0)
    noise = gumbel_noise(7, 0, noise_keys([f"c{i}" for i in range(n)]), noise_keys(["a", "b", "c", "d"]))
    freq = np.bincount(draw_choices(logits, noise), minlength=4) / n
    assert np.abs(freq - P).max() < 0.01, (freq, P)  # 4 sigma is about 0.01 at n=40,000


def test_unaffordable_options_never_win():
    logits = np.array([[-np.inf, 0.2, -np.inf, 0.1]] * 5000)
    noise = gumbel_noise(1, 0, noise_keys([f"c{i}" for i in range(5000)]), noise_keys(list("abcd")))
    assert set(draw_choices(logits, noise)) <= {1, 3}


def test_noise_is_standard_gumbel():
    g = gumbel_noise(3, 0, noise_keys([f"c{i}" for i in range(20_000)]), noise_keys(["x"])).ravel()
    assert np.isfinite(g).all()
    assert abs(g.mean() - 0.5772) < 0.03 and abs(g.std() - 1.2825) < 0.03  # Gumbel(0,1): mean 0.577, sd 1.283


# ---------------------------------------------------------------- 2. a pure function of the ids
def test_noise_is_deterministic_and_changes_with_seed_and_repeat():
    a, o = noise_keys(["a1", "a2"]), noise_keys(["x", "y"])
    assert np.array_equal(gumbel_noise(1, 0, a, o), gumbel_noise(1, 0, a, o))
    assert not np.array_equal(gumbel_noise(1, 0, a, o), gumbel_noise(2, 0, a, o))
    assert not np.array_equal(gumbel_noise(1, 0, a, o), gumbel_noise(1, 1, a, o))


def test_a_customers_luck_does_not_depend_on_other_customers_or_other_options():
    """Adding a rival or excluding other customers must not change anyone's luck for an option that stays."""
    full = gumbel_noise(5, 0, noise_keys(["a1", "a2", "a3"]), noise_keys(["x", "y", "z"]))
    subset = gumbel_noise(5, 0, noise_keys(["a3", "a1"]), noise_keys(["z", "x"]))  # reordered, fewer of each
    assert subset[0, 0] == full[2, 2] and subset[0, 1] == full[2, 0]
    assert subset[1, 0] == full[0, 2] and subset[1, 1] == full[0, 0]


# ---------------------------------------------------------------- 3. only affected customers move
def movers(run_a, run_b):
    a = {c["agent_id"]: c["choice"] for c in run_a["choices"]}
    return [(c["agent_id"], a[c["agent_id"]], c["choice"]) for c in run_b["choices"] if a[c["agent_id"]] != c["choice"]]


def with_option(oid, **changes):
    opts = copy.deepcopy(OPTIONS)
    next(o for o in opts if o["id"] == oid).update(changes)
    return opts


@pytest.mark.parametrize("seed", range(8))
def test_a_worse_rival_only_loses_its_own_customers(seed):
    base = run_scenario(POP, OPTIONS, seed)
    after = run_scenario(POP, with_option("chain_app", price=20.0), seed)
    assert all(prev == "chain_app" for _, prev, _ in movers(base, after))


@pytest.mark.parametrize("seed", range(8))
def test_a_better_product_only_gains_customers(seed):
    base = run_scenario(POP, OPTIONS, seed)
    after = run_scenario(POP, with_option("you", price=3.0), seed)
    assert all(new == "you" for _, _, new in movers(base, after))


@pytest.mark.parametrize("seed", range(8))
def test_a_worse_product_only_loses_its_own_customers(seed):
    base = run_scenario(POP, with_option("you", price=3.0), seed)
    after = run_scenario(POP, OPTIONS, seed)  # price back up
    assert all(prev == "you" for _, prev, _ in movers(base, after))


def test_excluding_customers_does_not_reshuffle_the_rest():
    base = run_scenario(POP, OPTIONS, 4)
    kept = [a for a in POP if a["segment"] != "loyal"]
    after = run_scenario(kept, OPTIONS, 4)
    before = {c["agent_id"]: c["choice"] for c in base["choices"]}
    assert all(before[c["agent_id"]] == c["choice"] for c in after["choices"])


def test_adding_a_rival_only_takes_customers_to_the_rival():
    base = run_scenario(POP, OPTIONS, 4)
    rival = {"id": "newcomer", "label": "Newcomer", "role": "competitor", "price": 0.0,
             "features": [0.9, 0.9, 0.9, 0.9], "novelty": 0.0}
    agents = [dict(a, brand={**a["brand"], "newcomer": 0.0}) for a in POP]
    with_rival = run_scenario(agents, OPTIONS[:-1] + [rival, OPTIONS[-1]], 4)
    assert all(new == "newcomer" for _, _, new in movers(base, with_rival))
