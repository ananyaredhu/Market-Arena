# Phase 3C — frontend integration completion

Branch: `c/telegram-real-integration`. The branch and inherited Phase 3B changes were checked before implementation. No Telegram backend files, simulation engine files, Council/Kit generation internals, secrets, environment files or dependency versions were changed. No Telegram requests, live messages, commits, pushes or merges were performed.

## Completed

### Project/run navigation

`frontend/lib/run-context.ts` owns the explicit project/run route context. The shared header uses it for:

- Arena: `/project/{project_id}?run={run_id}`
- Council: `/project/{project_id}/council?run={run_id}`
- Kit: `/project/{project_id}/kit?run={run_id}`

A header discards a context belonging to another project. History and Compare do not inherit an unrelated selection. Only the explicit `proj_1` demo defaults to `run_42`; a real project without a run shows the existing selection-required state.

ProjectRoute keys views by project, and Arena keys its loaded run view by both IDs, preventing old async results/selection from appearing under a different route context. The demo scenario selector writes its selection into the URL, including the alternate `run_42_price3`, so returning from Council or Kit preserves that selection. CouncilView changes are limited to navigation context; CouncilPanel and backend Council/Kit internals are unchanged.

### Mock intake contract

The mock branches in `backend/orchestrator/routes.py` now add the identity fields required by the real response interfaces. They retain the canonical fixture IDs: `proj_1`, `scn_1`, `run_42` and the SaaS fixture data. These are explicitly demo responses, not arbitrary persisted mock projects.

Mock scenario responses include `project_id`, `pack`, and `seed`; mock run-start responses include `project_id` and `scenario_id`. Existing IDs, options and status fields remain available. Real-mode branches are unchanged.

`frontend/lib/intake-flow.ts` is used by the intake page for both modes. It validates nonempty, well-formed IDs, exact project/scenario ownership and completed run status before constructing the Arena URL. There is no permissive client-side mock bypass. Missing or mismatched real responses are rejected rather than converted into demo IDs.

### Telegram presentation

KitView filters only the exact obsolete statement that delivery/approval/click rates are not live. Other backend notes and all hypotheses, assets and experiment recommendations are preserved, without mutating the source Kit.

Mock presentation explicitly says delivery is simulated, no messages are sent, and displayed counts/rates are samples.

The real console performs only a safe `/health` check when mounted and reports these distinct states: checking, backend offline, backend mock mode, backend connected in real mode with unverified bot configuration, explicitly incomplete configuration, and delivery confirmed by a positive send result. Campaign actions remain disabled until a real backend is reachable and an operator token has been entered. A backend connection, mode flag, campaign creation or approval does not prove bot credentials are valid. The unchanged backend has no non-sending bot-configuration readiness endpoint, so the UI deliberately does not invent that guarantee.

## Files changed during Phase 3C

Existing files updated:

- `backend/orchestrator/routes.py` — mock response fields only.
- `backend/orchestrator/tests/test_routes.py` — updated fixture expectation and shared mock/real identity-contract tests.
- `frontend/app/intake/page.tsx` — uses the shared strict flow.
- `frontend/app/project/[id]/ProjectView.tsx` — scoped run loading and URL-based demo selection.
- `frontend/app/project/[id]/council/CouncilView.tsx` — navigation context only.
- `frontend/app/project/[id]/kit/KitView.tsx` — navigation context and integration notices.
- `frontend/components/layout/AppHeader.tsx` — scoped navigation links.
- `frontend/components/layout/ProjectRoute.tsx` — project-scoped view lifetime.
- `frontend/components/telegram/TelegramConsole.tsx` — explicit simulated/observed label.
- `frontend/components/telegram/LiveTelegramConsole.tsx` — honest readiness presentation and safe backend check.

New files:

- `frontend/lib/run-context.ts`
- `frontend/lib/intake-flow.ts`
- `frontend/components/telegram/presentation.ts`
- `frontend/tests/helpers/load-ts.mjs`
- `frontend/tests/navigation.test.mjs`
- `frontend/tests/intake-flow.test.mjs`
- `frontend/tests/local-flow.test.mjs`
- `frontend/tests/telegram-presentation.test.mjs`
- This report.

The working tree also contains earlier uncommitted Telegram implementation files. They were not reset, staged or published. A before/after content-hash check across 78 protected Telegram backend, engine, Council/Kit internal and environment files reported no changes.

## Verification

- Backend regression suite: **649 passed**, with outbound network access blocked and temporary fallback data directories; **zero network attempts**. Existing Starlette/httpx deprecation warning remains.
- Frontend: **19 passed**, including existing Telegram state tests, actual header rendering, actual Kit/Council header wiring, mock and real intake shape checks, invalid-response rejection, and Telegram presentation states.
- Practical offline flow check: actual FastAPI mock and persisted real responses are produced using TestClient with network connections disabled. They are replayed through the real frontend API client and intake flow, then through the rendered shared navigation. Real project/run files and generated Kit ownership are checked. No HTTP listener or browser port is opened.
- TypeScript: `npx tsc --noEmit` passed.
- Frontend ESLint: `npm run lint` passed.
- Backend changed-file Ruff check passed.
- Mock-mode production build passed with the existing Next.js vulnerability warning.
- Real-mode production build compiled, type-checked and generated every page, but the build command exited 1 at the existing Next.js 16.4.0 security diagnostic. This is not reported as a clean production-build pass. No unrelated dependency upgrade was attempted; address the advisory before deployment.
- `git diff --check` passed.

Commands used for frontend checks, from `frontend/`:

```sh
node --test tests/*.test.mjs
npx tsc --noEmit
npm run lint
NEXT_PUBLIC_TELEGRAM_MODE=mock npm run build
NEXT_PUBLIC_TELEGRAM_MODE=real npm run build
```

A browser click-through and real Telegram pilot have not been performed. The Phase 3B delivery limits, manual reconciliation of unknown outcomes, independent webhook/operator credentials and live-action approval requirements remain unchanged; see [Telegram integration](telegram.md).
