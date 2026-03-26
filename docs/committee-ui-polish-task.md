# Task for Opus/Sonnet: Committee Mode Visual Polish

You are working in `/Users/johnbradley/Desktop/ElastiTune`.

## Goal

Polish the new committee-mode frontend so it feels impressively boardroom-ready for internal Value Engineering demos, without changing the search-mode workflow and without rewriting the backend contracts.

## Current State

Committee mode already exists and works end to end:

- Setup screen: `frontend/src/screens/CommitteeScreen.tsx`
- Live run screen: `frontend/src/screens/CommitteeRunScreen.tsx`
- Report screen: `frontend/src/screens/CommitteeReportScreen.tsx`
- Committee components live in `frontend/src/components/committee/`
- Shared shell/layout components already exist and search mode must remain intact

The backend and websocket event model are already wired. Treat them as stable unless a tiny frontend-facing shape fix is absolutely necessary.

## What to Improve

Focus only on the committee-mode UI/UX:

1. Make the center “committee space” feel more alive and more legible.
2. Improve visual hierarchy in the right rail so persona objections, missing info, and score posture are easier to scan.
3. Make the setup and report screens feel more polished and presentation-worthy.
4. Preserve the current layout structure and keep the app responsive on laptop screens.

## Specific Targets

- `frontend/src/components/committee/CommitteeSpaceCanvas.tsx`
  - Make coalition/alignment visually clearer.
  - Add stronger sense of motion and agreement/disagreement without introducing a heavy dependency.
  - Keep the experience intentional, not generic dashboard filler.

- `frontend/src/components/committee/CommitteeRightRail.tsx`
  - Improve persona list readability.
  - Make the selected persona detail feel more executive-briefing-quality.
  - Highlight top objection and strongest risk/missing items more clearly.

- `frontend/src/screens/CommitteeScreen.tsx`
  - Make the upload/setup experience feel more premium and less like a raw form.
  - Preserve the current inputs and flow.

- `frontend/src/screens/CommitteeReportScreen.tsx`
  - Improve spacing, typography, and summary presentation.
  - Keep the export/rewrite information easy to scan.

## Constraints

- Do not break search mode.
- Do not remove existing committee functionality.
- Do not introduce a large UI framework.
- Prefer editing the existing components over introducing many new abstractions.
- Keep changes frontend-only unless a tiny contract change is required.

## Validation

Before finishing:

- Run `npm run build` in `frontend/`
- Note any tradeoffs or residual issues

## Deliverable

Make the changes directly in the repo and report back with:

1. What you changed
2. Files touched
3. Anything that still feels rough

