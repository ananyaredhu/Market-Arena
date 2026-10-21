"""Backtest case files (Person A's harness; format proposed by Person B in backend/council/backtest/cafe_case_01.yaml).

A case describes ONE real event whose outcome is already known, in terms the simulator can run:

  direction : the market before vs after a change (a price cut, a new feature). Did the studied product's sales go
              up, down or stay flat?   scenario_before + scenario_after -> observed_outcome.direction
  success   : a launch with a stated target. Did it hit the target?
              scenario_before + success -> observed_outcome.result

Honesty rules enforced here:
  * Only cases with status "sourced" (every outcome backed by a URL and access date) or "synthetic" (a plumbing
    self-test, never counted in the headline accuracy) are scored. "needs_sourcing" cases are listed, not scored.
  * A sourced case must list at least one source and must carry its observed outcome.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

Direction = Literal["up", "down", "flat"]
Result = Literal["success", "fail"]


class Observed(BaseModel):
    model_config = ConfigDict(extra="ignore")

    direction: Direction | None = None  # direction cases
    result: Result | None = None  # success cases
    metric: str = ""  # what was measured: units sold, subscribers, footfall (NOT revenue, unless the case says so)
    value_before: float | None = None
    value_after: float | None = None
    period: str = ""
    note: str = ""


class Scenario(BaseModel):
    model_config = ConfigDict(extra="ignore")

    products: list[dict] = Field(default_factory=list)  # full Option dicts (id, label, role, price, features, novelty)
    change: str = ""  # human description, e.g. "chain_cafe price -20%"
    notes: str = ""


class SuccessSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    threshold: float = Field(gt=0, le=1)  # the subject must win at least this share of the simulated market
    threshold_rationale: str  # where the threshold comes from; it must be fixed BEFORE the simulation is run


class Case(BaseModel):
    model_config = ConfigDict(extra="ignore")

    case_id: str
    pack: str
    status: Literal["needs_sourcing", "sourced", "rejected", "synthetic"]
    question: str = ""
    question_type: Literal["direction", "success"] = "direction"
    subject: str = "you"  # the option whose sales are being predicted
    geography: str = "SG"
    n_agents: int = Field(default=300, ge=50, le=5000)
    seeds: list[int] = Field(default_factory=lambda: [1, 2, 3, 4, 5])  # independent populations and draws
    min_effect: float = Field(default=0.01, gt=0, lt=1)  # share change below this counts as "flat"
    scenario_before: Scenario = Field(default_factory=Scenario)
    scenario_after: Scenario | None = None
    success: SuccessSpec | None = None
    observed_outcome: Observed | None = None
    sources: list[dict] = Field(default_factory=list)
    limitations: str = ""
    synthetic: bool = False
    path: str = ""  # filled in by load_cases

    @model_validator(mode="after")
    def _checks(self) -> Case:
        if self.status == "synthetic":
            self.synthetic = True
        if self.status in ("sourced", "synthetic"):
            if self.observed_outcome is None:
                raise ValueError(f"{self.case_id}: a {self.status} case needs an observed_outcome")
            if self.status == "sourced" and not self.sources:
                raise ValueError(f"{self.case_id}: a sourced case needs at least one source (url + accessed date)")
            if not self.scenario_before.products:
                raise ValueError(f"{self.case_id}: scenario_before.products is empty")
            if self.question_type == "direction":
                if self.scenario_after is None or not self.scenario_after.products:
                    raise ValueError(f"{self.case_id}: a direction case needs scenario_after.products")
                if self.observed_outcome.direction is None:
                    raise ValueError(f"{self.case_id}: observed_outcome.direction is missing")
            else:
                if self.success is None:
                    raise ValueError(f"{self.case_id}: a success case needs a `success` block")
                if self.observed_outcome.result is None:
                    raise ValueError(f"{self.case_id}: observed_outcome.result is missing")
        return self

    @property
    def scorable(self) -> bool:
        return self.status in ("sourced", "synthetic")

    @property
    def outcomes(self) -> tuple[str, ...]:
        return ("up", "down", "flat") if self.question_type == "direction" else ("success", "fail")

    @property
    def observed(self) -> str | None:
        o = self.observed_outcome
        if o is None:
            return None
        return o.direction if self.question_type == "direction" else o.result


def load_cases(paths: list[Path]) -> tuple[list[Case], list[tuple[str, str]]]:
    """Load case files. Returns (valid cases, [(file, problem)] for files that could not be used)."""
    cases, problems = [], []
    for p in paths:
        try:
            raw = yaml.safe_load(Path(p).read_text())
            case = Case.model_validate(raw)
            case.path = str(p)
            cases.append(case)
        except Exception as e:  # noqa: BLE001  (a bad case file must be reported, never crash the whole run)
            problems.append((str(p), str(e).strip().splitlines()[-1][:200]))
    return cases, problems
