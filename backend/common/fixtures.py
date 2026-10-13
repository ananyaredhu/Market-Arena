"""Load fixture JSON from /fixtures (used by mock mode and tests)."""
import json
from functools import lru_cache
from pathlib import Path

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"


@lru_cache(maxsize=None)
def load_fixture(name: str):
    return json.loads((FIXTURES_DIR / f"{name}.json").read_text())
