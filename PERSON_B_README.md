# Person B — Council & Kit

Independent work package, now aligned with the Phase 0 monorepo skeleton on `main`.

## Ownership

| Area | Path |
|---|---|
| Strategist / Advocate / Moderator | `backend/council/` |
| Routes | `backend/council_routes.py` |
| Experiment Kit | `backend/kit/` |
| Café pack | `packs/cafe.yaml` |
| SaaS kit content (priors stay with A) | `backend/kit/content/saas.yaml` |
| Backtest stub | `backend/council/backtest/cafe_case_01.yaml` |
| Council UI | `frontend/components/council/` |

Shared contracts live in `backend/common/contracts.py` / `contracts/`. Person B does **not** fork them.

## Setup

```bash
make setup
make test
make api    # :8000
make web    # :3000 — open /dev/council
```

## How routes behave

`POST /runs/{id}/council` and `POST /runs/{id}/kit` compute via Person B modules using
shared `/fixtures` inputs (and `backend.engine.engine_ref` by default). If compute fails
and `MOCK=1`, they fall back to `fixtures/council.json` / `fixtures/kit.json`.

Force the labelled mock engine adapter with `COUNCIL_ENGINE=mock`.

## Local fixtures

Person B still keeps richer SaaS/café fixtures under `backend/council/fixtures/` for unit
tests and the standalone HTML page:

```bash
cd backend && ../.venv/bin/python -m council.fixtures.make_fixtures
# from repo root after PYTHONPATH=. :
.venv/bin/python -m backend.council.fixtures.make_fixtures
.venv/bin/python frontend/components/council/build_standalone.py
open frontend/components/council/council_standalone.html
```
