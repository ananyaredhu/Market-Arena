# Market Arena

Test a startup idea against a simulated market: see why every customer chooses or rejects you,
change the strategy, then run the real experiments. Competition entry, deadline 18 Oct 2026.

Read first: `MARKET_ARENA_Master_Plan.md` (what and why) and `MARKET_ARENA_Team_Work_Split.md`
(who owns what, contracts, dependencies).

## Quick start

```bash
make setup      # Python venv + deps, then npm install in frontend/
make test       # backend tests (no network, no keys needed)
make api        # FastAPI on :8000 in mock mode, docs at http://localhost:8000/docs
make web        # Next.js on :3000
```

Day-to-day work uses `MOCK=1` and `LLM_MODE=mock` (set by `make api`): every route returns
fixtures and no LLM key is needed. Copy `.env.example` to `.env` for live mode.

## Layout and ownership

| Path | Owner | What |
|---|---|---|
| `contracts/` | all (changes need all 3) | JSON schemas generated from `backend/common/contracts.py` |
| `fixtures/` | all | sample JSON for every contract (`make fixtures` regenerates engine-driven ones) |
| `backend/common/` | B (`llm.py`), shared | contracts, fixture loader, mock switch, LLM wrapper |
| `backend/engine/`, `backend/population/`, `backend/sim_routes.py` | A | decision engine, population, Glass-Box routes |
| `backend/council/`, `backend/kit/`, `backend/council_routes.py` | B | Council and Experiment Kit |
| `backend/intake/`, `backend/orchestrator/`, `backend/telegram/`, `backend/main.py` | C | intake, runs, Telegram |
| `frontend/components/glassbox/`, `components/compare/`, `app/compare/` | A | Glass-Box drawer, compare view |
| `frontend/components/council/`, `components/kit/` | B | Council screen, Experiment Kit |
| `frontend/components/arena/`, `components/intake/`, `components/telegram/`, `app/intake/`, `app/project/` | C | Arena, intake, Telegram console, project page |
| `frontend/components/ui/`, `components/layout/`, `lib/theme.ts`, `app/globals.css` | shared | design system (tokens, primitives, header) |

The 5 screens follow the design boards; see `frontend/DESIGN.md` for the screen map and how to reuse the design system.
| `packs/saas.yaml` / `packs/cafe.yaml` | A / B | industry pack priors |

## Rules

1. Branch per person (`a/sim`, `b/council`, `c/arena`), merge to `main` by PR at least twice a day.
2. Edit only your own folders. Need a change elsewhere or in a contract? Message the owner.
3. Contract changes: all three agree, add fields as optional, update fixtures and
   `contracts/CHANGELOG.md` in the same commit, run `make schemas`.
4. Every route keeps its path and response shape; replace the stub body, not the contract.
5. Run `make test` and `make lint` before pushing.
