"""Resolve the population, options and RunResult for one council request.

Person C does not yet persist scenario runs. This module therefore accepts three
authoritative sources, in order:

1. A bundle this process stored after an engine-backed request for that run id.
2. A shared demo fixture whose canonical choices match ``engine.py``.
3. A fresh ``engine.run_scenario`` call for the population and options in the request.

The path run id is never copied onto a result from a different run. A stored
bundle bound to one project is not returned for another project.
"""
from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from backend.common.contracts import RunResult
from backend.common.fixtures import load_fixture
from backend.engine.engine import run_scenario
from backend.intake.projects import get_persisted_project, project_data_dir

_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,80}$")
_SHARE_TOLERANCE = 1e-6

# Shared fixtures generated from the same population. price3 is the same draw with your price set to 3.
_DEMO = {
    "run_42": {"result": "run_result", "you_price": None, "pack": "saas"},
    "run_42_price3": {"result": "run_result_price3", "you_price": 3.0, "pack": "saas"},
}


class ResolutionError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass
class ResolvedRun:
    population: dict
    options: list
    run_result: dict
    pack: str
    project_id: Optional[str]
    origin: str  # stored | demo | engine
    trend_notes: list = field(default_factory=list)
    research_notes: list = field(default_factory=list)


def _check_run_id(run_id: str) -> None:
    if not _RUN_ID.match(run_id or ""):
        raise ResolutionError(400, "run_id may contain only letters, numbers, '_' and '-'")


def _runs_dir():
    path = project_data_dir() / "runs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _bundle_path(run_id: str):
    _check_run_id(run_id)
    return _runs_dir() / f"{run_id}.json"


def load_bundle(run_id: str) -> Optional[dict]:
    path = _bundle_path(run_id)
    if not path.is_file():
        return None
    data = json.loads(path.read_text())
    if data.get("run_id") != run_id:
        raise ResolutionError(409, "stored bundle run_id does not match the requested run")
    return data


def save_bundle(bundle: dict) -> None:
    run_id = bundle["run_id"]
    path = _bundle_path(run_id)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(bundle, indent=2, sort_keys=True))
    temporary.replace(path)


def _as_result(result: Any) -> dict:
    model = result if isinstance(result, RunResult) else RunResult.model_validate(result)
    return model.model_dump()


def _apply_you_price(options: list, price: Optional[float]) -> list:
    options = copy.deepcopy(options)
    if price is None:
        return options
    you = next((o for o in options if o.get("id") == "you" or o.get("role") == "you"), None)
    if you is None:
        raise ResolutionError(422, "scenario options have no product with id 'you'")
    you["price"] = price
    return options


def _demo_inputs(run_id: str) -> Optional[tuple[dict, list, dict, str]]:
    spec = _DEMO.get(run_id)
    if spec is None:
        return None
    population = load_fixture("population_saas")
    options = _apply_you_price(load_fixture("options_saas"), spec["you_price"])
    result = _as_result(load_fixture(spec["result"]))
    if result["run_id"] != run_id:
        raise ResolutionError(409, f"demo fixture run_id is {result['run_id']}, not {run_id}")
    return population, options, result, spec["pack"]


