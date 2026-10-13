"""Adapter between the Council and the decision engine.

The Council never computes market outcomes itself in production: it asks an
``EngineAdapter`` for the share of every option under a given population and
option set. Two implementations exist:

* ``FrozenSignatureAdapter`` wraps Person A's engine through the frozen
  signature ``run_scenario(agents, options, seed, repeats) -> RunResult``.
* ``MockEngineAdapter`` is a deterministic test double for fixture work. Its
  results are always labelled ``source="mock"`` and must never be presented
  as engine output.
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol

import numpy as np

OUTSIDE_ID = "outside"
YOU_ID = "you"


class EngineInputError(ValueError):
    """The population or options cannot be evaluated."""


class EngineEvaluationError(RuntimeError):
    """The engine ran but returned something unusable."""


@dataclass(frozen=True)
class EngineEvaluation:
    shares: Dict[str, float]
    source: str
    detail: Dict[str, Any] = field(default_factory=dict)

    def share(self, option_id: str) -> float:
        if option_id not in self.shares:
            raise EngineEvaluationError(f"engine returned no share for option '{option_id}'")
        return self.shares[option_id]


class EngineAdapter(Protocol):
    source: str

    def evaluate(self, agents: List[dict], options: List[dict], seed: int) -> EngineEvaluation:
        ...


def _finite(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


class MockEngineAdapter:
    """Deterministic stand-in for the engine (MOCK, not Person A's engine).

    Returns the *expected* share of each option: the mean softmax choice
    probability over agents, using the utility form from master plan 4.2.
    No sampling is involved, so results are exactly reproducible and the seed
    is recorded but has no effect.
    """

    source = "mock"

    _REQUIRED = ("budget", "alpha", "w", "switch", "risk", "outside_utility")

    def evaluate(self, agents: List[dict], options: List[dict], seed: int) -> EngineEvaluation:
        opts = [o for o in options if o.get("role") != OUTSIDE_ID]
        if not agents:
            raise EngineInputError("population has no agents")
        if not opts:
            raise EngineInputError("no options to evaluate")
        k = None
        for o in opts:
            if not _finite(o.get("price")) or o["price"] < 0:
                raise EngineInputError(f"option '{o.get('id')}' has an invalid price: {o.get('price')!r}")
            feats = o.get("features")
            if not isinstance(feats, list) or not feats or not all(_finite(f) for f in feats):
                raise EngineInputError(f"option '{o.get('id')}' has a missing or invalid feature vector")
            k = len(feats) if k is None else k
            if len(feats) != k:
                raise EngineInputError("options have feature vectors of different lengths")

        ids = [o["id"] for o in opts]
        price = np.array([o["price"] for o in opts], dtype=float)
        feats = np.array([o["features"] for o in opts], dtype=float)
        novelty = np.array([float(o.get("novelty", 0.0)) for o in opts])

        probs = np.zeros(len(ids) + 1)
        for a in agents:
            missing = [key for key in self._REQUIRED if key not in a]
            if missing:
                raise EngineInputError(f"agent '{a.get('id')}' is missing {missing}")
            w = np.array(a["w"], dtype=float)
            if w.shape != (k,):
                raise EngineInputError(f"agent '{a.get('id')}' weight vector does not match {k} attributes")
            brand = a.get("brand") or {}
            u = (
                np.array([float(brand.get(i, 0.0)) for i in ids])
                + feats @ w
                - float(a["alpha"]) * price
                - float(a["switch"]) * np.array([i != a.get("incumbent") for i in ids], dtype=float)
                - float(a["risk"]) * novelty
            )
            u_all = np.append(u, float(a["outside_utility"]))
            mask = np.append(price <= float(a["budget"]), True)
            tau = float(a.get("tau", 1.0)) or 1.0
            z = np.where(mask, u_all / tau, -np.inf)
            z -= z.max()
            p = np.exp(z)
            probs += p / p.sum()
        probs /= len(agents)
        shares = {i: float(probs[n]) for n, i in enumerate(ids)}
        shares[OUTSIDE_ID] = float(probs[-1])
        return EngineEvaluation(shares=shares, source=self.source, detail={"seed": seed, "method": "expected_share"})


class FrozenSignatureAdapter:
    """Wraps ``run_scenario(agents, options, seed, repeats) -> RunResult``."""

    source = "engine"

    def __init__(self, run_scenario: Callable[..., Any], repeats: int = 1):
        self._run = run_scenario
        self._repeats = repeats

    def evaluate(self, agents: List[dict], options: List[dict], seed: int) -> EngineEvaluation:
        result = self._run(agents, options, seed=seed, repeats=self._repeats)
        if hasattr(result, "model_dump"):
            result = result.model_dump()
        elif hasattr(result, "__dict__") and not isinstance(result, dict):
            result = vars(result)
        totals = result.get("totals") if isinstance(result, dict) else None
        if not isinstance(totals, dict) or not totals:
            raise EngineEvaluationError("engine result has no 'totals'; expected the frozen RunResult shape")
        shares: Dict[str, float] = {}
        for oid, entry in totals.items():
            share = entry.get("p50", entry.get("share")) if isinstance(entry, dict) else None
            if not _finite(share):
                raise EngineEvaluationError(f"engine returned a non-numeric share for '{oid}'")
            shares[oid] = float(share)
        return EngineEvaluation(
            shares=shares, source=self.source, detail={"seed": seed, "run_id": result.get("run_id")}
        )


def get_default_adapter(mode: Optional[str] = None) -> EngineAdapter:
    """``COUNCIL_ENGINE=mock`` forces the mock; ``auto`` (default) uses the
    frozen ``backend.engine.engine_ref.run_scenario`` (or ``engine.py`` when A
    ships it), otherwise the labelled mock."""
    mode = (mode or os.environ.get("COUNCIL_ENGINE", "auto")).lower()
    if mode == "mock":
        return MockEngineAdapter()
    for module in ("backend.engine.engine", "backend.engine.engine_ref"):
        try:
            mod = __import__(module, fromlist=["run_scenario"])
            return FrozenSignatureAdapter(getattr(mod, "run_scenario"))
        except (ImportError, AttributeError):
            continue
    if mode == "engine":
        raise ImportError("COUNCIL_ENGINE=engine but no engine module with run_scenario is importable")
    return MockEngineAdapter()
