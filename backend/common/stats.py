"""Small statistics helpers for evaluation reports (no SciPy needed)."""
from __future__ import annotations

import math


def wilson_interval(successes: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a proportion. Honest about small samples (unlike +/- sqrt(p(1-p)/n))."""
    if n == 0:
        return (0.0, 1.0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def binom_tail(k: int, n: int, p: float = 0.5) -> float:
    """One-sided exact P(X >= k) for X ~ Binomial(n, p): the chance of doing at least this well by luck."""
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1))


def pct(x: float) -> str:
    return f"{100 * x:.0f}%"
