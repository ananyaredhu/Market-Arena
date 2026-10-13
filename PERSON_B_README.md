# Person B — Council & Kit

Independent work package for the Market Arena competition MVP.

## What this owns

| Area | Path |
|---|---|
| Competitor Strategist | `backend/council/strategist.py` |
| Devil's Advocate | `backend/council/advocate.py` |
| Moderator / claims | `backend/council/moderator.py`, `claims.py`, `wording.py` |
| Engine adapter (mock + frozen signature) | `backend/council/engine_adapter.py` |
| Schemas / contract proposals | `backend/council/schemas.py`, `backend/council/contracts/` |
| Routes | `backend/council_routes.py` |
| Experiment Kit | `backend/kit/` |
| Café pack | `packs/cafe.yaml` |
| SaaS kit content (priors stay with A) | `backend/kit/content/saas.yaml` |
| Non-tech backtest case | `backend/council/backtest/cafe_case_01.yaml` |
| CouncilPanel | `frontend/components/council/` |

## Setup

```bash
cd /Users/umeshgjh/Projects/Market-Arena
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements-person-b.txt
```

## Regenerate mock fixtures

```bash
cd backend && ../.venv/bin/python -m council.fixtures.make_fixtures
python ../frontend/components/council/build_standalone.py
```

Fixtures are labelled `meta.source = mock_fixture` / `engine_source = mock`. They are **not** Person A's engine output.

## Run tests

```bash
cd backend && ../.venv/bin/pytest
```

## Run Council / Kit on fixtures (no API)

```bash
cd backend && ../.venv/bin/python - <<'PY'
from council.engine_adapter import MockEngineAdapter
from council.service import run_council, run_kit
from council.tests.conftest import load
pop, opts, rr = load("population_saas.json"), load("options_saas.json"), load("run_result_saas.json")
out = run_council(rr, pop, opts, "saas", adapter=MockEngineAdapter())
print(out["council"].verdict)
print(run_kit(out["council"], "saas", opts).hypotheses[0])
PY
```

## Frontend component

- React: `frontend/components/council/CouncilPanel.tsx` + `FixturePage.tsx`
- No Next.js app exists yet. Until Person C scaffolds it, open the standalone HTML:

```bash
open frontend/components/council/council_standalone.html
```

Mount later as:

```tsx
// app/dev/council/page.tsx
export { default } from "@/components/council/FixturePage";
```

## Environment flags

| Variable | Effect |
|---|---|
| `COUNCIL_ENGINE=mock` | Force mock adapter |
| `COUNCIL_ENGINE=auto` | Prefer Person A's `run_scenario` if importable, else mock |
| `MOCK=1` | Routes serve fixtures when body is omitted |

## Do not edit

Person A's engine/population, Person C's intake/orchestration/Arena/Telegram, or shared `/contracts` until the team approves the proposals in `backend/council/contracts/`.
