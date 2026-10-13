"""Data-level smoke tests for CouncilPanel fixtures (no Node required)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[4] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from council.schemas import CouncilOutput, KitOutput

HERE = Path(__file__).resolve().parents[1]
FIXTURES = HERE / "fixtures"


@pytest.mark.parametrize("pack", ["saas", "cafe"])
def test_frontend_fixtures_validate(pack):
    council = CouncilOutput.model_validate(json.loads((FIXTURES / f"council_{pack}.json").read_text()))
    kit = KitOutput.model_validate(json.loads((FIXTURES / f"kit_{pack}.json").read_text()))
    assert council.verdict
    assert len(council.risks) <= 3
    assert kit.hypotheses
    assert kit.assets.landing_copy
    assert kit.assets.telegram_variants


def test_standalone_html_exists_and_embeds_fixtures():
    html_path = HERE / "council_standalone.html"
    assert html_path.exists(), "run: python frontend/components/council/build_standalone.py"
    text = html_path.read_text()
    assert "data-testid=\"council-panel\"" in text or "council-panel" in text
    assert "council_saas" not in text  # fixtures are inlined as JSON, not filenames
    assert "StudyFlow" in text or "run_saas_fixture" in text
    assert "__councilSmoke" in text
    assert "Copy Markdown export" in text
