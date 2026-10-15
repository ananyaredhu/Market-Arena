"""Human overrides (Person A): lock a choice, edit a parameter, tune a segment, exclude a customer.

Master Plan 5.3. Every override is written to an audit trail (who: always "human", what, before and after), so a
result always shows what was machine-generated and what a person adjusted.

Safety rule: a new override is TRIAL-RUN against the engine before it is saved. If the engine rejects it (for
example a lock to an option the customer cannot afford, or excluding everyone) it is refused with the engine's own
message and nothing is stored.
"""
from __future__ import annotations

import copy
import json
import os
import re
import threading
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from backend.engine.engine import run_scenario
from backend.scenarios.context import ScenarioContext

SCALARS = ("budget", "alpha", "switch", "risk", "outside_utility", "tau")
LOWER = {"budget": 0.0, "alpha": 0.0, "switch": 0.0, "risk": 0.0, "tau": 1e-6}  # smallest allowed value
FACTOR_RANGE = (0.1, 10.0)


class OverrideError(ValueError):
    """The override is invalid or the engine cannot run with it. The message says why."""


# ---------------------------------------------------------------- models
class OverrideRequest(BaseModel):
    project_id: str = "proj_1"
    type: Literal["lock", "edit", "segment_tune", "exclude"]
    agent_id: str | None = None
    segment_id: str | None = None
    option_id: str | None = None  # lock: the option to pin to
    # edit / segment_tune: budget | alpha | switch | risk | outside_utility | tau | w:<attr> | brand:<option>
    param: str | None = None
    value: float | None = None  # edit: new absolute value
    factor: float | None = None  # segment_tune: multiplier
    note: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def _shape(self) -> OverrideRequest:
        t = self.type
        if t == "lock" and not (self.option_id and (self.agent_id or self.segment_id)):
            raise ValueError("lock needs option_id and an agent_id or segment_id")
        if t == "edit" and not (self.agent_id and self.param and self.value is not None):
            raise ValueError("edit needs agent_id, param and value")
        if t == "segment_tune" and not (self.segment_id and self.param and self.factor is not None):
            raise ValueError("segment_tune needs segment_id, param and factor")
        if t == "exclude" and not (self.agent_id or self.segment_id):
            raise ValueError("exclude needs an agent_id or segment_id")
        if t == "segment_tune" and not FACTOR_RANGE[0] <= (self.factor or 0) <= FACTOR_RANGE[1]:
            raise ValueError(f"factor must be between {FACTOR_RANGE[0]} and {FACTOR_RANGE[1]}")
        return self


class Override(OverrideRequest):
    id: str
    created_at: str
    created_by: str = "human"
    before: float | None = None  # edit: the agent's old value; segment_tune: the segment's mean before
    after: float | None = None  # edit: new value; segment_tune: the segment's mean after
    effect: str = ""  # one plain sentence for the audit trail


@dataclass
class Applied:
    agents: list[dict]
    locks: dict | None
    excluded: list[str]


# ---------------------------------------------------------------- parameter access
def _get(agent: dict, param: str) -> float:
    if param in SCALARS:
        return float(agent[param])
    kind, _, key = param.partition(":")
    if kind == "brand":
        return float(agent["brand"].get(key, 0.0))
    raise OverrideError(f"unknown parameter '{param}'")


def _set(agent: dict, param: str, value: float, attributes: list[str]) -> None:
    if param in SCALARS:
        if param in LOWER and value < LOWER[param]:
            raise OverrideError(f"{param} must be at least {LOWER[param]}")
        agent[param] = value
        return
    kind, _, key = param.partition(":")
    if kind == "w" and key in attributes:
        agent["w"][attributes.index(key)] = value
    elif kind == "brand":
        agent["brand"][key] = value
    else:
        raise OverrideError(f"unknown parameter '{param}'")


