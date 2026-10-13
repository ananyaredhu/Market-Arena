"""Experiment Kit tests (Person B)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from council.engine_adapter import MockEngineAdapter
from council.schemas import KitOutput
from council.service import run_council, run_kit
from kit.generator import KitValidationError, generate_kit, validate_kit
from kit.packs import kit_content, load_pack


@pytest.fixture
def saas_council():
    from council.tests.conftest import load

    population, options, run_result = (
        load("population_saas.json"), load("options_saas.json"), load("run_result_saas.json"),
    )
    council = run_council(run_result, population, options, "saas", adapter=MockEngineAdapter())["council"]
    return council, options


@pytest.fixture
def cafe_council():
    from council.tests.conftest import load

    population, options, run_result = (
        load("population_cafe.json"), load("options_cafe.json"), load("run_result_cafe.json"),
    )
    council = run_council(run_result, population, options, "cafe", adapter=MockEngineAdapter())["council"]
    return council, options


def test_saas_kit_valid_and_nonempty(saas_council):
    council, options = saas_council
    kit = run_kit(council, "saas", options)
    KitOutput.model_validate(kit.model_dump())
    validate_kit(kit)
    assert 3 <= len(kit.hypotheses) <= 5
    assert 8 <= len(kit.assets.survey) <= 12
    assert len(kit.assets.ad_variants) >= 2
    assert len(kit.assets.telegram_variants) == 2
    assert kit.assets.landing_copy
    assert kit.assets.interview_script
    assert kit.assets.tracking_plan is not None
    assert all("Proposed test threshold" in h for h in kit.hypotheses)


def test_cafe_kit_valid_and_nonempty(cafe_council):
    council, options = cafe_council
    kit = run_kit(council, "cafe", options)
    KitOutput.model_validate(kit.model_dump())
    validate_kit(kit)
    assert kit.assets.offline.flyer
    assert kit.assets.offline.checklist
    assert kit.assets.offline.price_board_test
    assert "QR" in kit.assets.offline.flyer


def test_thresholds_labelled_as_proposed(saas_council):
    council, options = saas_council
    kit = run_kit(council, "saas", options)
    for exp_title in (e.title for e in council.experiments):
        assert exp_title  # council experiments exist
    for threshold in (e.pass_threshold for e in council.experiments):
        assert threshold.startswith("Proposed test threshold")


def test_pack_content_loads():
    assert "kit" in load_pack("saas")
    assert "experiment_library" in kit_content("cafe")
    assert load_pack("cafe")["evidence"] == "illustrative_assumption"


def test_invalid_price_raises(saas_council):
    council, _ = saas_council
    with pytest.raises(KitValidationError):
        generate_kit(council, "saas", {"id": "you", "label": "X", "price": "free"})
