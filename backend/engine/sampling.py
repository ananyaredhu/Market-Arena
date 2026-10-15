"""How a customer's random choice is drawn (Person A): the Gumbel-max trick with fixed noise per (customer, option).

The choice rule is unchanged: a customer picks option j with probability softmax(U_ij / tau_i). What changed is HOW
the random draw is made, so that what-if comparisons only move the customers who are genuinely affected.

Old way: one uniform number per customer cut into slices (one per option). Changing one option's probability shifts
every later slice boundary, so a customer sitting near a boundary could "switch" between two options that did not
change at all.

New way: every (customer, option) pair gets a fixed random "luck" value G_ij, drawn once from a Gumbel distribution.
The customer picks argmax_j (U_ij / tau_i + G_ij). This samples EXACTLY the same softmax probabilities, but now if
option X gets worse, only customers whose winner was X can change their pick; nobody else's ranking moves.

G_ij is a pure function of (seed, repeat, customer id, option id): it does not depend on the order of customers,
on which other customers are present (exclusions) or on which other options exist (adding a rival). So the same
customer keeps the same luck for the same option in every scenario you compare.
"""
from __future__ import annotations

import hashlib

import numpy as np

_MASK = (1 << 64) - 1
_GOLDEN = 0x9E3779B97F4A7C15


def noise_keys(ids: list[str]) -> np.ndarray:
    """Stable 64-bit key per id (independent of order and of the other ids)."""
    return np.array(
        [int.from_bytes(hashlib.blake2b(i.encode(), digest_size=8).digest(), "little") for i in ids], dtype=np.uint64
    )


def _splitmix(x: np.ndarray) -> np.ndarray:
    """SplitMix64 finaliser: turns structured integers into well-mixed 64-bit values (arrays wrap silently)."""
    x = x + np.uint64(_GOLDEN)
    x = (x ^ (x >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
    x = (x ^ (x >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
    return x ^ (x >> np.uint64(31))


def gumbel_noise(seed: int, repeat: int, agent_keys: np.ndarray, option_keys: np.ndarray) -> np.ndarray:
    """(n_agents, n_options) fixed Gumbel(0, 1) noise for this seed and repeat."""
    base = np.uint64(((seed & _MASK) * _GOLDEN + (repeat + 1) * 0xBF58476D1CE4E5B9) & _MASK)
    mixed = _splitmix(agent_keys[:, None] ^ _splitmix(option_keys[None, :] ^ base))
    u = ((mixed >> np.uint64(11)).astype(np.float64) + 0.5) / 2.0**53  # uniform in (0, 1), never exactly 0 or 1
    return -np.log(-np.log(u))


def draw_choices(logits: np.ndarray, noise: np.ndarray) -> np.ndarray:
    """Pick argmax(logits + noise) per customer. Unaffordable options carry logit -inf and can never win."""
    return np.argmax(logits + noise, axis=1)