def _get_param(agent: dict, param: str, attributes: list[str]) -> float:
    kind, _, key = param.partition(":")
    if kind == "w":
        if key not in attributes:
            raise OverrideError(f"unknown attribute '{key}' (known: {attributes})")
        return float(agent["w"][attributes.index(key)])
    return _get(agent, param)


# ---------------------------------------------------------------- apply
def apply_overrides(ctx: ScenarioContext, overrides: list[Override]) -> Applied:
    """Apply overrides in creation order to COPIES of the agents. Returns agents, engine locks and exclusions."""
    agents = copy.deepcopy(ctx.agents)
    by_id = {a["id"]: a for a in agents}
    attrs = ctx.population["attributes"]
    locks: dict = {"agents": {}, "segments": {}}
    excluded: set[str] = set()

    for o in overrides:
        members = [a for a in agents if a["segment"] == o.segment_id] if o.segment_id else []
        if o.type == "edit" and o.agent_id in by_id:
            _set(by_id[o.agent_id], o.param, o.value, attrs)
        elif o.type == "segment_tune":
            for a in members:
                _set(a, o.param, _get_param(a, o.param, attrs) * o.factor, attrs)
        elif o.type == "lock":
            if o.agent_id:
                locks["agents"][o.agent_id] = o.option_id
            else:
                locks["segments"][o.segment_id] = o.option_id
        elif o.type == "exclude":
            excluded |= {o.agent_id} if o.agent_id else {a["id"] for a in members}

    kept = [a for a in agents if a["id"] not in excluded]
    live_ids = {a["id"] for a in kept}
    locks["agents"] = {k: v for k, v in locks["agents"].items() if k in live_ids}
    return Applied(kept, locks if (locks["agents"] or locks["segments"]) else None, sorted(excluded))


def _plain(engine_message: str) -> str:
    """Founder-friendly wording for the engine's technical refusals."""
    if "unaffordable" in engine_message:
        who = re.search(r"\[(.*)\]", engine_message)
        names = who.group(1).replace("'", "") if who else "a pinned customer"
        return (f"Cannot pin {names} to that option: its price is above their budget. "
                "Choose a cheaper option, or raise their budget first.")
    return engine_message


def run_with_overrides(ctx: ScenarioContext, overrides: list[Override]) -> tuple[dict, dict, Applied]:
    """(adjusted run, baseline run, applied). The adjusted run carries prev_choice from the baseline."""
    baseline = run_scenario(ctx.agents, ctx.options, ctx.seed, ctx.repeats)
    if not overrides:
        return baseline, baseline, Applied(copy.deepcopy(ctx.agents), None, [])
    applied = apply_overrides(ctx, overrides)
    if not applied.agents:
        raise OverrideError("every customer is excluded; at least one must remain")
    try:
        run = run_scenario(applied.agents, ctx.options, ctx.seed, ctx.repeats, locks=applied.locks, prev=baseline)
    except ValueError as e:  # unaffordable lock, unknown option, ...
        raise OverrideError(_plain(str(e))) from e
    run["overrides_applied"] = len(overrides)
    return run, baseline, applied


# ---------------------------------------------------------------- store
class OverrideStore:
    """Tiny JSON-file store (data/overrides.json). Fine for one process and a few hundred records."""

    def __init__(self, path: Path | None = None):
        default = Path(__file__).resolve().parents[2] / "data" / "overrides.json"
        self.path = Path(os.getenv("OVERRIDES_FILE", path or default))
        self._lock = threading.Lock()

    def _read(self) -> dict[str, list[dict]]:
        return json.loads(self.path.read_text()) if self.path.exists() else {}

    def _write(self, data: dict[str, list[dict]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2))

    def list(self, project_id: str) -> list[Override]:
        with self._lock:
            return [Override.model_validate(o) for o in self._read().get(project_id, [])]

    def save(self, project_id: str, items: list[Override]) -> None:
        with self._lock:
            data = self._read()
            data[project_id] = [o.model_dump() for o in items]
            self._write(data)


def get_store() -> OverrideStore:
    return OverrideStore()


