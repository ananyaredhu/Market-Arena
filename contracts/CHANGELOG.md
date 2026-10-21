# Contracts changelog

Source of truth: `backend/common/contracts.py` (Pydantic). JSON schemas in this folder are generated
with `make schemas` and checked in CI. Change rules: all three people agree, add fields as OPTIONAL
only, update the fixtures in the same commit, add a line here.

## 2026-10-21: Only real datasets move the priors; page evidence goes to Resources (Person A) - HEADS-UP B and C
- No shared shape changed. Behaviour change: statistics found on web pages (surveys, news, competitor prices) no longer
  change the population. Only dataset-backed evidence does (today: World Bank GDP per person scales budgets).
  `use_trends` on `POST /population/generate` is now ignored. `Population.generation.evidence` gains `reference_items`
  and no longer has `advisory`.
- `EvidenceSnapshot` gains `datasets` (official SingStat figures for Singapore: consumer prices and household spending,
  each with its table id, url and the row as read). Shown in the snapshot, in Resources as topic `official data`
  (`kind: dataset`) and to the Council as reference. They do not change priors. The country-income scale now also applies
  when web research is off or failed, because it needs no search or model.
- Consumer prices move budgets. For Singapore the snapshot keeps the all-items CPI by year (`price_index`) and the
  generator multiplies every budget range by the full reported change from a starting year to the latest year (no cap).
  The starting year is the year the pack's budgets are assumed to be in: new optional `price_base_year` (default 2024)
  on `POST /population/generate`, and on `POST /scenarios` (C's route, 2 lines). A year outside the published series
  changes nothing and says why in `generation.evidence.skipped`.
- New route `GET /resources?pack=&geography=&topic=&q=`: the Resources library of everything the researcher read, each with
  a verified quote, url and retrieved date. Reference only. Stored in `data/resources/`, filled whenever a snapshot is saved.
- `GET /evidence/{id}?view=council` now also carries `reference_only: true`; its trend notes have `effect: null`.
  B: cite these as labelled reference, not as inputs the model used.
- `POST /scenarios` (C) now accepts optional `research` and `evidence_snapshot_id` and passes them to the generator.

## 2026-10-15: Evidence researcher (Person A) - HEADS-UP B (Council) and C (orchestration)
- No shared shape changed. Already-optional fields are now filled: `Population.evidence_snapshot_id`,
  `Segment.sources` (`{url, quote, retrieved_at}`, quotes verified to occur in the fetched page) and
  `Segment.evidence = "evidence"` for segments the research adjusted. `Population.generation.evidence` (free-form) says
  what was applied, skipped, and why research fell back.
- `POST /population/generate` body gains optional `research` (run the web researcher), `evidence_snapshot_id`
  (reuse a saved one) and `use_trends` (default true). Omit all three for the old behaviour.
- New routes: `POST /evidence/research` `{pack, geography, product}` -> `EvidenceSnapshot` (always 200; read `status`:
  ok / partial / empty / failed / off, and `fallback_reason`). `GET /evidence/{id}` returns it;
  `GET /evidence/{id}?view=council` returns exactly the `fixtures/trend_notes.json` shape (`research_notes`,
  `trend_notes`) for B's Council to read as context. Trend notes change the population by at most +-20% (bounded).
- Needs a running SearXNG (`make search-up`, `SEARXNG_URL` in `.env`; free, no key) and `LLM_MODE=live`; otherwise the status is `off` and nothing changes.

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
