"""Saving and loading evidence snapshots, and the Council-facing view of one (Person A).

Run snapshots live in data/evidence/ (git-ignored). Demo snapshots, produced by one real live run and then committed,
live in fixtures/evidence/ so the demo works offline. A snapshot id can only be a plain slug, so an id can never be
used to read other files.
"""
from __future__ import annotations

import re
from pathlib import Path

from backend.evidence.models import EvidenceSnapshot

ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = ROOT / "data" / "evidence"
DEMO_DIR = ROOT / "fixtures" / "evidence"
_SAFE = re.compile(r"^[A-Za-z0-9_.-]{1,80}$")

EFFECT_TEXT = {"budget_down": "budget -10%", "budget_up": "budget +10%",
               "price_sensitivity_up": "price sensitivity +15%", "price_sensitivity_down": "price sensitivity -15%"}


def _check(snapshot_id: str) -> str:
    if not _SAFE.match(snapshot_id) or snapshot_id.startswith("."):
        raise KeyError(snapshot_id)
    return snapshot_id


def save(snap: EvidenceSnapshot, directory: Path | None = None) -> Path:
    d = directory or RUN_DIR
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{_check(snap.snapshot_id)}.json"
    f.write_text(snap.model_dump_json(indent=2))
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
    its source url and verbatim quote. Only verified items are in a snapshot, so everything here is quotable."""
    return {
        "geography": snap.geography,
        "evidence_snapshot_id": snap.snapshot_id,
        "research_notes": [
            {"topic": f.kind, "note": f.claim, "source_url": f.url, "quote": f.quote} for f in snap.findings
        ],
        "trend_notes": [
            {"note": n.note, "source_url": n.url, "quote": n.quote, "effect": EFFECT_TEXT.get(n.effect)}
            for n in snap.trend_notes
        ],
    }
