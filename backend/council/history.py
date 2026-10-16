"""Council decision history for one project.

Reads persisted run bundles and Council snapshots. It does not call the
simulation engine. A missing Council snapshot stays missing.
"""
from __future__ import annotations

import json
import math
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from backend.council.run_inputs import _check_run_id
from backend.intake.projects import project_data_dir

_FILE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,80}\.json$")
_LEVELS = {"low": 0, "medium": 1, "high": 2}
_NOT_REAL = (
    "These figures are simulated outcomes under the stored assumptions. "
    "They are not observed sales or real customer behaviour."
)
_NO_CAUSE = (
    "A difference in the stored scenario is not proof that it caused the change in share or in the Council wording."
)


class HistoryError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _council_dir():
    path = project_data_dir() / "council"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _council_path(run_id: str):
    _check_run_id(run_id)
    return _council_dir() / f"{run_id}.json"


def save_council_record(payload: dict) -> None:
    """Keep the Council response that was just computed. Later history reads this file."""
    run_id = payload.get("run_id")
    if not isinstance(run_id, str) or not run_id:
        return
    record = {
        "run_id": run_id,
        "project_id": payload.get("project_id"),
        "pack": payload.get("pack"),
        "scenario_origin": payload.get("scenario_origin"),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "verdict": payload.get("verdict"),
        "confidence": payload.get("confidence"),
        "fragility": payload.get("fragility"),
        "competitor_reaction": payload.get("competitor_reaction"),
        "baseline_share": payload.get("baseline_share"),
        "measured": payload.get("measured"),
        "scenario_note": payload.get("scenario_note"),
    }
    path = _council_path(run_id)
    # A second council request for the same run (for example a dev double-mount)
    # must not share this temporary name, or the later replace loses the file.
    temporary = path.with_name(f"{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(record, indent=2, sort_keys=True))
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def _finite(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        return None
    return float(value)


def _you_metrics(run_result: Any) -> dict:
    """Canonical share and range from the stored RunResult. Missing numbers stay missing."""
    totals = run_result.get("totals") if isinstance(run_result, dict) else None
    you = totals.get("you") if isinstance(totals, dict) else None
    if not isinstance(you, dict):
        return {
            "share": None, "p10": None, "p50": None, "p90": None,
            "metrics_note": "stored run has no totals for 'you'",
        }
    share, p10, p50, p90 = (_finite(you.get(key)) for key in ("share", "p10", "p50", "p90"))
    note = None if share is not None else "stored run has no numeric share for 'you'"
    return {"share": share, "p10": p10, "p50": p50, "p90": p90, "metrics_note": note}


def _move(reaction: Any) -> Optional[dict]:
    if not isinstance(reaction, dict):
        return None
    competitor_id = reaction.get("competitor_id")
    move = reaction.get("move")
    if not competitor_id or not move:
        return None
    return {
        "competitor_id": competitor_id,
        "move": move,
        "effect_on_share": _finite(reaction.get("effect_on_share")),
    }


def _load_council(run_id: str, project_id: str) -> tuple[Optional[dict], Optional[str]]:
    path = project_data_dir() / "council" / f"{run_id}.json"
    if not path.is_file():
        return None, None
    try:
        record = json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None, "saved Council record is unreadable"
    if not isinstance(record, dict) or record.get("run_id") != run_id:
        return None, "saved Council record does not match this run"
    # A snapshot with no project, or a different project, must not be shown on this project.
    if record.get("project_id") != project_id:
        return None, "saved Council record belongs to a different project"
    return record, None


def _runs_dir():
    return project_data_dir() / "runs"


def _read_bundle(path) -> tuple[Optional[dict], Optional[str]]:
    try:
        data = json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None, "stored run is not valid JSON"
    if not isinstance(data, dict):
        return None, "stored run is not an object"
    return data, None


def _entry(bundle: dict, project_id: str) -> dict:
    run_id = bundle.get("run_id")
    result = bundle.get("run_result") if isinstance(bundle.get("run_result"), dict) else {}
    metrics = _you_metrics(result)
    council, council_problem = _load_council(run_id, project_id)
    origin = bundle.get("scenario_origin") or (council or {}).get("scenario_origin")
    label = "demo" if origin == "demo" else "live"
    created_at = bundle.get("created_at") if isinstance(bundle.get("created_at"), str) else None
    reaction = _move((council or {}).get("competitor_reaction"))
    limitations = []
    if council is None:
        missing = "Council output has not been saved for this run. "
        missing += "Open the Council to record it. History does not rerun the simulation."
        limitations.append(council_problem or missing)
    if metrics["metrics_note"]:
        limitations.append(metrics["metrics_note"])
    return {
        "run_id": run_id,
        "scenario_id": bundle.get("scenario_id") if isinstance(bundle.get("scenario_id"), str) else None,
        "project_id": project_id,
        "pack": bundle.get("pack") if isinstance(bundle.get("pack"), str) else None,
        "created_at": created_at,
        "council_recorded_at": (council or {}).get("recorded_at"),
        "run_label": label,
        "share": metrics["share"],
        "p10": metrics["p10"],
        "p50": metrics["p50"],
        "p90": metrics["p90"],
        "verdict": (council or {}).get("verdict"),
        "confidence": (council or {}).get("confidence") if (council or {}).get("confidence") in _LEVELS else None,
        "competitor_move": reaction,
        "council_available": council is not None and bool((council or {}).get("verdict")),
        "limitations": limitations,
    }


def list_history(project_id: str) -> dict:
    """Runs stored for this project, plus a Council snapshot when one was saved."""
    entries = []
    problems = []
    folder = _runs_dir()
    paths = sorted(folder.glob("*.json")) if folder.is_dir() else []
    for path in paths:
        if not _FILE.match(path.name):
            continue
        bundle, error = _read_bundle(path)
        run_id = path.stem
        if error or bundle is None:
            continue
        if bundle.get("project_id") != project_id:
            continue
        if bundle.get("run_id") != run_id:
            problems.append({"run_id": run_id, "detail": "stored bundle run_id does not match the file name"})
            continue
        result = bundle.get("run_result")
        if not isinstance(result, dict) or result.get("run_id") != run_id:
            problems.append({"run_id": run_id, "detail": "stored run result is missing or its run_id does not match"})
            continue
        entries.append(_entry(bundle, project_id))

    def stamp(entry: dict) -> str:
        return entry.get("created_at") or entry.get("council_recorded_at") or ""

    entries.sort(key=lambda entry: (stamp(entry) == "", stamp(entry), entry["run_id"]))
    return {
        "project_id": project_id,
        "entries": entries,
        "problems": problems,
        "ordering": (
            "created_at when the run bundle stores it, otherwise the Council snapshot time, otherwise run id"
        ),
        "note": _NOT_REAL,
    }


def _find(project_id: str, run_id: str) -> dict:
    _check_run_id(run_id)
    path = _runs_dir() / f"{run_id}.json"
    if not path.is_file():
        raise HistoryError(404, f"no stored result for run '{run_id}'")
    bundle, error = _read_bundle(path)
    if error or bundle is None:
        raise HistoryError(422, f"stored result for run '{run_id}' is not valid JSON")
    if bundle.get("project_id") != project_id:
        raise HistoryError(404, f"run '{run_id}' is not stored for this project")
    if bundle.get("run_id") != run_id or not isinstance(bundle.get("run_result"), dict):
        raise HistoryError(422, f"stored result for run '{run_id}' is malformed")
    if bundle["run_result"].get("run_id") != run_id:
        raise HistoryError(422, f"stored result for run '{run_id}' is malformed")
    return _entry(bundle, project_id)


def _share_change(base: dict, other: dict) -> dict:
    left, right = base.get("share"), other.get("share")
    if left is None or right is None:
        return {
            "value": None,
            "comparable": False,
            "detail": "Simulated share is missing on one of the runs, so no difference is calculated.",
        }
    return {
        "value": right - left,
        "base": left,
        "other": right,
        "comparable": True,
        "detail": "Change in the stored canonical simulated share (other minus base). Not a change in real demand.",
    }


def _text_change(base: Optional[str], other: Optional[str], missing: str) -> dict:
    if not base or not other:
        return {"changed": None, "base": base, "other": other, "comparable": False, "detail": missing}
    return {"changed": base != other, "base": base, "other": other, "comparable": True, "detail": None}


def _confidence_change(base: Optional[str], other: Optional[str]) -> dict:
    if base not in _LEVELS or other not in _LEVELS:
        return {
            "base": base,
            "other": other,
            "steps": None,
            "comparable": False,
            "detail": "Confidence was not saved for both runs, so it is not compared.",
        }
    return {
        "base": base,
        "other": other,
        "steps": _LEVELS[other] - _LEVELS[base],
        "comparable": True,
        "detail": (
            "Confidence is a label for how robust the simulation is to its own assumptions. "
            "A step up or down is not a statistical interval and not a real-world outcome."
        ),
    }


def _move_change(base: Optional[dict], other: Optional[dict]) -> dict:
    if base is None or other is None:
        return {
            "base": base,
            "other": other,
            "changed": None,
            "comparable": False,
            "detail": "A recommended competitor move was not saved for both runs.",
        }
    changed = (base.get("competitor_id"), base.get("move")) != (other.get("competitor_id"), other.get("move"))
    return {
        "base": base,
        "other": other,
        "changed": changed,
        "comparable": True,
        "detail": (
            "This is a change in the Council's recommended simulated response, not an observed competitor action."
        ),
    }


def _option_rows(options: Any) -> dict:
    rows = {}
    if not isinstance(options, list):
        return rows
    for option in options:
        if not isinstance(option, dict) or not option.get("id"):
            continue
        price = _finite(option.get("price"))
        features = option.get("features") if isinstance(option.get("features"), list) else None
        rows[option["id"]] = {
            "role": option.get("role"),
            "label": option.get("label"),
            "price": price,
            "features": features,
        }
    return rows


def _bundle_body(run_id: str) -> dict:
    path = _runs_dir() / f"{run_id}.json"
    data, error = _read_bundle(path)
    if error or data is None:
        return {}
    return data


def _scenario_differences(base_id: str, other_id: str) -> list[dict]:
    base, other = _bundle_body(base_id), _bundle_body(other_id)
    diffs = []
    if base.get("pack") != other.get("pack"):
        diffs.append({
            "field": "pack",
            "base": base.get("pack"),
            "other": other.get("pack"),
            "statement": (
                f"Stored pack is {base.get('pack')!s} on the base run and {other.get('pack')!s} on the other run."
            ),
        })
    base_seed = (base.get("run_result") or {}).get("seed") if isinstance(base.get("run_result"), dict) else None
    other_seed = (other.get("run_result") or {}).get("seed") if isinstance(other.get("run_result"), dict) else None
    if base_seed != other_seed:
        diffs.append({
            "field": "seed",
            "base": base_seed,
            "other": other_seed,
            "statement": f"Stored seed is {base_seed} on the base run and {other_seed} on the other run.",
        })
    left = _option_rows(base.get("options"))
    right = _option_rows(other.get("options"))
    for option_id in sorted(set(left) | set(right)):
        a, b = left.get(option_id), right.get(option_id)
        if a is None or b is None:
            diffs.append({
                "field": f"option:{option_id}",
                "base": a,
                "other": b,
                "statement": f"Option '{option_id}' is stored on only one of the two runs.",
            })
            continue
        if a.get("price") != b.get("price"):
            diffs.append({
                "field": f"price:{option_id}",
                "base": a.get("price"),
                "other": b.get("price"),
                "statement": (
                    f"Stored price of '{option_id}' is {a.get('price')} on the base run "
                    f"and {b.get('price')} on the other run."
                ),
            })
        if a.get("features") != b.get("features"):
            diffs.append({
                "field": f"features:{option_id}",
                "base": a.get("features"),
                "other": b.get("features"),
                "statement": f"Stored feature vector of '{option_id}' differs between the two runs.",
            })
    return diffs


def compare_runs(project_id: str, base_id: str, other_id: str) -> dict:
    if base_id == other_id:
        raise HistoryError(422, "choose two different runs")
    base = _find(project_id, base_id)
    other = _find(project_id, other_id)
    scenario = _scenario_differences(base_id, other_id)
    limitations = [_NOT_REAL, _NO_CAUSE]
    if not base["council_available"] or not other["council_available"]:
        limitations.append(
            "Council wording is compared only where a snapshot was saved. Missing verdicts are left blank."
        )
    if not scenario:
        limitations.append(
            "No stored pack, seed, price, or feature difference was found. "
            "That does not mean the runs are identical in every input."
        )
    return {
        "project_id": project_id,
        "base": base,
        "other": other,
        "observed": {"share": _share_change(base, other)},
        "interpretation": {
            "verdict": _text_change(
                base.get("verdict"), other.get("verdict"), "A Council verdict was not saved for both runs.",
            ),
            "confidence": _confidence_change(base.get("confidence"), other.get("confidence")),
            "competitor_move": _move_change(base.get("competitor_move"), other.get("competitor_move")),
        },
        "scenario_differences": scenario,
        "limitations": limitations,
    }
