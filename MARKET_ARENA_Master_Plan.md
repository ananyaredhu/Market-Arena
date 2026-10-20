# MARKET ARENA: Master Business and Implementation Plan

*2026 NTU AI Alliance Entrepreneurship Competition (Singapore Track of the Global AI Creation Competition)*
*Primary track: Track 01, Smart Office & Task Execution. Alternative: Track 04, AI New Species.*
*Plan date: 12 Oct 2026. Registration reportedly closes in late October; confirm the exact date with the organisers.*

> **How to read this document.** Anything marked **[ASSUMPTION]** is a working number we must measure or validate. Anything marked **[VERIFY]** is a fact we have not confirmed from a primary source. "Fool-proof" here means *every major risk has a named mitigation and a fallback*. It does not mean guaranteed success.

---

## Table of contents

1. Product definition (final feature set)
2. Business plan
3. System architecture
4. The decision engine (the core IP)
5. The Glass-Box layer (transparent, interruptible agents)
6. The Arena Council (four grounded agent roles)
7. Industry Packs (tech and non-tech startups)
8. The live Arena visualisation
9. Experiment Kit generator (closing the loop)
10. Telegram integration
11. Data model and API
12. Technology stack
13. Evaluation and backtesting plan
14. 14-day build plan (competition MVP)
15. Post-competition roadmap
16. Demo script and submission checklist
17. Risk register
18. Ethics, legal and compliance
19. Open decisions for the team

---

## 1. Product definition

**One-line pitch:** *Test your startup against a simulated market, see exactly why every customer chooses or rejects you, change the strategy, and run the real experiments, all in one place.*

### 1.1 Final feature set

| # | Feature | What it does | MVP? |
|---|---|---|---|
| F1 | Idea Intake | Turns free text or a form into a structured product profile and flags missing assumptions | Yes |
| F2 | Industry Pack selection | Picks segment templates, attributes and experiment menus for the business type | Yes (3 packs) |
| F3 | Customer population generator | Builds 300 to 1,000 heterogeneous agents with explicit parameters | Yes |
| F4 | Decision engine | Transparent utility model that makes every choice, seeded and reproducible | Yes |
| F5 | Live Arena | Animated view where agent dots move between product bubbles as strategy changes | Yes |
| F6 | Glass-Box inspector | Click any agent: see why it chose or switched, what would flip it, and override it | Yes |
| F7 | Arena Council | Customer Council, Competitor Strategist, Devil's Advocate, Moderator | Yes (simplified) |
| F8 | Scenario lab | Change price, features, positioning, competitor moves; side-by-side compare | Yes |
| F9 | Experiment Kit | Generates landing page copy, survey, interview script, ad variants, tracking sheet | Yes (partial) |
| F10 | Telegram promotion | Sends approved promo messages to the founder's own opted-in audience and tracks response | Stretch, demo with one bot |
| F11 | Reality-gap calibration | Upload real survey or experiment data; agents are re-fit and the gap is shown | Stretch |
| F12 | Backtest report | Published accuracy results on known outcomes | Yes (small) |

### 1.2 Design principles

1. **Math decides, language explains.** The LLM never makes a purchase decision. A transparent model does. The LLM builds the population and verbalises the model's own numbers.
2. **Every outcome is traceable** to agent parameters, the rule that fired and the scenario configuration.
3. **The user stays in control.** Any agent decision can be inspected, challenged and overridden.
4. **Honest by design.** Every output is labelled as a simulated outcome with a confidence range. The product's job is to decide *what to test next*, not to predict revenue.
5. **Any business, same engine.** Industry Packs change the inputs, not the engine.

---

## 2. Business plan

### 2.1 Problem

Founders must decide on price, features and target customer before they have customers. Real validation (interviews, surveys, landing pages, pop-ups) is slow, costs money and needs a clear hypothesis. Most first-time founders, especially students and small-business owners, skip it or run it badly. General AI chat gives a single, agreeable, hard-to-reproduce answer and cannot show how a market *reacts* when a variable changes.

### 2.2 Solution

Market Arena builds a simulated, competitive market around the founder's idea, lets them change strategy and watch the market respond, explains every decision, and then produces the real-world experiment materials to verify the findings. It works for software, cafés, clinics, retail, services and hardware.

### 2.3 Target customers (in priority order)

| Segment | Why they buy | Willingness to pay | Channel |
|---|---|---|---|
| **Student founders and university entrepreneurship programmes** | Fast, cheap validation for projects and competitions | Low individually, higher via institution | NTU, NUS, SMU and polytechnic enterprise centres; hackathons |
| **First-time small-business founders** (cafés, retail, services, home businesses) | No research budget, high personal financial risk | Medium | Telegram and Instagram communities, SME workshops, incubators |
| **Early-stage tech startups** | Pricing and positioning decisions | Medium | Accelerators, founder communities, Product Hunt |
| **Incubators and accelerators** | Screen and coach many ideas consistently | High (team plans) | Direct sales, pilot programmes |
| **Product and innovation teams** (later) | Compare feature and pricing options before a build | High | Enterprise pilots after product-market fit |

### 2.4 Competitive landscape and positioning

