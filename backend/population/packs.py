"""Load and validate industry packs from /packs/<name>.yaml."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import ValidationError

from backend.population.models import PackSpec

PACKS_DIR = Path(__file__).resolve().parents[2] / "packs"


class PackError(ValueError):
    """The pack is missing, unreadable or fails validation. The message says what to fix."""


def available_packs() -> list[str]:
    return sorted(p.stem for p in PACKS_DIR.glob("*.yaml"))


@lru_cache(maxsize=None)
def load_pack(name: str) -> PackSpec:
    path = PACKS_DIR / f"{name}.yaml"
    if not path.exists():
        raise PackError(f"unknown pack '{name}' (available: {available_packs()})")
    raw = yaml.safe_load(path.read_text())
    if not isinstance(raw, dict):
        raise PackError(f"{path.name} is not a YAML mapping")

    outside = raw.get("outside_option")  # either {id, label} (current format) or a plain label string
    outside_id = outside.get("id", "outside") if isinstance(outside, dict) else "outside"
    data = {**raw, "outside_id": outside_id, "competitors": raw.get("competitor_archetypes", [])}
    # Older packs list archetype names only; keep just full option specs.
    data["competitors"] = [c for c in data["competitors"] if isinstance(c, dict)]
    try:
        return PackSpec.model_validate(data)
    except ValidationError as e:
        raise PackError(f"{path.name} is not a valid pack:\n{e}") from e
