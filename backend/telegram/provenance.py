"""Read existing project/run contracts and regenerate Kit context via public services."""

import hashlib
import json
import re

from fastapi import HTTPException

from backend.common.money import currency_of
from backend.council.engine_adapter import get_default_adapter
from backend.council.service import run_council, run_kit
from backend.council.wording import TemplateWording
from backend.intake.projects import get_persisted_project
from backend.orchestrator.storage import StoredDataError, load_run_bundle

ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,100}$")


def identifier(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise HTTPException(422, "Valid project_id and run_id are required")
    return value


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def persisted_run(project_id, run_id):
    identifier(project_id)
    identifier(run_id)
    try:
        project = get_persisted_project(project_id)
        bundle = load_run_bundle(run_id)
    except HTTPException:
        raise
    except (StoredDataError, ValueError, KeyError, TypeError, OSError):
        raise HTTPException(422, "Persisted project or run is invalid") from None
    if project["id"] != project_id:
        raise HTTPException(409, "Persisted project ID does not match")
    if bundle is None:
        raise HTTPException(404, "Persisted run not found; demo runs are not campaign sources")
    if bundle["project_id"] != project_id or bundle["pack"] != project["profile"]["pack"]:
        raise HTTPException(409, "Run does not belong to this project and pack")
    return bundle


def source_for(body):
    bundle = persisted_run(body.get("project_id"), body.get("run_id"))
    index = body.get("hypothesis_index")
    if type(index) is not int or index < 0:
        raise HTTPException(422, "Select a Kit hypothesis_index")
    try:
        council = run_council(
            bundle["run_result"],
            bundle["population"],
            bundle["options"],
            bundle["pack"],
            adapter=get_default_adapter("engine"),
            wording=TemplateWording(),
            trend_notes=bundle.get("trend_notes"),
            research_notes=bundle.get("research_notes"),
        )
        kit = run_kit(council["council"], bundle["pack"], bundle["options"],
                      currency_of(bundle["population"], "") or None).model_dump(mode="json")
    except Exception:
        raise HTTPException(422, "Could not derive Experiment Kit from persisted run") from None
    expected = {"hypotheses": kit["hypotheses"], "telegram_variants": kit["assets"]["telegram_variants"]}
    if body.get("kit_context") != expected:
        raise HTTPException(409, "Kit source is missing or stale; reload the Experiment Kit")
    if index >= len(kit["hypotheses"]):
        raise HTTPException(422, "hypothesis_index is outside the source Kit")
    return {
        "version": 1,
        "source": "persisted_run_public_kit_services",
        "pack": bundle["pack"],
        "run_digest": digest(bundle),
        "kit_digest": digest(kit),
        "kit": kit,
        "hypothesis_index": index,
        "hypothesis": kit["hypotheses"][index],
    }


def check_scope(row, project_id, run_id):
    identifier(project_id)
    identifier(run_id)
    if not row["project_id"] or not row["kit_source"]:
        raise HTTPException(409, "Legacy campaign lacks verified provenance; create a new campaign")
    if row["project_id"] != project_id or row["run_id"] != run_id:
        raise HTTPException(404, "Campaign not found in this project/run")
    bundle = persisted_run(project_id, run_id)
    try:
        source = json.loads(row["kit_source"])
        valid = source["version"] == 1 and digest(bundle) == source["run_digest"]
    except (ValueError, KeyError, TypeError):
        valid = False
    if not valid:
        raise HTTPException(409, "Campaign source run changed or provenance is invalid")
