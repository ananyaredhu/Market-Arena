"""Numeric-claim grounding for Council text.

Every number written in Council text must match a value in the evidence set
built from the inputs (RunResult, Strategist, Advocate). A cited number
matches if it equals an evidence value at the precision it was written, for
example ``0.19`` matches 0.1904 and ``36.8%`` matches a relative change of
-0.368 (signs are compared as written magnitudes).

Digits embedded in identifiers (``p10``, ``run_8f21``, ``price_cut_20``) are
not treated as claims.
"""
from __future__ import annotations

import math
import re
from typing import Iterable, List, Set

_NUMBER = re.compile(r"(?<![A-Za-z_\d.])(\d+(?:\.\d+)?)(%?)(?![A-Za-z_\d])")


class Evidence:
    def __init__(self) -> None:
        self._values: Set[float] = set()

    def add(self, value, *, as_percent: bool = False) -> None:
        if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
            return
        if not math.isfinite(value):
            return
        self._values.add(abs(float(value)))
        if as_percent:
            self._values.add(abs(float(value)) * 100)

    def extend(self, values: Iterable, *, as_percent: bool = False) -> None:
        for v in values:
            self.add(v, as_percent=as_percent)

    def supports(self, written: str) -> bool:
        x = float(written)
        decimals = len(written.split(".")[1]) if "." in written else 0
        tol = 0.5 * 10 ** (-decimals) + 1e-12
        return any(abs(v - x) <= tol for v in self._values)


def cited_numbers(text: str) -> List[str]:
    return [m.group(1) for m in _NUMBER.finditer(text or "")]


def unsupported_numbers(text: str, evidence: Evidence) -> List[str]:
    return [n for n in cited_numbers(text) if not evidence.supports(n)]


def is_grounded(text: str, evidence: Evidence) -> bool:
    return not unsupported_numbers(text, evidence)
