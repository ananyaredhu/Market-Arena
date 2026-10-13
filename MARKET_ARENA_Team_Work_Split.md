# MARKET ARENA: 3-Person Work Split (12 to 18 Oct 2026)

*Companion to `MARKET_ARENA_Master_Plan.md`. This document replaces the 14-day schedule in Section 14 of that plan, which no longer fits the 18 Oct deadline.*

> **Assumptions to confirm now:** (1) the deadline is Sunday 18 Oct, but the cut-off *time* and timezone are unknown, so this plan targets submitting on the night of **Saturday 17 Oct** and keeps Sunday as a buffer; (2) each person can give roughly **30 focused hours** between Tue 13 and Sat 17 **[ASSUMPTION]**; (3) all three can code in Python and TypeScript at a basic level.

---

## 1. The idea that makes "no dependencies" possible

Teams get blocked when one person waits for another's code. We avoid this with three rules:

1. **Contract first.** Tonight, all three people lock the *shapes* of the data that pass between modules (JSON schemas, function signatures, API routes). After tonight, nobody changes a contract without telling the other two.
2. **Mock first.** Tonight we also commit **fixture files** (realistic sample JSON for every contract) and a **reference engine** (the working engine code from Section 4.3 of the master plan). Every module can run against fixtures with no one else's code.
3. **Own your folder.** Each person writes only inside their own folders. Git conflicts cannot happen if nobody edits the same file.

Result: from Tue 13 morning to Thu 15 morning, **each person works with zero waiting**. The only joint moments are listed in Section 6 (the dependency register).

---

## 2. Scope for 6 days (what we build and what we cut)

We cannot build the whole master plan in six days. This is the **competition MVP**:

