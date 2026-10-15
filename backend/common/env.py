"""Tiny .env loader (no extra dependency). Call `load_env()` once at process start.

Reads KEY=VALUE lines from <repo>/.env into os.environ. It never overrides a variable that is already set
(so a shell `export` or a test's monkeypatch always wins) and it never prints values.
"""
from __future__ import annotations

import os
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


def load_env(path: Path | None = None) -> list[str]:
    """Load the file; return the names of the variables it set (names only, never values)."""
    path = path or ENV_FILE
    if not path.exists():
        return []
    loaded = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
            loaded.append(key)
    return loaded
