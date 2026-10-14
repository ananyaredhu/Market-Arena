import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def load(name: str):
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
def saas():
    return {
        "population": load("population_saas.json"),
        "options": load("options_saas.json"),
        "run_result": load("run_result_saas.json"),
    }


@pytest.fixture
def cafe():
    return {
        "population": load("population_cafe.json"),
        "options": load("options_cafe.json"),
        "run_result": load("run_result_cafe.json"),
    }


class StubAdapter:
    """Returns scripted shares; ``rule(agents, options) -> shares dict``."""

    def __init__(self, rule, source="engine"):
        self.rule = rule
        self.source = source
        self.calls = 0

    def evaluate(self, agents, options, seed):
        from backend.council.engine_adapter import EngineEvaluation

        self.calls += 1
        return EngineEvaluation(shares=self.rule(agents, options), source=self.source)


@pytest.fixture
def stub_adapter():
    return StubAdapter
