"""Resolve the population, options and RunResult for one council or kit request.

Sources, in order:

1. An explicit population and options in the request, evaluated with ``engine.py``.
2. A bundle stored after that evaluation. It is checked again against ``engine.py``
   and is never returned for a different project or a different scenario.
3. For a live SaaS project with no stored run, Person A's current scenario view
   (the same ``adjusted_view`` the Arena and Glass-Box use), including saved overrides.
4. With no project, the shared SaaS demo ids. Those results are computed by
   ``engine.py`` from the shared fixtures and labelled ``demo``.

Fixture JSON is never copied onto a live run. Person C does not persist project
scenarios yet, so a café project has no shared demo.
"""
from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from pydantic import ValidationError

from backend.common.contracts import RunResult
from backend.common.fixtures import load_fixture
from backend.engine.engine import run_scenario
from backend.intake.projects import get_persisted_project, project_data_dir
from backend.scenarios.context import ScenarioContext

_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,80}$")
_SHARE_TOLERANCE = 1e-6
# Same repeat count as Person A's ScenarioContext. Repeat 0 stays the canonical draw.
_ENGINE_REPEATS = ScenarioContext.repeats

# price3 is the shared SaaS draw with your price set to 3. The engine still labels it run_<seed>.
_DEMO = {
    "run_42": {"you_price": None, "pack": "saas"},
    "run_42_price3": {"you_price": 3.0, "pack": "saas"},
}

SHARED_SAAS_NOTE = (
    "Computed by engine.py from the shared SaaS scenario, including human overrides saved for this project. "
    "Project scenario storage is not implemented, so this is not a population saved on the project."
)


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
    scenario_note: Optional[str] = None


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
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ResolutionError(422, f"stored result for run '{run_id}' is not valid JSON") from exc
    if not isinstance(data, dict):
        raise ResolutionError(422, f"stored result for run '{run_id}' is not an object")
    missing = [key for key in ("run_result", "population", "options") if key not in data]
    if missing:
        raise ResolutionError(422, f"stored result for run '{run_id}' is missing {', '.join(missing)}")
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
    try:
        model = result if isinstance(result, RunResult) else RunResult.model_validate(result)
    except ValidationError as exc:
        raise ResolutionError(422, "run result does not match the RunResult contract") from exc
    return model.model_dump()


def _engine_result(agents: list, options: list, seed: int, run_id: str) -> dict:
    """Run the real engine. Only the shared price-cut alias may rename ``run_<seed>``."""
    try:
        fresh = run_scenario(agents, options, int(seed), repeats=_ENGINE_REPEATS)
    except (TypeError, ValueError, KeyError) as exc:
        raise ResolutionError(422, f"scenario could not be evaluated: {exc}") from exc
    except Exception as exc:  # noqa: BLE001 — engine failures are reported, not replaced
        raise ResolutionError(502, f"engine failed: {exc}") from exc
    natural = str(fresh.get("run_id"))
    if run_id != natural:
        if run_id != f"{natural}_price3":
            raise ResolutionError(
                409,
                f"engine.py labels this draw '{natural}' (run_<seed>). The requested run id is '{run_id}'.",
            )
        fresh = dict(fresh)
        fresh["run_id"] = run_id
    return _as_result(fresh)


def _scenario_signature(population: dict, options: list, run_result: dict) -> tuple:
    choices = tuple(c.get("choice") for c in run_result.get("choices") or [])
    option_rows = []
    for option in options:
        price = option.get("price")
        features = option.get("features") or []
        option_rows.append((
            option.get("id"),
            option.get("role"),
            None if price is None else round(float(price), 6),
            tuple(round(float(value), 6) for value in features),
        ))
    return (run_result.get("seed"), choices, tuple(option_rows), population.get("population_id"))


def _apply_you_price(options: list, price: Optional[float]) -> list:
    options = copy.deepcopy(options)
    if price is None:
        return options
    you = next((o for o in options if o.get("id") == "you" or o.get("role") == "you"), None)
    if you is None:
        raise ResolutionError(422, "scenario options have no product with id 'you'")
    you["price"] = price
    return options


def _demo_run(run_id: str) -> Optional[ResolvedRun]:
    """Shared SaaS demo. The result is an engine draw, not the fixture file."""
    spec = _DEMO.get(run_id)
    if spec is None:
        return None
    population = load_fixture("population_saas")
    options = _apply_you_price(load_fixture("options_saas"), spec["you_price"])
    result = _engine_result(population["agents"], options, int(population["seed"]), run_id)
    assert_matches_engine(population, options, result)
    return ResolvedRun(
        population=population,
        options=options,
        run_result=result,
        pack=spec["pack"],
        project_id=None,
        origin="demo",
        scenario_note=(
            "Shared demo. Computed by engine.py from the shared SaaS fixtures. "
            "Not stored on a project, and not a forecast of real demand."
        ),
    )


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


def _live_project(project_id: Optional[str], *, live: bool) -> Optional[dict]:
    if not project_id or not live:
        return None
    # Person C's lookup raises 404 when the project file is missing.
    return get_persisted_project(project_id)


