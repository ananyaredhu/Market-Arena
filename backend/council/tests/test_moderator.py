"""Moderator / CouncilOutput tests (Person B)."""
from __future__ import annotations

from backend.council.advocate import run_advocate
from backend.council.claims import Evidence, unsupported_numbers
from backend.council.engine_adapter import MockEngineAdapter
from backend.council.moderator import build_council, decide_confidence, enforce_grounding
from backend.council.schemas import CouncilOutput, Risk
from backend.council.service import run_council
from backend.council.strategist import run_strategist
from backend.kit.packs import kit_content


def test_council_validates_against_schema(saas):
    result = run_council(
        saas["run_result"], saas["population"], saas["options"], "saas",
        adapter=MockEngineAdapter(),
    )
    out = result["council"]
    assert isinstance(out, CouncilOutput)
    # Round-trip through the frozen shape.
    CouncilOutput.model_validate(out.model_dump())
    assert out.confidence in ("low", "medium", "high")
    assert 0.0 <= out.fragility <= 1.0
    assert len(out.risks) <= 3
    assert len(out.experiments) <= 3
    assert out.engine_source == "mock"
    assert any("simulated" in lim.lower() for lim in out.limitations)


def test_cafe_council_validates(cafe):
    out = run_council(
        cafe["run_result"], cafe["population"], cafe["options"], "cafe",
        adapter=MockEngineAdapter(),
    )["council"]
    CouncilOutput.model_validate(out.model_dump())
    assert out.run_id == cafe["run_result"]["run_id"]


def test_claims_cannot_cite_absent_numbers(saas):
    adapter = MockEngineAdapter()
    agents, options = saas["population"]["agents"], saas["options"]
    strategist = run_strategist(agents, options, adapter, seed=42)
    advocate = run_advocate(agents, options, adapter, seed=42)
    out = build_council(
        saas["run_result"], strategist, advocate,
        population=saas["population"], options=options,
        experiment_library=kit_content("saas")["experiment_library"],
        context={"price": "S$9", "price_low": "S$7.20"},
    )
    # Build a thin evidence set and force a bad claim through enforce_grounding.
    thin = Evidence()
    thin.add(0.0)
    poisoned = out.model_copy(update={"verdict": "Share will be 0.99 forever."})
    cleaned = enforce_grounding(poisoned, thin)
    assert "withheld" in cleaned.verdict.lower()
    assert unsupported_numbers(cleaned.verdict, thin) == []


def test_confidence_caps_for_mock():
    from backend.council.advocate import AdvocateReport
    from backend.council.strategist import StrategistReport

    advocate = AdvocateReport(
        status="ok", engine_source="mock", seed=1, baseline_share=0.2, baseline_leader="you",
        perturbations=[], fragility=0.1,
    )
    # Pretend all three parameters were tested cleanly.
    from backend.council.advocate import Perturbation

    advocate.perturbations = [
        Perturbation(parameter=p, factor=0.8, direction="-20%", assumption="x", status="ok")
        for p in ("budget", "alpha", "brand")
    ]
    strategist = StrategistReport(status="ok", engine_source="mock", seed=1, baseline_share=0.2)
    level, reasons = decide_confidence(0.1, "mock", advocate, strategist, {"p10": 0.18, "p50": 0.2, "p90": 0.22})
    assert level == "low"
    assert any("mock" in r.lower() for r in reasons)


def test_llm_wording_rejected_on_bad_numbers(saas):
    from backend.council.wording import CallableLLMWording

    class BadLLM:
        def __call__(self, prompt: str) -> str:
            return "Simulated share will jump to 0.99 next quarter."

    out = run_council(
        saas["run_result"], saas["population"], saas["options"], "saas",
        adapter=MockEngineAdapter(), wording=CallableLLMWording(BadLLM()),
    )["council"]
    assert "0.99" not in out.verdict
    assert any("rejected" in lim.lower() or "template" in lim.lower() for lim in out.limitations)