Synthetic-research companies already exist. Examples reported in the press: Simile (AI "twins" of real people, reported $200M raise at a $2B valuation), Aaru (simulated user behaviour for research) and Synthetic Users. **[VERIFY all figures before using them in the deck.]** Sources: [The Next Web](https://thenextweb.com/news/simile-200-million-agentic-twins-ai-market-research), [Renascence](https://www.renascence.io/news/30097/simile-raises-200m-at-2b-valuation-for-synthetic-user-ai-testing), [F4 Fund](https://app.f4.fund/startups/aaru), [AIMultiple](https://research.aimultiple.com/synthetic-users).

| Dimension | Typical synthetic-research tools | General AI chat | Market Arena |
|---|---|---|---|
| Core question | "What would these people say?" | "What do you think of my idea?" | "What would this market *do* when I change my strategy?" |
| Primary buyer | Enterprise research teams | Anyone | Founders with no research budget |
| Competitors in the same simulation | Usually no | Narrative only | Yes, with scripted and best-response reactions |
| Decision transparency | Often opaque | None | Utility breakdown per agent, user can override |
| Non-tech businesses | Mostly consumer brands and digital products | Generic | Industry Packs (café, clinic, retail, etc.) |
| Path to real evidence | Report | None | Experiment Kit plus Telegram tests plus calibration |
| Reproducibility | Varies | Low | Seeded runs, saved configurations |

**Positioning statement:** *Market Arena is the validation workbench for founders who cannot afford a research agency: a transparent simulation you can interrogate, followed by the tools to test it for real.*

### 2.5 Moat (honest version)

Early on, the moat is not the algorithm. It builds over time through:
1. **Calibration data:** every real experiment result users upload (with consent) improves the priors for each Industry Pack.
2. **Industry Packs:** curated segment priors and experiment playbooks per business type.
3. **Backtested credibility:** a published accuracy record that incumbents' black boxes cannot easily match.
4. **Workflow lock-in:** saved projects, scenario history and linked real experiments.

### 2.6 Business model and pricing **[ASSUMPTION: test through pilots]**

| Plan | Price (SGD/month) | Includes |
|---|---|---|
| Free | 0 | 3 simulations/month, 1 industry pack, 200 agents, watermark on exports |
| Founder | ~19 | 30 simulations/month, all packs, 1,000 agents, scenario compare, Experiment Kit, Telegram (1 bot) |
| Team | ~79 | 5 seats, shared workspace, calibration with uploaded data |
| Incubator | ~299 and up, or per-cohort | Multi-project dashboard, cohort analytics, branded reports |
| Enterprise | Custom | Custom packs, SSO, integrations |

Optional later revenue: paid survey-panel integration (referral or resale), and a per-message fee for high-volume Telegram campaigns.

### 2.7 Unit economics (to be measured in week 1)

A key cost advantage comes from the architecture: **LLM calls scale with the number of segments, not agents.** Agents are sampled parameter vectors scored by math. LLM calls are used for:
- Intake extraction: ~1 call
- Segment priors: ~1 per segment (6 to 10 calls)
- Competitor profiles: ~1 to 3 calls
- Narration of *sampled* agents on demand: ~10 to 30 short calls
- Council summary and Experiment Kit: ~3 to 6 calls

**[ASSUMPTION]** roughly 25 to 60 LLM calls per full scenario, giving a cost of about **$0.05 to $0.50 per scenario** depending on the model. Week 1 task: log real token counts and replace this with measured numbers. If the Free tier costs more than ~$1 per user per month, reduce narration depth or cache results.

Gross margin target: above 75% on paid plans.

### 2.8 Go-to-market

**Phase 0 (competition, Oct to Dec 2026):** Win visibility. Use the finals, the Shenzhen incubation benefits and investor matching described by the organisers **[VERIFY benefits on the official page]**.

**Phase 1 (Jan to Mar 2027): Campus beachhead.** Offer free access to NTU entrepreneurship clubs and one or two incubator programmes. Goal: 10 pilot projects, 3 real experiments run end to end, 1 written testimonial.

**Phase 2 (Apr to Sep 2027): Small-business wedge.** Partner with SME workshops and café or retail communities in Singapore. The Telegram QR-code feature (Section 10) is the hook: a café owner can test a promo and see real responses the same week.

**Phase 3: Incubators and regional expansion.** Sell cohort plans. Localise packs for Malaysia, Indonesia and Greater China.

### 2.9 Illustrative 12-month targets **[ASSUMPTION, not a forecast]**

| Metric | Target |
|---|---|
| Registered users | 2,000 |
| Paid conversion | 4 to 6% (80 to 120 paid) |
| Incubator or university accounts | 3 to 5 |
| ARR at month 12 | ~SGD 30k to 50k |
| Real experiments run via Kit or Telegram | 300+ |
| Backtest directional accuracy (see Section 13) | Report honestly; aim to beat baselines |

### 2.10 Use of funds (if prize money or investment is secured)

Roughly 40% engineering and infrastructure, 25% calibration data (survey panel credits, pilot incentives), 20% go-to-market, 15% legal, compliance and operations. Adjust to the actual amount.

### 2.11 Team and roles (fill in)

| Role | Owner | Responsibilities |
|---|---|---|
| Product and pitch lead | | Narrative, deck, video, business plan |
| ML or simulation lead | | Decision engine, population generator, backtests |
| Backend lead | | API, queue, database, Telegram |
| Frontend lead | | Arena visualisation, Glass-Box UI, dashboard |
| Research and QA | | Industry Packs, backtest data, user tests |

---

## 3. System architecture

```
┌──────────────────────────── Web App (Next.js) ────────────────────────────┐
│ Intake wizard │ Live Arena (canvas) │ Glass-Box drawer │ Scenario compare │
│ Council panel │ Experiment Kit │ Telegram console │ Reports               │
└───────────────▲──────────────────────────────────────────▲────────────────┘
                │ REST + SSE/WebSocket (progress, frames)  │
┌───────────────┴──────────────────────────────────────────┴────────────────┐
│                         API Gateway (FastAPI)                             │
│ Auth │ Projects │ Scenarios │ Runs │ Overrides │ Kit │ Telegram webhooks   │
└──────┬───────────────┬──────────────────┬──────────────────┬──────────────┘
       │               │                  │                  │
┌──────▼─────┐  ┌──────▼───────┐  ┌───────▼───────┐  ┌───────▼────────┐
│ Intake &   │  │ Simulation   │  │ Council       │  │ Telegram       │
│ Population │  │ Engine       │  │ Orchestrator  │  │ Service        │
│ (LLM)      │  │ (NumPy)      │  │ (LLM + engine)│  │ (Bot API)      │
└──────┬─────┘  └──────┬───────┘  └───────┬───────┘  └───────┬────────┘
       └───────────────┴────────┬─────────┴──────────────────┘
                                │
          ┌─────────────────────▼─────────────────────┐
          │ Postgres (+pgvector) │ Redis (queue/cache)│
          │ Object storage (reports, exports)         │
          └───────────────────────────────────────────┘
```

**Request flow for a scenario run**

1. User submits or edits a product profile; the API validates it against the schema.
2. A job is queued. The worker loads the population (generated once per project and reused, so runs are comparable).
3. The simulation engine computes utilities and choices for every agent and stores per-agent breakdowns.
4. The Council orchestrator derives competitor responses, failure scenarios and the verdict from the engine's numbers.
5. The API streams progress and then the "frames" (agent to product assignments) to the Arena.
6. Narration of individual agents is generated lazily when a user clicks an agent, then cached.

---

## 4. The decision engine (the core IP)

### 4.1 Agent definition

Each agent `i` is a parameter vector sampled from its segment's distributions:

| Parameter | Meaning |
|---|---|
| `budget_i` | Maximum spend per period; hard affordability constraint |
| `alpha_i` | Price sensitivity |
| `w_i,k` | Weight on attribute `k` (feature, quality, convenience, location, etc.) |
| `brand_i,j` | Brand affinity for each option `j` |
| `switch_i` | Cost of leaving the current solution |
| `risk_i` | Aversion to unproven products (penalises new entrants) |
| `incumbent_i` | The option they currently use (including "nothing" and "free alternative") |
| `tau_i` | Randomness of choice |

### 4.2 Utility and choice

For option `j` with price `p_j` and attribute vector `f_j`:

```
U_ij = brand_ij + Σ_k ( w_ik · f_jk ) − alpha_i · p_j − switch_i · 1[j ≠ incumbent_i] − risk_i · novelty_j
P(choose j) = softmax(U_ij / tau_i)   over all options with p_j ≤ budget_i, plus the outside option
```

- The **outside option** ("do nothing", "use a free tool", "go to the café across the road") is always present. Many simulators omit it, which inflates demand.
- Affordability is a **hard constraint**, not a soft preference.
- Choices are drawn with a **seeded RNG** so a saved scenario reproduces exactly.

### 4.3 Reference implementation (core of the engine)

```python
import numpy as np

def run_scenario(agents, options, seed=42):
    """agents: dict of arrays; options: list of dicts with price, features, novelty, id."""
    rng = np.random.default_rng(seed)
    n, m = len(agents["budget"]), len(options)
    price = np.array([o["price"] for o in options])               # (m,)
    feats = np.array([o["features"] for o in options])            # (m, K)
    novelty = np.array([o["novelty"] for o in options])           # (m,)

    # utility components kept separately for explainability
    comp = {
        "brand":   agents["brand"],                               # (n, m)
        "feature": agents["w"] @ feats.T,                         # (n, m)
        "price":  -agents["alpha"][:, None] * price[None, :],
        "switch": -agents["switch"][:, None] * (agents["incumbent"][:, None] != np.arange(m)[None, :]),
        "risk":   -agents["risk"][:, None] * novelty[None, :],
    }
    U = sum(comp.values())                                         # (n, m)

    # add outside option as column m
    U_out = agents["outside_utility"][:, None]                     # (n, 1)
    U_all = np.hstack([U, U_out])

    # hard affordability constraint
    afford = price[None, :] <= agents["budget"][:, None]
    mask = np.hstack([afford, np.ones((n, 1), dtype=bool)])
    U_all = np.where(mask, U_all, -np.inf)

    # softmax choice
    z = U_all / agents["tau"][:, None]
    z -= z.max(axis=1, keepdims=True)
    P = np.exp(z); P /= P.sum(axis=1, keepdims=True)
    choice = np.array([rng.choice(m + 1, p=P[i]) for i in range(n)])
    return choice, P, comp, U_all
```

### 4.4 Uncertainty

- Run each scenario `R` times (default 30) with different seeds *and* parameters resampled from segment priors. Report share ranges (e.g. 10th to 90th percentile) instead of single numbers.
- **Fragility score:** perturb key priors (price sensitivity, willingness to pay, brand strength) by ±20% and measure how much the winner or share changes. Large changes mean "do not trust this result; test it for real".

### 4.5 How the LLM is used (and not used)

| Task | LLM? | Notes |
|---|---|---|
| Extract product profile from text | Yes | Structured output validated against a JSON schema |
| Propose segment definitions and parameter priors | Yes | Every prior tagged `evidence`, `user_supplied` or `llm_assumption` |
| Sample individual agents | No | Numeric sampling from priors |
| Decide purchases | **No** | Utility model above |
| Write reasons for decisions | Yes, constrained | Given the utility breakdown; must cite only the top contributing terms; checked against the numbers |
| Competitor profiles | Yes | Reviewed by the user |
| Council narrative and verdict | Yes, constrained | Inputs are engine outputs, not free imagination |
| Experiment Kit text | Yes | Grounded in the verdict and Industry Pack |

**Guard against LLM optimism:** the segment-prior prompt must require at least one *hostile* segment (non-buyers, free-tool loyalists) and a minimum share for the outside option. A validator rejects populations where average willingness to pay exceeds a plausible bound for the category, or where segment diversity (parameter variance) is below a threshold.

### 4.6 Evidence-first population (v2 amendment)

Before the segment priors are generated, a **bounded research agent** (retrieval-augmented generation over the live web) looks for real information that is useful for *this* type of startup in *this* country. It is not limited to economics. It starts from a topic checklist and picks what is relevant: competitor pricing, market size and demand, sourced behaviour statistics (e.g. "62% of students use free planners"), regulation and licensing, distribution channels and costs, seasonality, rent or supply costs, recent trends and news, and country-level economics (e.g. the World Bank API **[VERIFY free access]**).

How findings are used:

| Finding type | Used for |
|---|---|
| Maps to a model parameter (price points, budget ranges, segment shares, free-alternative share) | Sets the centre and spread of the segment priors, tagged `evidence` |
| Everything else (regulation, channels, qualitative facts) | Stored as cited `research_notes` that feed the Council, the narration context and the Experiment Kit |
| Trends and news | Stored as `trend_notes` (see Section 6). May apply a small, bounded, user-visible, toggleable adjustment (about ±10% on budget or price sensitivity) |

Rules that keep it honest:
1. **Every number carries a source URL and a quote.** Our code (outside the agent) checks that the quote actually appears in the fetched page. If not, the number is dropped and the value stays `llm_assumption`.
2. **No evidence found, a failure or a timeout means the original LLM-prior plan runs unchanged.** The user sees which numbers had evidence and which did not.
3. **Hard caps:** about 8 tool calls and 60 seconds per run. Page text is treated as data, never as instructions (prompt-injection guard).
4. **Geography is dynamic:** data is fetched for the country in the user's idea (default Singapore), cached per country as users request it. Budgets are scaled relative to the baseline the pack's priors were written for. Country-based price-sensitivity scaling is tagged `llm_assumption`.
5. **No cultural stereotypes.** Inferring national "personalities" or personal traits by country is excluded (see Section 18). Sourced behavioural statistics are allowed; assumed ones are not.
6. **Reproducibility:** the evidence used is saved as an `evidence_snapshot` with each population, so re-running a scenario reuses the same evidence and seeded results stay comparable.
7. **Fetching:** plain HTTP plus a text extractor first; a headless browser (Playwright) only for JavaScript-rendered pages; no scraping of search-engine result pages; respect robots.txt and site terms. The search provider is an open decision (Section 19).
8. **Demo safety:** evidence for the SaaS and café demos is precomputed so the demo never depends on live search.

Owner: Person A (Simulation Core).

---

## 5. The Glass-Box layer (transparent, interruptible agents)

> *Note on naming.* You described this as "suitcase theory". I could not identify a standard method by that name, so I have implemented the idea you described: **the user always knows why an agent switched and can intervene.** If your team has a specific framework in mind, tell me and I will align the naming and structure.

**Pitch line:** *Other tools give you a verdict. Market Arena shows you the reasoning, and lets you overrule it.*

### 5.1 What the user sees when they click an agent

1. **Profile card:** segment, budget, key priorities, current solution.
2. **Decision breakdown:** a bar chart of the utility components (brand, features, price, switching cost, risk) for the chosen option versus the runner-up.
3. **Plain-language reason:** "Chose the free planner because the price gap outweighed the AI-revision feature; switching cost was low."
4. **Switch history:** across scenarios, "Moved from Your Product to Free Tool after the 20% price rise."
5. **What would flip me:** the smallest change that alters this agent's choice.
6. **Controls:** edit parameters, lock the decision, or exclude the agent.

### 5.2 The "What would flip me" computation

For agent `i`, chosen option `a`, runner-up `b`, the utility gap is `gap = U_ia − U_ib`. Closed forms:

- **Price flip for b:** if `b` is your product, the price must fall by `gap / alpha_i`.
- **Feature flip for b:** feature `k` must rise by `gap / w_ik`.
- **Switching-cost flip:** a trial or migration incentive worth `gap`.

Aggregated across agents, this yields founder-level insights such as "A SGD 2 price cut flips 18% of the Budget segment; adding the revision feature flips 6%."

### 5.3 Human override modes

| Override | Effect |
|---|---|
| **Lock choice** | Pin one agent (or a whole segment) to a chosen option; engine respects it on reruns |
| **Edit parameter** | Change this agent's budget, weights, etc.; rerun instantly (engine is fast, no LLM call) |
| **Segment tuning** | Move sliders for a whole segment ("students are more price sensitive than I assumed") |
| **Evidence tag** | Mark a parameter as backed by real data; shown with a different badge |

All overrides are logged in the scenario's configuration, so the result stays reproducible and the **audit trail** shows what was machine-generated and what was human-adjusted.

### 5.4 Reason-faithfulness check

The narration prompt receives the exact component values and must name only the top two or three positive and negative contributors. A post-check compares the cited drivers with the real top contributors; if they mismatch, regenerate or fall back to a template sentence. This prevents the model from inventing plausible but false explanations. Mention this in the pitch as a differentiator.

---

## 6. The Arena Council (four grounded agent roles)

Each role has a defined input, a defined output, and is grounded in engine numbers. This is multi-agent *design*, not multi-agent theatre.

| Role | Job | Grounding |
|---|---|---|
| **Customer Council** | The segmented customer agents; speaks for each segment ("Budget students: we dislike the S$12 price") | Segment-level aggregates from the engine plus sampled agent reasons |
| **Competitor Strategist** | Chooses how each rival reacts to your move | Tries a bounded menu of moves (price cut of 10 or 20%, add feature, run promo, do nothing), runs the engine for each, and picks the move that maximises the rival's share (one-step best response). The LLM only writes the rationale. |
| **Devil's Advocate** | Finds the most credible ways the idea fails | Runs sensitivity analysis and a worst-case search over priors; reports the top 3 failure modes with numbers (e.g. "If willingness to pay is 25% lower than assumed, your share falls from 21% to 6%") |
| **Moderator** | Produces the verdict, the confidence statement and the experiment list | Combines the three outputs; every claim links to a run ID |

**Council output format (always the same):**
1. Verdict in one sentence, with a confidence label (Low, Medium, High) derived from the fragility score
2. Who buys, who does not, and why
3. Top 3 risks (from the Devil's Advocate)
4. Likely competitor reaction (from the Strategist)
5. The 3 experiments to run first, ranked by "information gained per rupee/dollar"

**Trend context (v2 amendment).** The evidence step (Section 4.6) also outputs `trend_notes` and `research_notes`, each with a source URL and a verified quote (e.g. "rising cost of living", "a rival launched a free tier"). The **Moderator and Devil's Advocate receive them as context** when writing risks and the verdict. Rules:
- A claim that cites a trend must cite its source; the Moderator test "every claim cites a metric or a source" covers this.
- Trend notes never change engine numbers, except Person A's bounded, user-visible, toggleable prior adjustment (about ±10%).
- No trends found means the Council runs exactly as before.

---

## 7. Industry Packs (tech and non-tech startups)

An Industry Pack is a configuration file containing segment templates, attribute schemas, decision-rule tweaks, competitor archetypes, cost assumptions and an experiment menu. The engine is identical across packs.

### 7.1 Pack contents

```yaml
pack: cafe_retail_fnb
attributes: [taste_quality, price, distance_minutes, wait_time, ambience, dietary_fit, loyalty_perks]
extra_constraints: [opening_hours, seating_capacity]
segments:
  - name: Office lunch crowd
    priors: {budget: [6, 14], alpha: [0.4, 0.8], w_distance: [0.5, 0.9], w_wait: [0.5, 0.9]}
  - name: Students on a budget
    priors: {budget: [3, 8], alpha: [0.8, 1.4], w_ambience: [0.3, 0.7]}
  - name: Remote workers
    priors: {budget: [5, 12], w_ambience: [0.6, 1.0], w_wifi_seating: [0.6, 1.0]}
competitor_archetypes: [chain_cafe, hawker_centre, convenience_store, home_brew]
outside_option: "make coffee at home / skip"
experiment_menu: [pop_up_stall, tasting_preorder_form, flyer_qr_test, telegram_promo, price_board_test]
```

### 7.2 Packs for the MVP and beyond

| Pack | Key differences | Example experiments |
|---|---|---|
| **Software / SaaS / apps** (MVP) | Switching cost, integrations, free-tier alternatives, trial behaviour | Landing page with two prices, waitlist, 5 user interviews |
| **Food and beverage / local retail** (MVP) | Distance, wait time, footfall, repeat visits, location | Pop-up stall, QR-code taste test, Telegram promo |
| **Local services** (clinic, tutoring, salon) (MVP-lite) | Trust, referral, appointment friction | Waitlist form, referral-partner pitch, trial session |
| E-commerce / consumer goods | Shipping, reviews, marketplace competition | Pre-order page, small-batch sale |
| Hardware | Unit cost, upfront price, long lead times | Pre-order or crowdfunding page, prototype demo survey |
| B2B / SaaS enterprise | Buying committee, procurement, ROI | Discovery interviews, pilot proposal |

### 7.3 Generic fallback

If a user's business does not match a pack, the intake wizard asks five questions (who pays, what they use today, how often they buy, what the main cost drivers are, how customers find you) and builds a **custom pack** on the fly, flagged as "lower reliability: less tested".

### 7.4 Pack quality control

Each pack ships with: source notes for priors, one backtest case where possible, and a known-limitations paragraph shown to the user.

---

## 8. The live Arena visualisation

### 8.1 Visual design

- Each **product** is a large circle (bubble); your product is highlighted, plus competitors and an "Outside option / Do nothing" bubble.
- Each **agent** is a small dot coloured by segment, sitting inside the bubble it chose.
- Dot size can optionally scale with purchase value.
- When the founder changes a variable, dots **animate** from old to new bubbles; dots that stay put stay put.
- A side panel shows live counts per product and per segment, and a ribbon summarising "why" dots moved (e.g. "62% of switchers cited price").
- Clicking a dot opens the Glass-Box drawer (Section 5).

### 8.2 Data contract

```json
{
  "run_id": "run_8f21",
  "options": [{"id":"you","label":"StudyFlow","x":420,"y":260}, ...],
  "agents": [
    {"id":"a17","segment":"budget","choice":"free_tool","prev_choice":"you",
     "top_reasons":[{"term":"price","delta":-1.8},{"term":"feature","delta":0.9}],
     "flip":{"price_drop":2.3}}
  ],
  "totals": {"you":{"p10":0.14,"p50":0.19,"p90":0.24}, "...":{}}
}
```

*v2 amendment:* the Population, segment and Council contracts gain **optional, backward-compatible** fields: `geography` (country code, default `SG`), `evidence_snapshot_id`, per-segment `sources: [{url, quote, retrieved_at}]`, `research_notes`, `trend_notes: [{note, source_url, quote, effect}]` and `trend_context` on the Council output. Existing consumers can ignore them.

### 8.3 Implementation

- **Library:** PixiJS or plain Canvas for 1,000 dots at 60 fps; D3 for layout (`d3-force` with each product acting as an attractor).
- **Animation:** on a new run, compute the diff between `prev_choice` and `choice`; tween each switching dot's target position over ~1.5 seconds with a staggered delay so the movement reads clearly.
- **Interaction:** hover shows segment and choice; click opens the drawer; lasso selection filters a segment.
- **Fallback for demo and slow networks:** precomputed run files (`/demo/*.json`) so the video never waits for the model.
- **Accessibility:** also expose the data as a sortable table, and avoid colour-only encoding (use shapes or outlines for key segments).

---

## 9. Experiment Kit generator (closing the loop)

Goal: after the verdict, the system produces everything the founder needs to run the first real tests. The Kit adapts to the Industry Pack.

| Artifact | Generated content | Used for |
|---|---|---|
| **Hypothesis sheet** | 3 to 5 testable statements with a pass/fail threshold, e.g. "At least 8% of 100 visitors join the waitlist at S$9/month" | Keeps tests honest |
| **Landing page** | Copy for headline, benefits, price variants A/B, email or Telegram capture form; exportable as static HTML | Online demand tests |
| **Survey** | 8 to 12 questions targeting the riskiest assumption (price ladder, feature trade-offs) | Willingness to pay |
| **Interview script** | Screening questions, open-ended prompts, "mom test" style questions, notes template | Qualitative evidence |
| **Ad variants** | Short ad copy and audience suggestions | Small paid tests |
| **Offline kit (non-tech)** | Flyer text with QR code, tasting-event checklist, price-board test plan, pop-up stall plan | Cafés, retail, services |
| **Tracking sheet** | CSV or sheet with the metrics to record and the decision rule | Reading results |

**Why this wins on Track 01:** the agent completes a real task chain (analyse, decide, draft, deploy), not just analysis.

**Feedback loop (stretch):** the user enters real results (conversion, survey counts) into the tracking sheet; the system compares them with the simulated share and shows a **Reality Gap** (e.g. "Simulated 18% vs real 9%: your price sensitivity prior was too low"). It then offers to re-fit the segment priors.

---

## 10. Telegram integration

### 10.1 What it does

The founder connects a Telegram bot and can send **promotional messages** generated from the winning positioning to their own audience, then see how people respond. For example, a café owner prints a QR code on the counter; customers scan it to subscribe; the owner sends a lunch-deal message and sees clicks and replies in the dashboard.

### 10.2 Important platform and legal constraints

- A Telegram bot **cannot start a conversation** with someone who has not interacted with it. Cold messaging by phone number or username is not possible and not allowed. The design below uses **opt-in subscribers** and **owned channels or groups** only.
- Mass broadcasts are rate-limited by Telegram (documented bulk limit of roughly 30 messages per second **[VERIFY in the Bot API FAQ]**). Our volumes are small, but queue sends anyway.
- Obtain explicit consent, provide a `/stop` command, and keep a consent log. Review Singapore's PDPA and Telegram's terms with a qualified adviser before launch. **[VERIFY legal position]**

### 10.3 User flow

1. Founder opens the Telegram console and either connects their own bot (via BotFather token) or uses the shared "Market Arena" bot with a campaign deep link.
2. System generates a **subscribe link and QR code** (`t.me/<bot>?start=<campaign_id>`) for printing or sharing on social media.
3. Customers tap the link and press Start, giving consent (the bot shows a short consent message and a `/stop` option).
4. Founder asks Market Arena to draft 2 or 3 **message variants** from the winning positioning (including one that tests a different price or offer).
5. Founder **approves** variants (mandatory human approval; nothing is sent automatically).
6. The system splits subscribers randomly between variants (A/B) and sends via the queue with frequency caps (e.g. max 2 per week per subscriber).
7. Responses are tracked: link clicks (short links), button taps (inline keyboards), replies, and unsubscribes.
8. Results feed the Reality Gap view and a "Promo Lab" report.

### 10.4 Technical design

```python
# FastAPI webhook receiving Telegram updates
@app.post("/telegram/webhook/{secret}")
async def tg_webhook(secret: str, update: dict):
    verify_secret(secret)
    msg = update.get("message", {})
    text = msg.get("text", "")
    chat_id = msg["chat"]["id"]
    if text.startswith("/start"):
        campaign_id = text.split(" ", 1)[1] if " " in text else None
        await record_consent(chat_id, campaign_id)
        await send(chat_id, "Thanks for subscribing. Reply /stop any time to unsubscribe.")
    elif text == "/stop":
        await revoke_consent(chat_id)
        await send(chat_id, "You have been unsubscribed.")
```

- **Library:** `python-telegram-bot` or `aiogram` (Python), or `grammY` (Node).
- **Tables:** `tg_campaigns`, `tg_subscribers (chat_id, campaign_id, consent_at, revoked_at)`, `tg_messages (variant, sent_at, subscriber_id)`, `tg_events (clicks, taps, replies)`.
- **Safety rails:** approval gate, frequency cap, content check (no deceptive or prohibited content), opt-out honoured within seconds, per-campaign send log.
- **Inline keyboard** buttons: "Interested", "Too expensive", "Not for me", turning each message into a mini-survey with structured responses.

### 10.5 MVP scope

For the competition: one demo bot, one campaign, a small test audience (team members and friends who opt in), A/B message send, and a results screen. Do not build multi-tenant bot management yet.

---

## 11. Data model and API

### 11.1 Core tables (Postgres)

```
users(id, email, plan, created_at)
projects(id, user_id, name, industry_pack, created_at)
product_profiles(id, project_id, version, json, created_at)
segments(id, project_id, name, priors_json, evidence_tag, share_assumption)
populations(id, project_id, seed, n_agents, geography, evidence_snapshot_id, created_at)
evidence_snapshots(id, project_id, country, sources_json, research_notes_json, trend_notes_json, created_at)   -- v2
agents(id, population_id, segment_id, params_json)
options(id, scenario_id, role, name, price, features_json, novelty)   -- you / competitor / outside
scenarios(id, project_id, parent_scenario_id, config_json, created_at, label)
runs(id, scenario_id, seed, r_repeats, status, results_json, created_at)
agent_choices(run_id, agent_id, option_id, utility_json, prob_json)
overrides(id, project_id, agent_id_or_segment_id, type, value_json, created_by, created_at)
council_outputs(run_id, role, text, evidence_refs_json)
experiment_kits(id, run_id, hypotheses_json, assets_json)
tg_* tables (Section 10)
```

### 11.2 Main endpoints

| Method and path | Purpose |
|---|---|
| `POST /projects` | Create project and run intake |
| `POST /projects/{id}/population` | Generate or regenerate population |
| `POST /scenarios` | Create scenario (clone with changes) |
| `POST /scenarios/{id}/run` | Queue simulation |
| `GET /runs/{id}/stream` | SSE progress and result frames |
| `GET /runs/{id}/agents/{agent_id}` | Glass-Box breakdown and narration |
| `POST /overrides` | Apply lock or parameter edit |
| `POST /runs/{id}/council` | Generate Council output |
| `POST /runs/{id}/kit` | Generate Experiment Kit |
| `POST /telegram/campaigns` and `/send` | Promo management (with approval) |
| `POST /calibration/upload` | Upload real data (stretch) |

---

## 12. Technology stack

| Layer | Choice | Reason |
|---|---|---|
| Frontend | **Next.js (TypeScript), React, Tailwind** | Fast to build, deploys easily |
| Arena rendering | **PixiJS or Canvas + d3-force** | 1,000 animated dots smoothly |
| Charts | Recharts or D3 | Distribution and sensitivity charts |
| Backend API | **FastAPI (Python)** | Same language as the simulation code |
| Simulation | **NumPy / pandas / SciPy** | Vectorised, fast, easy to test |
| Job queue | **Redis + RQ or Celery** | Runs, narration, kit generation |
| Database | **Postgres** (+ pgvector later for similar-case retrieval) | Relational integrity for runs and overrides |
| LLM | **Free open-weight provider chain behind one OpenAI-style interface (v2 change; the team has no paid API credits):** Groq (`gpt-oss-120b`) → OpenRouter `:free` models → local Ollama (small Qwen, demo fallback) → cached or template answer. Timeouts, retry on 429/5xx, temporary skip of a failing provider, cache by prompt hash, model logged per run. **[VERIFY current free-tier limits, tool-calling support and any router library's fallback support before relying on them.]** Free tiers may train on prompts: fine for fictional demo ideas; state it in the privacy section | Free, swappable, survives one provider failing. Schema validation runs on every provider's answer, so a weaker fallback model cannot pass bad output through |
| Validation | **Pydantic** schemas for every LLM output | Reject malformed data |
| Telegram | `python-telegram-bot` or `aiogram` | Webhook bot |
| Auth | Clerk, Auth0 or Supabase Auth | Avoids writing auth |
| Hosting | Vercel (frontend), Fly.io / Railway / AWS (API, worker, DB, Redis) | Quick deploy |
| Observability | Sentry and structured logs; log token usage per run | Cost control and debugging |
| Testing | pytest, property tests for the engine, Playwright for UI smoke tests | Reproducibility |
| CI | GitHub Actions | Tests on every push |

**Keep it small:** if time is short, use a single FastAPI service with an in-process background task instead of Redis and Celery, and SQLite or a hosted Postgres. Upgrade later.

### 12.1 Prompt and schema discipline

- Every LLM call has a **JSON schema**, a retry-with-error-message loop (max 2 retries), and a deterministic fallback template.
- Cache by hash of (prompt, inputs, model version) for repeatability.
- Store model name and version with each run.
- Temperature low (≤0.3) for extraction; moderate for creative copy.

---

## 13. Evaluation and backtesting plan

This is the most important credibility section. Judges and investors will ask whether the simulation matches reality.

### 13.1 Tests, in order of priority

| Test | Method | Pass criterion |
|---|---|---|
| **Engine correctness** | Unit tests: budget constraint never violated; raising price never raises share (monotonicity); identical seed gives identical result | 100% pass |
| **Reproducibility** | Re-run saved scenarios 20 times | Same output with same seed |
| **Sensitivity sanity** | Change price ±20%, remove top feature, add competitor | Directionally sensible changes; not flat, not wildly jumpy |
| **Diversity check** | Variance of parameters per segment; share of non-buyers | Exceeds thresholds; non-buyers present |
| **Backtest on known outcomes** | 6 to 10 cases with public outcomes (e.g. crowdfunding campaigns that succeeded or failed, public pricing changes and subsequent reaction, product launches with documented results); include at least 2 non-tech cases | Report directional accuracy and rank agreement versus baselines |
| **Baseline comparison** | Compare against (a) a single LLM prompt "will this succeed?" and (b) a coin flip | Beat both, or report honestly where we do not |
| **Glass-Box faithfulness** | Sample 50 narrations and compare cited drivers to the true top contributors | ≥ 95% match |
| **User study** | 5 to 8 student founders or café owners run the demo; measure time-to-first-insight and perceived usefulness | Qualitative quotes and a simple 1 to 5 rating |

### 13.2 Honest reporting rule

Publish the backtest table even if some cases fail. A modest but honest result (for example, "directionally correct in 6 of 9 cases; failed on two, here is why") is more credible than a perfect claim. Never describe simulated share as a forecast of sales.

---

## 14. 14-day build plan (competition MVP)

*Assumes work starts 13 Oct and the registration deadline is in late October; confirm the date and register early.*

### Day 0 (today)
- Confirm the registration deadline and the submission format with the organiser (LILO0002@e.ntu.edu.sg); ask for the judging criteria.
- Decide the track (recommended: Track 01) and assign roles.

### Week 1: Engine and data

| Day | Deliverable |
|---|---|
| 1 | Repo, CI, FastAPI skeleton, Next.js skeleton; JSON schemas for product profile, segment, option |
| 2 | Decision engine (Section 4) with unit tests; seeded runs |
| 3 | Intake extraction and population generator with LLM; validators for diversity and willingness-to-pay bounds |
| 4 | SaaS pack (study planner) and café pack priors; competitor profiles; first end-to-end run in a notebook |
| 5 | Scenario system (clone and change price or feature) and side-by-side compare; repeated runs with ranges |
| 6 | Glass-Box breakdown and "what would flip me" functions; narration with faithfulness check |
| 7 | **Checkpoint:** demo the study-planner scenario in a bare UI; start a backtest data list |

### Week 2: Experience, Council, Kit, polish

| Day | Deliverable |
|---|---|
| 8 | Arena visualisation with animated switching; precomputed demo runs |
| 9 | Glass-Box drawer and override controls in the UI |
| 10 | Council: Competitor Strategist (best response), Devil's Advocate (sensitivity), Moderator output |
| 11 | Experiment Kit generator (SaaS and café variants); Telegram demo bot with opt-in, approval and A/B send |
| 12 | Backtest run on 6+ cases; results table; fix top bugs |
| 13 | Record the demo video; write business plan and pitch deck from this document; IP statement |
| 14 | Buffer: submit early; rehearse the pitch; dry-run the demo offline |

**Cut line (if behind schedule):** drop Telegram first, then Reality-gap calibration, then the third Industry Pack. Never cut: the engine, the Arena animation, the Glass-Box inspector, the backtest and the Council summary.

---

## 15. Post-competition roadmap

| Period | Focus |
|---|---|
| Months 1 to 3 | Run pilots with 10 projects at NTU; collect real experiment results; improve packs; add auth and billing |
| Months 4 to 6 | Reality-gap calibration live; survey-panel integration; Telegram multi-tenant; incubator dashboard |
| Months 7 to 12 | More packs (e-commerce, hardware, B2B); learned priors from aggregated consented data; API; regional localisation |
| Year 2 | Adaptive competitor agents; automated experiment orchestration (landing page deploy, ad platform connectors); enterprise features |

---

## 16. Demo script and submission checklist

### 16.1 Three-minute demo video storyboard

| Time | Scene |
|---|---|
| 0:00 to 0:20 | Hook: "Most startups find out they were wrong after they launched." A founder with an idea (study planner). |
| 0:20 to 0:50 | Paste idea; intake structures it; Industry Pack chosen; population appears as dots. |
| 0:50 to 1:25 | Run the market: dots flow into your product, competitors and "do nothing". Dashboard shows the share ranges. |
| 1:25 to 2:00 | **Glass-Box moment:** click a dot that left; see the reason and "what would flip me"; override it; rerun. |
| 2:00 to 2:25 | Change strategy (add free tier); watch dots migrate; Council speaks: strategist reaction, devil's advocate risks, verdict. |
| 2:25 to 2:45 | Experiment Kit appears; show the café variant and the Telegram QR-code and A/B promo. |
| 2:45 to 3:00 | Backtest result and closing line: "Before the market tests your startup, test your startup against the market." |

Tip: show a *second, non-tech* example (the café) in the video to prove generality; keep the main story on one case.

### 16.2 Submission checklist (based on the organiser's page; confirm each item)

- [ ] Registered on the official page; all team members listed
- [ ] Project description
- [ ] Business plan or pitch deck (use Section 2 content), under the 50MB file limit
- [ ] Demo video link (public or unlisted, tested in an incognito window)
- [ ] IP commitment / originality statement signed by the team
- [ ] Live demo link or fallback recording, in case the server fails
- [ ] Truthful and lawful materials: every claim in the deck matches evidence; competitor data cited with sources
- [ ] Backup copy of all files and a printed or offline slide version

### 16.3 Pitch narrative (for the deck)

1. Problem: founders guess; real tests are slow and costly.
2. Insight: a market is a set of choices under constraints, so we can simulate the choices transparently.
3. Product: Arena, Glass-Box, Council, Kit.
4. Proof: backtest and demo.
5. Market and business model.
6. Why us and why now.
7. Ask: what we need from the competition and the Shenzhen programme.

---

## 17. Risk register

| # | Risk | Likelihood / impact | Mitigation | Fallback |
|---|---|---|---|---|
| 1 | Simulated customers do not match reality | High / High | Transparent model, hostile segments, fragility scores, backtests, calibration, honest labelling | Position as "decide what to test", not "predict sales" |
| 2 | LLM produces optimistic or homogeneous personas | High / Medium | Validators for diversity and WTP bounds; mandatory non-buyer segments; LLM never decides purchases | Template priors from the Industry Pack |
| 3 | Narrations misrepresent the real cause of a decision | Medium / High | Faithfulness check against utility components | Template sentences |
| 4 | Time overrun in a 2-week sprint | High / High | Cut line (Section 14); precomputed demo runs | Slide-based walkthrough with recorded video |
| 5 | Live demo fails (network, API limits) | Medium / High | Precomputed runs, offline mode, recorded backup | Video only |
| 6 | Non-tech packs are weak or untested | Medium / Medium | Label custom packs "lower reliability"; include one backtested non-tech case | Focus the pitch on one strong pack |
| 7 | Incumbents (well-funded) overlap | Medium / Medium | Focus on founders, transparency, closed loop, SME wedge | Partner or specialise by vertical |
| 8 | Telegram misuse (spam) or policy breach | Medium / High | Opt-in only, approval gate, frequency caps, `/stop`, consent logs | Disable the feature; keep the message generator only |
| 9 | LLM cost overrun | Medium / Medium | LLM calls scale with segments; caching; usage logging; plan limits | Smaller model for drafts |
| 10 | Data privacy (user idea confidentiality) | Medium / Medium | Clear privacy policy; no training on user data; delete-on-request | Offer local or private-instance mode for incubators |
| 11 | Competition rules differ from assumptions | Medium / Medium | Email the organiser now; keep materials format-flexible | Adapt quickly |
| 12 | False confidence from a polished UI | High / High | Always show ranges, fragility, assumptions, and "simulated" labels | Remove single-number displays |
| 13 | Free-tier LLM rate limits or provider outage (v2) | High / Medium | Provider chain with fallback, cache by prompt hash, `LLM_MODE=mock` for day-to-day work, precomputed demo runs | Cached or template answers; local Ollama for demos |
| 14 | Web evidence is wrong, stale or contains injected instructions (v2) | Medium / High | Quote-in-source verification, source URL on every number, page text treated as data, hard caps, evidence snapshot saved per population | Drop the number and fall back to `llm_assumption` priors (original plan) |

---

## 18. Ethics, legal and compliance

- **Labelling:** all simulated outputs are labelled "simulated outcome under stated assumptions". No claims of predicting revenue.
- **Stereotype risk:** personas are parameter vectors with documented priors, not demographic caricatures. Allow users to edit segment definitions, and avoid sensitive attributes (race, religion, etc.) as decision drivers.
- **User data:** store ideas privately; do not use customer data to train models without explicit opt-in; support deletion.
- **Telegram and marketing:** explicit opt-in, easy opt-out, human approval, truthful promotional content; check PDPA obligations and Telegram's terms with a qualified adviser **[VERIFY]**.
- **Third-party claims:** cite sources for competitor and market data in the deck; avoid presenting unverified figures as fact.
- **IP:** document that the team wrote the code and models used; list open-source licences and API terms in the IP statement.

---

## 19. Open decisions for the team

1. **Track:** confirm Track 01 versus Track 04 after the organiser replies. With the Arena and Glass-Box features, either is defensible; Track 01 is the safer fit because of the task-execution loop.
2. **Primary demo case:** study planner (tech) plus café (non-tech) is recommended.
3. **Telegram scope:** full demo or a short clip? Decide by Day 10 based on progress.
4. **LLM provider and budget:** *decided (v2):* free open-weight provider chain (Section 12). Still to do: confirm current free-tier limits and get API keys.
8. **Search provider for the evidence agent (v2):** DECIDED: self-hosted SearXNG (free, open-source, no key; `make search-up`). Do not scrape search-engine pages directly.
5. **Backtest cases:** agree on 6 to 10 and who sources the data.
6. **Team roles:** fill in Section 2.11.
7. **Naming:** confirm "Glass-Box" or your preferred term for the transparent-reasoning feature.

---

*Prepared as a working plan. Update the [ASSUMPTION] and [VERIFY] items as evidence arrives, and keep the backtest table honest.*