| Build | Cut or fake |
|---|---|
| Intake (text to structured product profile) | Full custom industry pack generator: use 2 hand-written packs only |
| 2 Industry Packs: **SaaS (study planner)** and **Café** | Hardware, B2B, services packs |
| Population generator (LLM priors, numeric sampling) | Learned or calibrated priors |
| Transparent decision engine + repeated runs with ranges | Adaptive learning |
| Live Arena animation | Multi-user or auth |
| Glass-Box inspector (explain, "what would flip me", overrides) | Billing, accounts: use a single hard-coded demo user |
| Arena Council (Strategist, Devil's Advocate, Moderator) | Multi-step competitor game search: one-step best response only |
| Experiment Kit (text outputs, exportable) | Auto-deploying landing pages |
| Telegram demo bot (opt-in, approve, A/B send, results) | **Stretch: first thing cut if behind** |
| Small backtest (3 cases) | Full 6 to 10 case backtest |
| Precomputed demo runs as a fallback | Heavy infrastructure: no Redis, no Celery |

**Simplified stack for six days:** Next.js (frontend) plus one FastAPI app (backend) with a router file per person, SQLite or JSON files for storage, FastAPI background tasks instead of a queue, and an LLM wrapper with a **mock mode**.

---

## 3. Who owns what (equal split by component type)

Each person gets **one slice of every component type**: backend or logic, AI or prompts, and frontend. That way the workload is balanced, and nobody is stuck doing only UI or only prompts.

| | **Person A: Simulation Core** | **Person B: Council & Kit** | **Person C: Intake, Arena & Telegram** |
|---|---|---|---|
| **Backend / logic** | Decision engine improvements, repeated runs with p10/p50/p90, scenario compare, "what would flip me", overrides | Competitor Strategist (best response), Devil's Advocate (sensitivity and fragility), `/council` and `/kit` endpoints | Project and scenario storage, run orchestration plus streaming, Telegram bot (opt-in, approval, A/B send, tracking) |
| **AI / prompts** | Population and segment-prior generator, validators (diversity, WTP bounds), faithful agent narration | Moderator verdict prompt, Experiment Kit prompts for SaaS and café, expert content for both packs' experiment menus | Intake extraction prompt, competitor profile generation, Telegram promo message variants |
| **Frontend** | Glass-Box drawer, override controls, scenario compare view | Council panel, verdict card, Experiment Kit viewer and export | Intake wizard, **Live Arena animation**, results dashboard (totals and ranges) |
| **Tests / evaluation** | Engine unit tests (budget, monotonicity, reproducibility), backtest harness | Output-schema tests, 1 backtest case (non-tech) | Playwright smoke test, 1 backtest case (tech), precomputed demo runs |
| **Approx. share of effort** | ~33% | ~33% | ~33% |

Balanced effort per person (about 30 focused hours **[ASSUMPTION]**): ~9h backend/logic, ~9h AI/prompts, ~9h frontend, ~3h tests/evaluation.

---

## 4. Tonight: Phase 0 "Contract Lock" (all three, about 2 hours)

This is the **only phase where all three must work together**. Do not skip it.

### 4.1 Tasks (split so each finishes in parallel)

| Task | Who | Output |
|---|---|---|
| Create repo, folder structure, CI lint, `.env.example`, README with run commands | C | Monorepo skeleton |
| Write all JSON schemas in `contracts/` and the sample fixtures in `fixtures/` (see 4.2) | A and B write half each; C reviews | Schemas plus fixtures |
| Commit `engine_ref.py` (reference engine from the master plan, section 4.3) with the frozen function signature | A | Working baseline engine |
| Write `llm.py`: one wrapper with `LLM_MODE=mock|live`, caching by prompt hash, JSON-schema retry loop, token logging | B | Shared LLM client (frozen after tonight) |
| Stub FastAPI app with all routes returning fixtures when `MOCK=1`; stub Next.js pages | C | Everyone can call every endpoint tonight |
| Agree branch and merge rules (Section 7) | All | One-page agreement |

### 4.2 Contracts to freeze (the shapes everyone codes against)

The attribute list below is fixed **per pack** so feature vectors line up. Example for the SaaS pack: `["ai_planning", "simplicity", "privacy", "integrations"]`.

**Option** (your product, a competitor, or the outside option):
```json
{ "id": "you", "label": "StudyFlow", "role": "you|competitor|outside",
  "price": 9.0, "features": [0.8, 0.5, 0.6, 0.3], "novelty": 0.6 }
```

**Population** (output of A's generator; input to the engine):
```json
{ "population_id": "pop_1", "seed": 42, "pack": "saas",
  "attributes": ["ai_planning","simplicity","privacy","integrations"],
  "segments": [{ "id": "budget", "name": "Budget-conscious", "share": 0.3, "evidence": "llm_assumption" }],
  "agents": [{ "id": "a17", "segment": "budget", "budget": 8.0, "alpha": 1.1,
               "w": [0.3, 0.8, 0.2, 0.1], "brand": {"you":0.0,"free_tool":0.4},
               "switch": 0.3, "risk": 0.2, "incumbent": "free_tool",
               "outside_utility": 0.1, "tau": 0.8 }] }
```

**Engine function (frozen signature):**
```python
run_scenario(agents: list[dict], options: list[dict], seed: int, repeats: int = 1) -> RunResult
```

**RunResult** (output of the engine; input to the Arena, Glass-Box and Council):
```json
{ "run_id": "run_8f21", "seed": 42,
  "option_ids": ["you","free_tool","chain_app","outside"],
  "totals": { "you": {"count": 190, "share": 0.19, "p10": 0.14, "p50": 0.19, "p90": 0.24} },
  "choices": [{ "agent_id": "a17", "segment": "budget", "choice": "free_tool", "prev_choice": "you",
                "runner_up": "you", "gap": 0.7,
                "components": { "brand": 0.4, "feature": 0.9, "price": -1.8, "switch": -0.3, "risk": -0.1 } }] }
```

**AgentExplain** (A produces; Arena click opens it):
```json
{ "agent_id": "a17", "segment": "budget", "choice": "free_tool", "runner_up": "you",
  "top_drivers": [{"term":"price","delta":-1.8},{"term":"feature","delta":0.9}],
  "narration": "Chose the free tool because the price gap outweighed the AI planning feature.",
  "flip": { "price_drop": 2.3, "feature_boost": {"attr": "ai_planning", "amount": 0.4} } }
```

**CouncilOutput** (B produces from a RunResult):
```json
{ "run_id": "run_8f21", "verdict": "...", "confidence": "low|medium|high", "fragility": 0.42,
  "who_buys": ["..."], "who_rejects": ["..."],
  "risks": [{ "title": "...", "evidence": "...", "metric": "share 0.19 -> 0.06 if WTP -25%" }],
  "competitor_reaction": { "competitor_id": "chain_app", "move": "price_cut_20", "effect_on_share": -0.05 },
  "experiments": [{ "title": "...", "hypothesis": "...", "pass_threshold": "...", "kind": "landing|survey|interview|offline|telegram" }] }
```

**KitOutput** (B produces):
```json
{ "hypotheses": ["..."],
  "assets": { "landing_copy": "...", "survey": ["..."], "interview_script": ["..."],
              "ad_variants": ["..."], "offline": {"flyer": "...", "checklist": ["..."]},
              "telegram_variants": ["variant A text", "variant B text"] } }
```

**Frontend component props (frozen):**
```ts
<Arena runResult={RunResult} onAgentClick={(agentId: string) => void} />          // C builds
<GlassBoxDrawer agentId={string} runId={string} onOverride={() => void} />        // A builds
<CouncilPanel council={CouncilOutput} kit={KitOutput} />                          // B builds
```
Each component fetches or receives only these props, so each can be built and tested alone on a standalone page with fixture data.

**API routes and owners (frozen):**

| Route | Owner |
|---|---|
| `POST /projects` (intake text to ProductProfile) | C |
| `GET /projects/{id}`, `POST /scenarios`, `POST /scenarios/{id}/run`, `GET /runs/{id}`, `GET /runs/{id}/stream` | C |
| `POST /population/generate` | A |
| `GET /runs/{id}/agents/{agent_id}` (returns AgentExplain), `POST /overrides`, `POST /scenarios/compare` | A |
| `POST /runs/{id}/council`, `POST /runs/{id}/kit` | B |
| `POST /telegram/campaigns`, `POST /telegram/campaigns/{id}/send`, `GET /telegram/campaigns/{id}/results`, webhook | C |

### 4.3 Repository layout (so nobody edits the same files)

```
/contracts/          schemas (frozen after tonight; changes need all 3 approvals)
/fixtures/           sample JSON for every contract (frozen shapes; content can grow)
/backend/
  common/llm.py      (frozen)   shared LLM wrapper
  engine/            A          engine_ref.py then engine.py (same signature)
  population/        A
  sim_routes.py      A
  council/           B
  kit/               B
  council_routes.py  B
  intake/            C
  orchestrator/      C
  telegram/          C
  main.py            C          mounts all routers
/frontend/
  components/arena/        C
  components/glassbox/     A
  components/council/      B
  app/intake/              C
  app/compare/             A
  app/project/[id]/page.tsx  C (composes the three components; built last, ~30 min)
/packs/              saas.yaml (A), cafe.yaml (B)   pack priors and experiment menus
/docs/               deck, video script, IP statement (see Section 8)
```

---

## 5. Individual work packages (build phase, no dependencies)

Each person works only against fixtures and the frozen contracts. Each package ends with a **definition of done** that can be checked without anyone else.

### Person A: Simulation Core

**Days: Tue 13 to Fri 16**

| When | Backend / logic | AI / prompts | Frontend | Tests |
|---|---|---|---|---|
| Tue 13 | Upgrade `engine_ref.py` to `engine.py`: hard budget constraint, outside option, components stored, seeded choices | Population generator prompt: returns segment priors as JSON, with `evidence` tags and at least one hostile segment | Scaffold GlassBoxDrawer reading `fixtures/agent_explain.json` | Unit tests: budget never violated, identical seed gives identical result |
| Wed 14 | Repeated runs with p10/p50/p90; scenario clone and compare logic; overrides (lock choice, edit parameter) | Validators: diversity threshold, WTP bound, minimum outside-option share; numeric sampling of agents from priors | Drawer shows utility breakdown bars, narration, "what would flip me", override controls | Monotonicity test (higher price never raises share) |
| Thu 15 (am) | **Integration 1** (Section 6). Pm: "what would flip me" closed-form calculations, aggregate flip summary | Narration prompt with faithfulness check against top components; template fallback | Compare view (two scenarios side by side) | Narration faithfulness check on 30 samples |
| Fri 16 | Performance (1,000 agents under 1 second), edge cases | Tune segment priors for SaaS pack (`packs/saas.yaml`) | Polish; empty and error states | Backtest harness (script that runs a case file and prints direction accuracy) |

**Definition of done:** (1) `pytest` passes for the engine; (2) `/population/generate` returns a valid Population; (3) GlassBoxDrawer works standalone on fixtures and live; (4) the harness can run a backtest case file.

### Person B: Council & Kit

**Days: Tue 13 to Fri 16**

| When | Backend / logic | AI / prompts | Frontend | Tests |
|---|---|---|---|---|
| Tue 13 | Competitor Strategist: for each rival, try 4 bounded moves (price −10%, price −20%, add feature, promo), call `run_scenario` (reference engine), pick the one that cuts your share most | Moderator prompt: input = numbers from RunResult plus strategist and advocate outputs; output = CouncilOutput JSON | CouncilPanel scaffold on `fixtures/council.json` | Schema tests for CouncilOutput |
| Wed 14 | Devil's Advocate: perturb priors ±20% (WTP, price sensitivity, brand), record share changes, compute fragility score and top 3 failure modes | Experiment Kit prompts for the **SaaS** pack: hypotheses with pass or fail thresholds, landing copy, survey, interview script | Verdict card, risks list, experiments list | Test that every claim in the verdict cites a metric present in the input |
| Thu 15 (am) | **Integration 1.** Pm: wire `/council` and `/kit` endpoints | Experiment Kit prompts for the **café** pack (flyer text with QR, tasting-event checklist, price-board test) plus 2 Telegram promo variants | Kit viewer with copy buttons and a markdown or text export | Cafe-pack output test |
| Fri 16 | Make strategist and advocate deterministic under a seed | Write `packs/cafe.yaml` (segments, attributes, competitor archetypes, experiment menu) | Polish; loading states | **Backtest case 1 (non-tech)**: gather data and write the case file |

**Definition of done:** (1) `/council` and `/kit` return schema-valid output from any RunResult fixture; (2) CouncilPanel works standalone on fixtures; (3) café and SaaS packs both generate sensible kits.

### Person C: Intake, Arena & Telegram

**Days: Tue 13 to Fri 16**

| When | Backend / logic | AI / prompts | Frontend | Tests |
|---|---|---|---|---|
| Tue 13 | Skeleton API (done tonight), SQLite or JSON storage for projects, scenarios, runs; `/scenarios/{id}/run` calls `run_scenario` (reference engine) in a background task | Intake extraction prompt: free text to ProductProfile JSON plus a list of missing assumptions | Intake wizard (form plus paste box), pack selector | Intake schema tests |
| Wed 14 | SSE stream of run progress and frames; competitor profile generation endpoint | Competitor profile prompt (3 plausible rivals per pack, each with price and feature vector) | **Live Arena v1**: canvas with product bubbles and dots coloured by segment, driven by `fixtures/run_result.json` | Smoke test: Arena renders 1,000 dots at 60 fps |
| Thu 15 (am) | **Integration 1.** Pm: Telegram bot (webhook, `/start` opt-in, `/stop`, consent log) | Telegram promo variants from the Kit (use fixtures until B ships) | Arena animation: dots tween from `prev_choice` to `choice`; side panel with live counts and ranges | |
| Fri 16 | Telegram: approval gate, A/B send, click or button tracking, results endpoint; precompute demo runs to `/fixtures/demo/*.json` | | Results dashboard (totals with ranges), Telegram console screen (approve, send, results), project page composing the three components | Playwright end-to-end smoke test |

**Definition of done:** (1) pasting an idea creates a valid ProductProfile; (2) the Arena animates between two RunResult fixtures; (3) the Telegram bot can opt in a test user and send an A/B message after approval; (4) precomputed demo runs exist for both the SaaS and café examples.

**Cut rule for C:** if behind on Thu night, drop Telegram sending and show the Kit's Telegram variants and the opt-in QR flow only.

---

## 6. Dependency register (every point where one person needs another)

Outside this table, **no one should be waiting for anyone**. Each dependency has a mitigation so a late handover never blocks anyone.

| ID | What is needed | Who needs it | From whom | When | Mitigation if late |
|---|---|---|---|---|---|
| **D0** | Contracts, fixtures, `engine_ref.py`, `llm.py`, API stubs | A, B, C | All three | **Tonight (Mon 12)** | Do not start Tue until done |
| **D1** | Real engine (`engine.py`, same signature as `engine_ref.py`) | B (strategist calls it), C (orchestrator calls it) | A | **Thu 15 am** | Both keep using `engine_ref.py`; swap is a one-line import change |
| **D2** | Real Population from the generator | C (run orchestration), B (to test on varied data) | A | **Thu 15 am** | Both use `fixtures/population_*.json` |
| **D3** | Real RunResult with the `components` field | A (drawer data), B (council), C (Arena) | C's orchestrator calling the engine | **Thu 15 am** | All use `fixtures/run_result.json`; shapes are frozen so no code changes |
| **D4** | Arena `onAgentClick(agentId)` wired to `GlassBoxDrawer` | A (opens drawer), C (emits click) | C and A | **Thu 15 am** (composed in project page by C) | A tests the drawer through a standalone page; C tests Arena with a console log |
| **D5** | Council and Kit endpoints returning real output | C's project page and Telegram | B | **Thu 15 pm** | C uses `fixtures/council.json`, `fixtures/kit.json` and hard-coded Telegram variants |
| **D6** | Competitor profiles (rival options) | A and B use them as options in scenarios | C | **Thu 15 am** | Fixtures contain 3 rivals per pack |
| **D7** | `packs/saas.yaml` (A) and `packs/cafe.yaml` (B) loaded by C's pack selector | C | A and B | **Fri 16 am** | C reads fixture packs |
| **D8** | Backtest case files (one each) | A's harness | B and C | **Fri 16** | A tests the harness with a dummy case |
| **D9** | Full end-to-end run on real components | All | All | **Fri 16 evening** | Fall back to precomputed demo runs |
| **D10** | Final deck, video, IP statement, submission | All | All | **Sat 17** | See Section 8 |

**Rule:** if you are going to miss a handover time, say so in the team chat **at least 2 hours before**, and everyone continues on the fixture. Never wait silently.

---

## 7. Working agreements (to keep it conflict-free)

1. **Branches:** one branch per person (`a/sim`, `b/council`, `c/arena`). Merge to `main` through a pull request. A reviewer is **not** required, but the other two must be notified.
2. **Folders:** only edit your own folders (Section 4.3). If you need a change in someone else's folder or a contract, message them and let them make it.
3. **Contract changes:** need agreement from all three, a note in `contracts/CHANGELOG.md`, and a fixture update in the same commit. Prefer *adding* optional fields over changing existing ones.
4. **Mock mode:** run `MOCK=1` and `LLM_MODE=mock` for day-to-day work. Use `LLM_MODE=live` sparingly (shared key, spending cap set tonight).
5. **Daily sync:** 10 minutes at 9:30 and 10 minutes at 21:00 on a call or chat. Each person says: done, doing, blocked. Blockers resolve with fixtures first.
6. **Merge windows:** merge to `main` at least twice a day (lunchtime and 21:00) so integration problems surface early.
7. **Definition of done:** a feature is done when it runs on fixtures, passes its tests and is merged.

---

## 8. Non-build deliverables (also split equally)

The competition also needs a project description, a deck or business plan, a demo video and an IP commitment. These come from the master plan, so they are mostly assembly work.

| Deliverable | Owner | Notes |
|---|---|---|
| Pitch deck and business plan (from master plan Section 2, trimmed to the 50MB limit) | **A** | Uses backtest numbers once available (Fri 16) |
| Demo video (storyboard in master plan Section 16.1): recording, voiceover, edit | **C** | Uses the precomputed demo runs, so recording never depends on a live server |
| Project description, IP statement, submission form, final checklist | **B** | Collect all three members' names and details; verify the file size and links |
| Backtest write-up (3 cases) | A writes it; B and C provide a case each | Include any failures honestly |

---

## 9. Calendar

| Date | Work | Notes |
|---|---|---|
| **Mon 12 (tonight)** | **Phase 0: Contract Lock (all three)** | Only joint building phase |
| **Tue 13** | Independent build (Day 1) | Everyone on fixtures. Check registration status; email the organiser if not done |
| **Wed 14** | Independent build (Day 2) | Everyone on fixtures. Evening sync: confirm engine signature unchanged |
| **Thu 15 am** | **Integration 1** (D1 to D4, D6): swap fixtures for real components | Max 2 hours together; C composes the project page |
| **Thu 15 pm** | Independent build (Day 3) | D5 handover at the end of the day |
| **Fri 16** | Independent build (Day 4); **Integration 2** (D7 to D9) in the evening | Feature freeze at 21:00 |
| **Sat 17** | Backtest numbers, deck, video recording, IP statement; bug-fix only; **submit by night** | No new features |
| **Sun 18** | Buffer: submit if anything slipped; verify the submission was received | Deadline day |

---

## 10. Cut line (decide at the daily sync, never alone)

Cut in this order if behind schedule:

1. Telegram sending (keep opt-in QR and message variants only)
2. Café pack depth (keep SaaS fully, café as a lighter second example)
3. Scenario compare view (keep a simple before/after)
4. Experiment Kit export (keep on-screen display)
5. Backtest down to 2 cases

**Never cut:** the decision engine, the Live Arena animation, the Glass-Box inspector (explain, flip and override), the Council verdict, and the demo video.

---

## 11. Final checklist (Sat 17)

- [ ] Full flow works on the precomputed demo runs with no internet
- [ ] Full flow works live with `LLM_MODE=live` (backup only)
- [ ] Arena animates on strategy change; clicking a dot opens the Glass-Box
- [ ] Council verdict, Kit and (if built) Telegram A/B demo are visible
- [ ] Backtest table written, including any failures
- [ ] Every outcome is labelled "simulated outcome under stated assumptions"
- [ ] Deck, video, project description, IP statement uploaded; links tested in an incognito window
- [ ] Submission confirmation received and screenshotted