def assert_matches_engine(population: dict, options: list, run_result: dict) -> None:
    """Reject a result whose canonical choices are not this population, options and seed."""
    agents = population.get("agents")
    if not isinstance(agents, list) or not agents:
        raise ResolutionError(422, "population has no agents")
    if not options:
        raise ResolutionError(422, "scenario has no options")
    try:
        seed = int(run_result["seed"])
        fresh = run_scenario(agents, options, seed, repeats=1)
    except (TypeError, ValueError, KeyError) as exc:
        raise ResolutionError(422, f"scenario could not be evaluated: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 — engine failures are reported, not replaced
        raise ResolutionError(502, f"engine failed: {exc}") from exc

    if list(fresh["option_ids"]) != list(run_result["option_ids"]):
        raise ResolutionError(409, "run result option_ids do not match engine.py for this population and options")
    for oid in fresh["option_ids"]:
        stored = run_result["totals"].get(oid, {}).get("share")
        if stored is None or abs(float(stored) - float(fresh["totals"][oid]["share"])) > _SHARE_TOLERANCE:
            raise ResolutionError(409, f"run result share for '{oid}' does not match engine.py")
    stored_choices = [c["choice"] for c in run_result["choices"]]
    fresh_choices = [c["choice"] for c in fresh["choices"]]
    if stored_choices != fresh_choices:
        raise ResolutionError(409, "run result choices do not match engine.py for this seed")


def _require_project(project_id: Optional[str], *, live: bool) -> None:
    if not project_id or not live:
        return
    # Person C's lookup raises 404 when the project file is missing.
    get_persisted_project(project_id)


def _notes(body: Any, name: str, fallback: Optional[list] = None) -> list:
    if body is not None and getattr(body, name, None) is not None:
        notes = getattr(body, name)
        if not isinstance(notes, list):
            raise ResolutionError(422, f"{name} must be a list")
        return notes
    return list(fallback or [])


def _from_bundle(bundle: dict, body: Any, project_id: Optional[str]) -> ResolvedRun:
    bound = bundle.get("project_id")
    if bound and project_id and bound != project_id:
        raise ResolutionError(409, f"run '{bundle['run_id']}' belongs to project '{bound}'")
    if bound and project_id is None and body is not None and (body.population or body.options or body.run_result):
        raise ResolutionError(409, f"run '{bundle['run_id']}' belongs to project '{bound}'")
    result = _as_result(bundle["run_result"])
    return ResolvedRun(
        population=bundle["population"],
        options=bundle["options"],
        run_result=result,
        pack=bundle.get("pack") or "saas",
        project_id=bound,
        origin="stored",
        trend_notes=_notes(body, "trend_notes", bundle.get("trend_notes")),
        research_notes=_notes(body, "research_notes", bundle.get("research_notes")),
    )


def _store(resolved: ResolvedRun, project_id: Optional[str]) -> ResolvedRun:
    """Persist an engine-verified scenario so a later request can reload this run id."""
    existing = load_bundle(resolved.run_result["run_id"])
    if existing and existing.get("project_id") and project_id and existing["project_id"] != project_id:
        raise ResolutionError(
            409, f"run '{resolved.run_result['run_id']}' belongs to project '{existing['project_id']}'",
        )
    if existing and existing.get("project_id") and not project_id:
        raise ResolutionError(
            409, f"run '{resolved.run_result['run_id']}' belongs to project '{existing['project_id']}'"
        )
    bound = project_id or (existing or {}).get("project_id")
    save_bundle({
        "run_id": resolved.run_result["run_id"],
        "project_id": bound,
        "pack": resolved.pack,
        "population": resolved.population,
        "options": resolved.options,
        "run_result": resolved.run_result,
        "trend_notes": resolved.trend_notes,
        "research_notes": resolved.research_notes,
    })
    resolved.project_id = bound
    return resolved


def resolve_run(run_id: str, body: Any, *, live: bool) -> ResolvedRun:
    """Return the inputs for ``run_id``. ``body`` is a CouncilRequest or None."""
    _check_run_id(run_id)
    project_id = getattr(body, "project_id", None) if body is not None else None
    _require_project(project_id, live=live)

    supplied_result = getattr(body, "run_result", None) if body is not None else None
    supplied_population = getattr(body, "population", None) if body is not None else None
    supplied_options = getattr(body, "options", None) if body is not None else None
    explicit = supplied_result is not None or supplied_population is not None or supplied_options is not None

    if explicit:
        if not supplied_population or not supplied_options:
            raise ResolutionError(422, "population and options are required to evaluate a scenario")
        pack = getattr(body, "pack", None) or "saas"
        if supplied_result is not None:
            result = _as_result(supplied_result)
            if result["run_id"] != run_id:
                raise ResolutionError(409, f"run result run_id is {result['run_id']}, not {run_id}")
            assert_matches_engine(supplied_population, supplied_options, result)
            origin = "engine"
        else:
            agents = supplied_population.get("agents") if isinstance(supplied_population, dict) else None
            if not isinstance(agents, list) or not agents:
                raise ResolutionError(422, "population has no agents")
            seed = body.seed if getattr(body, "seed", None) is not None else supplied_population.get("seed")
            if seed is None:
                raise ResolutionError(422, "seed is required when run_result is omitted")
            try:
                fresh = run_scenario(agents, supplied_options, int(seed), repeats=1)
            except (TypeError, ValueError, KeyError) as exc:
                raise ResolutionError(422, f"scenario could not be evaluated: {exc}") from exc
            except Exception as exc:  # noqa: BLE001
                raise ResolutionError(502, f"engine failed: {exc}") from exc
            if fresh["run_id"] != run_id:
                raise ResolutionError(
                    409,
                    f"engine.py labels this draw '{fresh['run_id']}' (run_<seed>). "
                    f"The requested run id is '{run_id}'.",
                )
            result = _as_result(fresh)
            origin = "engine"
        resolved = ResolvedRun(
            population=supplied_population,
            options=supplied_options,
            run_result=result,
            pack=pack,
            project_id=project_id,
            origin=origin,
            trend_notes=_notes(body, "trend_notes"),
            research_notes=_notes(body, "research_notes"),
        )
        return _store(resolved, project_id)

    bundle = load_bundle(run_id)
    if bundle is not None:
        resolved = _from_bundle(bundle, body, project_id)
        # Stored results were checked before they were written. Do not draw the baseline again.
        return resolved

    demo = _demo_inputs(run_id)
    if demo is not None:
        population, options, result, pack = demo
        assert_matches_engine(population, options, result)
        return ResolvedRun(
            population=population,
            options=options,
            run_result=result,
            pack=pack,
            project_id=None,
            origin="demo",
            trend_notes=_notes(body, "trend_notes"),
            research_notes=_notes(body, "research_notes"),
        )

    raise ResolutionError(404, f"no stored result for run '{run_id}'")
