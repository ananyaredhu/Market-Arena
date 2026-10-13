"""Every fixture must validate against its contract; committed schemas must match the models."""
import json

import pytest

from backend.common.contracts import (
    CONTRACTS,
    AgentExplain,
    CouncilOutput,
    KitOutput,
    Option,
    Population,
    ProductProfile,
    RunResult,
)
from backend.common.fixtures import FIXTURES_DIR, load_fixture
from scripts.export_schemas import render

CASES = [
    ("population_saas", Population),
    ("run_result", RunResult),
    ("run_result_price3", RunResult),
    ("agent_explain", AgentExplain),
    ("council", CouncilOutput),
    ("kit", KitOutput),
    ("product_profile_saas", ProductProfile),
]


@pytest.mark.parametrize("name,model", CASES)
def test_fixture_matches_contract(name, model):
    model.model_validate(load_fixture(name))


@pytest.mark.parametrize("name", ["options_saas", "competitors_saas"])
def test_option_fixtures(name):
    for o in load_fixture(name):
        Option.model_validate(o)


def test_trend_notes_fixture_shape():
    data = load_fixture("trend_notes")
    from backend.common.contracts import ResearchNote, TrendNote

    for n in data["research_notes"]:
        ResearchNote.model_validate(n)
    for n in data["trend_notes"]:
        TrendNote.model_validate(n)


@pytest.mark.parametrize("name", list(CONTRACTS))
def test_committed_schema_is_current(name):
    path = FIXTURES_DIR.parent / "contracts" / f"{name}.schema.json"
    assert path.exists(), "run `make schemas`"
    assert json.loads(path.read_text()) == json.loads(render(CONTRACTS[name]))
