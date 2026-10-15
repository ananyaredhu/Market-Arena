"""JSON persistence for real project scenarios and Person B compatible run bundles."""
from __future__ import annotations

import json
import os
import re
import tempfile
import uuid
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from backend.common.contracts import RunResult
from backend.intake.projects import project_data_dir

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,100}$")


class StoredDataError(ValueError):
    """A stored scenario or run is malformed or inconsistent."""


class RecordCollisionError(StoredDataError):
    """A new scenario or run cannot replace a record with the same identifier."""


def _read(path: Path, kind: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise StoredDataError(f"stored {kind} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise StoredDataError(f"stored {kind} must be an object")
    return value


def _write_new(path: Path, data: dict[str, Any]) -> None:
    """Install a complete JSON document atomically without replacing an existing ID."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            # A hard link is an atomic create-if-absent on the same filesystem.
            # Readers see either no record or the fully written record.
            os.link(temporary, path)
        except FileExistsError as exc:
            raise RecordCollisionError(f"a record with id '{path.stem}' already exists") from exc
    finally:
        temporary.unlink(missing_ok=True)


def _path(folder: str, identifier: str) -> Path:
    if not _ID.fullmatch(identifier or ""):
        raise StoredDataError("identifier may contain only letters, numbers, '_' and '-'")
    return project_data_dir() / folder / f"{identifier}.json"


def new_scenario_id() -> str:
    return f"scn_{uuid.uuid4().hex}"


def new_run_id() -> str:
    return f"run_{uuid.uuid4().hex}"


def save_scenario(scenario: dict[str, Any]) -> None:
    _write_new(_path("scenarios", scenario["id"]), scenario)


def load_scenario(scenario_id: str) -> dict[str, Any] | None:
    path = _path("scenarios", scenario_id)
    if not path.is_file():
        return None
    scenario = _read(path, "scenario")
    if scenario.get("id") != scenario_id:
        raise StoredDataError("stored scenario id does not match the requested id")
    return scenario


def save_run_bundle(bundle: dict[str, Any]) -> None:
    """Match Person B's run_inputs bundle: run_id, project_id, pack, population, options, run_result.

    Additional metadata is allowed by that interface and does not change Council/Kit resolution.
    """
    result = RunResult.model_validate(bundle["run_result"]).model_dump(mode="json")
    if result["run_id"] != bundle["run_id"]:
        raise StoredDataError("bundle and RunResult run_id values must match")
    canonical = {**bundle, "run_result": result}
    _write_new(_path("runs", canonical["run_id"]), canonical)


def load_run_bundle(run_id: str) -> dict[str, Any] | None:
    path = _path("runs", run_id)
    if not path.is_file():
        return None
    bundle = _read(path, "run bundle")
    if bundle.get("run_id") != run_id:
        raise StoredDataError("stored bundle run_id does not match the requested run")
    required = ("project_id", "pack", "population", "options", "run_result")
    missing = [key for key in required if key not in bundle]
    if missing:
        raise StoredDataError(f"stored run bundle is missing {', '.join(missing)}")
    try:
        result = RunResult.model_validate(bundle["run_result"]).model_dump(mode="json")
    except ValidationError as exc:
        raise StoredDataError("stored run result does not match the RunResult contract") from exc
    if result["run_id"] != run_id:
        raise StoredDataError("stored bundle and RunResult run_id values do not match")
    bundle["run_result"] = result
    return bundle
