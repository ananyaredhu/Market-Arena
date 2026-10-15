# Contracts changelog

Source of truth: `backend/common/contracts.py` (Pydantic). JSON schemas in this folder are generated
with `make schemas` and checked in CI. Change rules: all three people agree, add fields as OPTIONAL
only, update the fixtures in the same commit, add a line here.

## 2026-10-14: optional `Population.generation` (Person A, population generator)
- `generation`: free-form note on how the population was made (`source`: `llm` or `template`, optional
  `fallback_reason`, validation summary). Optional; consumers may ignore it.

## 2026-10-14: optional fields on Choice (Person A, engine.py)
- `Choice.p_choice` (model probability of the chosen option) and `Choice.locked` (human override pinned the
  choice). Both optional; `engine_ref.py` does not emit them. Existing consumers can ignore them.

## 2026-10-13: initial lock (Phase 0)
- Option, Population (Segment, Agent), RunResult (Totals, Choice), AgentExplain, CouncilOutput,
  KitOutput, ProductProfile.
- v2 optional fields: `Population.geography` (default `SG`), `Population.evidence_snapshot_id`,
  `Segment.sources`, `CouncilOutput.trend_context`, `ProductProfile.geography`; new
  `ResearchNote` and `TrendNote` shapes.
- Scale rule: `alpha` is price sensitivity per currency unit, roughly 0.05 to 0.3 (not 1.1).
- `Choice.gap` can be negative because the draw is stochastic; `Choice.prev_choice` is filled by the
  orchestrator by diffing against the previous run.