def _pack_of(population: dict, requested: Optional[str]) -> str:
    pop_pack = population.get("pack") if isinstance(population, dict) else None
    pack = requested or pop_pack or "saas"
    if pop_pack and pack != pop_pack:
        raise ResolutionError(409, f"population pack is '{pop_pack}', not '{pack}'")
    return pack


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
    population = bundle["population"]
    options = bundle["options"]
    if not isinstance(population, dict) or not isinstance(options, list):
        raise ResolutionError(422, "stored population or options have the wrong shape")
    assert_matches_engine(population, options, result)
    return ResolvedRun(
        population=population,
        options=options,
        run_result=result,
        pack=_pack_of(population, bundle.get("pack")),
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
    if existing:
        previous = _scenario_signature(existing["population"], existing["options"], _as_result(existing["run_result"]))
        current = _scenario_signature(resolved.population, resolved.options, resolved.run_result)
        if previous != current:
            raise ResolutionError(
                409,
                f"run '{resolved.run_result['run_id']}' is already stored for a different population, options or seed",
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


def _shared_saas_run(run_id: str, project_id: str, body: Any) -> Optional[ResolvedRun]:
    """The scenario Arena and Glass-Box are showing for this project, when the run id matches."""
    from backend.scenarios.context import get_context
    from backend.scenarios.state import adjusted_view

    ctx = get_context(project_id)
    try:
        run, population, options = adjusted_view(ctx, run_id)
    except (TypeError, ValueError, KeyError) as exc:
        raise ResolutionError(422, f"scenario could not be evaluated: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        raise ResolutionError(502, f"engine failed: {exc}") from exc
    if run.get("run_id") != run_id:
        return None
    result = _as_result(run)
    assert_matches_engine(population, options, result)
    return ResolvedRun(
        population=population,
        options=options,
        run_result=result,
        pack=_pack_of(population, "saas"),
        project_id=project_id,
        origin="engine",
        trend_notes=_notes(body, "trend_notes"),
        research_notes=_notes(body, "research_notes"),
        scenario_note=SHARED_SAAS_NOTE,
    )


def resolve_run(run_id: str, body: Any, *, live: bool) -> ResolvedRun:
    """Return the inputs for ``run_id``. ``body`` is a CouncilRequest, KitRequest or None."""
    _check_run_id(run_id)
    project_id = getattr(body, "project_id", None) if body is not None else None
    project = _live_project(project_id, live=live)
    project_pack = (project or {}).get("profile", {}).get("pack")

    supplied_result = getattr(body, "run_result", None) if body is not None else None
    supplied_population = getattr(body, "population", None) if body is not None else None
    supplied_options = getattr(body, "options", None) if body is not None else None
    explicit = supplied_result is not None or supplied_population is not None or supplied_options is not None

    if explicit:
        if not isinstance(supplied_population, dict) or not supplied_options:
            raise ResolutionError(422, "population and options are required to evaluate a scenario")
        pack = _pack_of(supplied_population, getattr(body, "pack", None))
        if project_pack and pack != project_pack:
            raise ResolutionError(409, f"project pack is '{project_pack}', not '{pack}'")
        if supplied_result is not None:
            result = _as_result(supplied_result)
            if result["run_id"] != run_id:
                raise ResolutionError(409, f"run result run_id is {result['run_id']}, not {run_id}")
            assert_matches_engine(supplied_population, supplied_options, result)
        else:
            agents = supplied_population.get("agents")
            if not isinstance(agents, list) or not agents:
                raise ResolutionError(422, "population has no agents")
            seed = body.seed if getattr(body, "seed", None) is not None else supplied_population.get("seed")
            if seed is None:
                raise ResolutionError(422, "seed is required when run_result is omitted")
            result = _engine_result(agents, supplied_options, int(seed), run_id)
        resolved = ResolvedRun(
            population=supplied_population,
            options=supplied_options,
            run_result=result,
            pack=pack,
            project_id=project_id,
            origin="engine",
            trend_notes=_notes(body, "trend_notes"),
            research_notes=_notes(body, "research_notes"),
        )
        return _store(resolved, project_id)

    bundle = load_bundle(run_id)
    if bundle is not None:
        return _from_bundle(bundle, body, project_id)

    if project is not None:
        if project_pack == "saas":
            shared = _shared_saas_run(run_id, project["id"], body)
            if shared is not None:
                return shared
            raise ResolutionError(
                404,
                f"no stored result for run '{run_id}'. "
                "The shared SaaS scenario for this project is run_42 (or run_42_price3).",
            )
        raise ResolutionError(
            404,
            f"no stored result for run '{run_id}'. "
            f"This {project_pack} project has no saved simulation, and there is no shared {project_pack} demo. "
            "Scenario storage is not implemented yet. Submit population, options and seed to compute one.",
        )

    demo = _demo_run(run_id)
    if demo is not None:
        demo.trend_notes = _notes(body, "trend_notes")
        demo.research_notes = _notes(body, "research_notes")
        return demo

    raise ResolutionError(404, f"no stored result for run '{run_id}'")
