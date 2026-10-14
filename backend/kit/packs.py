"""Loads Experiment Kit content per Industry Pack.

* ``cafe`` reads the ``kit`` section of ``packs/cafe.yaml`` (Person B).
* ``saas`` reads ``backend/kit/content/saas.yaml``, because ``packs/saas.yaml``
  belongs to Person A and holds only segment priors.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
SOURCES = {
    "cafe": REPO / "packs" / "cafe.yaml",
    "saas": BACKEND / "kit" / "content" / "saas.yaml",
}


class UnknownPackError(KeyError):
    pass


@lru_cache(maxsize=None)
def load_pack(pack: str) -> dict:
    if pack not in SOURCES:
        raise UnknownPackError(f"no Experiment Kit content for pack '{pack}' (known: {sorted(SOURCES)})")
    data = yaml.safe_load(SOURCES[pack].read_text())
    if not isinstance(data, dict) or "kit" not in data:
        raise ValueError(f"{SOURCES[pack]} has no 'kit' section")
    return data


def kit_content(pack: str) -> dict:
    return load_pack(pack)["kit"]


def outside_label(pack: str) -> str:
    data = load_pack(pack)
    outside = data.get("outside_option")
    if isinstance(outside, dict):
        return outside.get("label", "doing nothing")
    return outside or "doing nothing"
