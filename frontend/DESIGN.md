# Frontend design guide

The screens follow the boards in `Market Arena UI Ideas` (5 screens, dark theme, one lime accent).
Everything is a **mockup on mock data**: layout, colours and motion are final-ish, text is placeholder.

## The 5 screens

| # | Screen | Route | Owner | Page file |
|---|---|---|---|---|
| 1 | Live Arena + Glass-Box | `/project/[id]` | C (Arena), A (Glass-Box) | `app/project/[id]/ProjectView.tsx` |
| 2 | Idea Intake + Packs | `/intake` | C | `app/intake/page.tsx` |
| 3 | Arena Council verdict | `/project/[id]/council` | B | `app/project/[id]/council/CouncilView.tsx` |
| 4 | Scenario compare | `/compare` | A | `app/compare/page.tsx` |
| 5 | Experiment Kit + Telegram | `/project/[id]/kit` | B (Kit), C (Telegram) | `app/project/[id]/kit/KitView.tsx` |

`/` lists them. `/dev/arena`, `/dev/glassbox`, `/dev/council` render one component alone.
The nav pills in the header link the screens (`components/layout/AppHeader.tsx`). Pages are not final: moving a
screen means changing its route folder and the `NAV` list.

## Shared (change only after telling the team)

| What | Where |
|---|---|
| Colour, font and motion tokens | `app/globals.css` (`@theme`). Use as classes: `bg-surface`, `border-line`, `text-muted`, `text-accent`, `font-display`, `font-mono` |
| Fonts (self-hosted) | `app/fonts/`, wired in `app/layout.tsx` |
| Segment and option colours | `lib/theme.ts` (`segmentStyle`, `optionStyle`) |
| UI primitives | `components/ui`: `Card` (variants), `Button`, `Pill`, `SectionLabel`, `Stat`, `ProgressBar`, `DivergingBar`, `SegmentDot` |
| Page chrome | `components/layout`: `AppHeader`, `PageShell` (per-screen background glow), `Logo`, `ProjectRoute` |
| Contract types | `lib/types.ts` (mirrors `backend/common/contracts.py`) |

Build new UI from these primitives instead of writing new colours or spacing, so every screen stays consistent.

## Who owns which components

| Folder | Owner |
|---|---|
| `components/glassbox`, `components/compare`, `app/compare` | A |
| `components/council`, `components/kit` | B |
| `components/arena`, `components/intake`, `components/telegram`, `app/intake`, `app/project/[id]/ProjectView.tsx` | C |

## Mock data

Placeholder text lives in `lib/mock/*.ts` (one file per screen), not inside components. To make a part real:
fetch it from the API (`lib/api.ts`), pass it as props, and delete the matching constant. Frozen component
props are unchanged: `Arena`, `GlassBoxDrawer`, `CouncilPanel`.

Parts of the design the contracts do not carry yet (they use mock data): customer quotes and numeric what-if
bars (Council), Glass-Box profile line (budget, incumbent), aggregate flip percentages (Compare), trial length,
Telegram counts and results. Add them as **optional** contract fields with all three people agreeing.

## Adding a project page

Pages under `/project/[id]/...` must use `ProjectRoute` (see the comment in
`components/layout/ProjectRoute.tsx`); this Next.js version requires runtime params inside `<Suspense>`.

## Notes

- Mock API: `make api` (port 8000). The mock Glass-Box returns the same fixture for any agent id.
- The Arena draws one DOM button per dot, fine for the 80-agent fixture. For 1,000 dots at 60 fps switch the
  internals to canvas/Pixi (C); the props stay the same.
