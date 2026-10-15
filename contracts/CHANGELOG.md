# Contracts changelog

Source of truth: `backend/common/contracts.py` (Pydantic). JSON schemas in this folder are generated
with `make schemas` and checked in CI. Change rules: all three people agree, add fields as OPTIONAL
only, update the fixtures in the same commit, add a line here.

## 2026-10-15: Engine draw changed to fixed Gumbel noise per (customer, option) (Person A) - HEADS-UP B and C
- Shapes are unchanged. What changes: for a given seed, WHICH customers pick what. The probabilities are exactly the
  same (softmax of utility / tau), but a what-if now moves only customers whose winning option actually got worse
  (a rival's price rise only moves that rival's customers; your price cut only moves customers TO you).
- Why: the old draw used one uniform number per customer, so changing one option's probability shifted the slice
  boundaries of later options and made unrelated customers "switch" in the Arena animation.
- Effect: `engine.py` and `engine_ref.py` both use it (`backend/engine/sampling.py`), and `fixtures/run_result*.json`
  were regenerated, so a few exact numbers in the fixtures differ (e.g. FreeTool 61% -> 55% on 80 customers).
  Tests that pin one specific customer's outcome should pick a customer from the data instead.
- Hand-written mock fixtures (`agent_explain.json`, `council.json`) still quote the old numbers; they are only used
  as mock fallbacks.

## 2026-10-15: Person A routes: overrides, scenario compare, adjusted run (not shared contracts)
New or now-real routes owned by A, with their own request/response shapes (see `backend/scenarios/`):
- `POST /overrides` `{type: lock|edit|segment_tune|exclude, agent_id|segment_id, option_id|param+value|param+factor}`
  -> `{override, run, moved, audit}`. Trial-run first; refused with 422 if the engine cannot run it.
  `GET /overrides` (audit trail), `DELETE /overrides/{id}` (undo). Saved in `data/overrides.json` (gitignored).
- `GET /runs/{id}/adjusted`: the run with the project's saved overrides applied. The Arena should load this one.
  Excluded customers are absent from it; `GET /runs/{id}/agents/{agent_id}` reflects overrides too.
- `POST /scenarios/compare` `{changes: {option_id: {price, features, novelty}}, label_b, seed, repeats}`
  -> `{a, b, scenarios, deltas, headline, revenue, flip_summary_b, ...}`. Same customers and same seed in both.
- All read inputs through `backend/scenarios/context.py:get_context`, the one function to change when C's run
  storage exists.

## 2026-10-15: Glass-Box optional fields (Person A, flips and narration)
- `Flip.switch_incentive` (trial/migration credit that closes the gap) and `Flip.price_rise` (for agents who
  chose you: price rise before they would leave). `AgentExplain.narration_source` (`llm` or `template`).
  All optional; existing consumers can ignore them.
- `AgentExplain.top_drivers[].delta` is now defined as the component of the chosen option MINUS the same
  component of the runner-up (positive favours the chosen option).

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