# ---------------------------------------------------------------- service
def _describe(ctx: ScenarioContext, req: OverrideRequest, before: float | None, after: float | None) -> str:
    who = f"customer {req.agent_id}" if req.agent_id else f"segment {req.segment_id}"
    if req.type == "lock":
        return f"Pinned {who} to '{req.option_id}'."
    if req.type == "exclude":
        return f"Excluded {who} from the run."
    if req.type == "edit":
        return f"Set {who}'s {req.param} from {before:.3g} to {after:.3g}."
    return f"Scaled {req.param} for {who} by x{req.factor:g} (segment average {before:.3g} to {after:.3g})."


def _validate_targets(ctx: ScenarioContext, req: OverrideRequest) -> None:
    ids = {a["id"] for a in ctx.agents}
    segs = {a["segment"] for a in ctx.agents}
    if req.agent_id and req.agent_id not in ids:
        raise OverrideError(f"unknown customer '{req.agent_id}'")
    if req.segment_id and req.segment_id not in segs:
        raise OverrideError(f"unknown segment '{req.segment_id}' (known: {sorted(segs)})")
    if req.type == "lock" and req.option_id not in {o["id"] for o in ctx.options}:
        raise OverrideError(f"unknown option '{req.option_id}'")


def add_override(
    ctx: ScenarioContext, req: OverrideRequest, store: OverrideStore | None = None
) -> tuple[Override, dict]:
    """Validate, trial-run and save. Returns (the saved override, the adjusted run)."""
    store = store or get_store()
    _validate_targets(ctx, req)
    existing = store.list(ctx.project_id)
    if req.agent_id and req.agent_id in apply_overrides(ctx, existing).excluded:
        raise OverrideError(f"customer '{req.agent_id}' is already excluded; remove that exclusion first")

    attrs = ctx.population["attributes"]
    before = after = None
    if req.type == "edit":
        # "before" is the value the customer has NOW, i.e. after earlier overrides (excluded customers keep theirs)
        current = {a["id"]: a for a in ctx.agents} | {a["id"]: a for a in apply_overrides(ctx, existing).agents}
        before, after = _get_param(current[req.agent_id], req.param, attrs), req.value
    elif req.type == "segment_tune":
        cur = [a for a in apply_overrides(ctx, existing).agents if a["segment"] == req.segment_id]
        before = sum(_get_param(a, req.param, attrs) for a in cur) / max(1, len(cur))
        after = before * req.factor

    record = Override(**req.model_dump(), id=uuid.uuid4().hex[:8], created_at=datetime.now(UTC).isoformat(),
                      before=before, after=after, effect="")
    record.effect = _describe(ctx, req, before, after)
    run, _, _ = run_with_overrides(ctx, existing + [record])  # raises OverrideError if the engine refuses
    store.save(ctx.project_id, existing + [record])
    return record, run


def remove_override(ctx: ScenarioContext, override_id: str, store: OverrideStore | None = None) -> dict:
    store = store or get_store()
    items = store.list(ctx.project_id)
    if override_id not in {o.id for o in items}:
        raise KeyError(override_id)
    keep = [o for o in items if o.id != override_id]
    run, _, _ = run_with_overrides(ctx, keep)
    store.save(ctx.project_id, keep)
    return run


def audit_trail(ctx: ScenarioContext, store: OverrideStore | None = None) -> dict:
    items = (store or get_store()).list(ctx.project_id)
    gen = ctx.population.get("generation") or {}
    if items:
        summary = (f"{len(items)} human adjustment(s) on top of a machine-generated population "
                   f"of {len(ctx.agents)} customers.")
    else:
        summary = "No human adjustments: everything is machine-generated."
    return {
        "project_id": ctx.project_id,
        "machine_generated": {
            "agents": len(ctx.agents),
            "seed": ctx.seed,
            "population_source": gen.get("source", "fixture"),
        },
        "human_adjustments": [o.model_dump() for o in items],
        "summary": summary,
    }
