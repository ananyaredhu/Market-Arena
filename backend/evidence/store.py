"""Saving and loading evidence snapshots, and the Council-facing view of one (Person A).

Saving a snapshot also files its findings in the Resources library (data/resources/, see resources.py).
Run snapshots live in data/evidence/ (git-ignored). Demo snapshots, produced by one real live run and then committed,
live in fixtures/evidence/ so the demo works offline. A snapshot id can only be a plain slug, so an id can never be
used to read other files.
"""
from __future__ import annotations

import re
from pathlib import Path

from backend.evidence import resources
from backend.evidence.models import EvidenceSnapshot

ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = ROOT / "data" / "evidence"
DEMO_DIR = ROOT / "fixtures" / "evidence"
_SAFE = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")


SEED_RESOURCES_DIR = ROOT / "fixtures" / "resources"  # committed demo copy, so a fresh clone's library is not empty


def resources_dir() -> Path:
    """Where the Resources library lives: next to the run snapshots."""
    return RUN_DIR.parent / "resources"


def _check(snapshot_id: str) -> str:
    if not _SAFE.match(snapshot_id) or snapshot_id.startswith("."):
        raise KeyError(snapshot_id)
    return snapshot_id


def save(snap: EvidenceSnapshot, directory: Path | None = None) -> Path:
    d = directory or RUN_DIR
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{_check(snap.snapshot_id)}.json"
    f.write_text(snap.model_dump_json(indent=2))
    resources.add(snap, d.parent / "resources")
    return f


def load(snapshot_id: str, directories: list[Path] | None = None) -> EvidenceSnapshot:
    """Raise KeyError if no such snapshot exists in the run or demo folders."""
    name = _check(snapshot_id)
    for d in directories or [RUN_DIR, DEMO_DIR]:
        f = d / f"{name}.json"
        if f.exists():
            return EvidenceSnapshot.model_validate_json(f.read_text())
    raise KeyError(snapshot_id)


def council_context(snap: EvidenceSnapshot) -> dict:
    """The snapshot as B's Council expects it (fixtures/trend_notes.json): research notes and trend notes, each with
    its source url and verbatim quote. Only verified items are in a snapshot, so everything here is quotable.
    These are reference material: they were read from web pages and never changed the simulation."""
    return {
        "geography": snap.geography,
        "evidence_snapshot_id": snap.snapshot_id,
        "reference_only": True,
        "research_notes": [
            {"topic": f.kind, "note": f.claim, "source_url": f.url, "quote": f.quote} for f in snap.findings
        ],
        "trend_notes": [
            {"note": n.note, "source_url": n.url, "quote": n.quote, "effect": None}
            for n in snap.trend_notes
        ],
    }
