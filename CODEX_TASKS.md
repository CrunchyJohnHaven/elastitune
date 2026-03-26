# ElastiTune Task Map

> **Last updated:** 2026-03-26
> **Goal:** keep the backlog readable, grouped by milestone, and aligned with the current dual-mode product.

## Milestone 1: Docs And Onboarding

Order of operations:

1. Refresh the README and keep the happy path obvious.
2. Keep the architecture diagram, local development guide, benchmark guide, and committee guide in sync.
3. Maintain the API reference and demo narrative.
4. Keep environment variables and issue templates easy to discover.

Deliverables:

- [README](README.md)
- [Architecture diagram](doc-assets/architecture.svg)
- [Local dev guide](docs/CONTRIBUTING.md)
- [Benchmark guide](BENCHMARKS.md)
- [Committee guide](docs/committee.md)
- [API reference](docs/api-reference.md)
- [Demo narrative](docs/demo-narrative.md)
- [Executive Summary](docs/executive-summary.md)
- [Issue templates](.github/ISSUE_TEMPLATE/)

## Milestone 2: Trust Rails And UX Polish

Order of operations:

1. Keep telemetry counters and elapsed time stable.
2. Keep the landing flow obvious and low-friction.
3. Normalize frontend errors into friendly messages.
4. Add loading skeletons and accessibility affordances.
5. Keep shared theme tokens centralized.

Target areas:

- `frontend/src/components/layout/TopTelemetryBar.tsx`
- `frontend/src/components/layout/RightRail.tsx`
- `frontend/src/components/connect/ConnectForm.tsx`
- `frontend/src/screens/ConnectScreen.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/components/ui/Skeleton.tsx`
- `frontend/src/lib/theme.ts`
- `frontend/src/components/walkthrough/WalkthroughOverlay.tsx`

## Milestone 3: Committee Mode Reproducibility

Order of operations:

1. Keep committee telemetry readable and monotonic.
2. Reuse the same loading strategy on committee screens.
3. Strengthen committee docs and report exports.
4. Add history and persistence when the backend supports it.

Target areas:

- `frontend/src/components/committee/CommitteeTopBar.tsx`
- `frontend/src/components/committee/CommitteeRightRail.tsx`
- `frontend/src/screens/CommitteeRunScreen.tsx`
- `frontend/src/screens/CommitteeReportScreen.tsx`
- `backend/api/routes_committee.py`
- `backend/committee/personas.py`
- `backend/committee/evaluator.py`

## Milestone 4: Backend Foundations

Order of operations:

1. Keep the live demo guardrails strict.
2. Reduce error-prone shared code in the run manager.
3. Expand persistence and recovery once the UI needs history views.
4. Improve tests around continuation and report generation.

Target areas:

- `backend/services/demo_service.py`
- `backend/services/run_manager.py`
- `backend/services/persistence_service.py`
- `backend/tests/`

## Milestone 5: Research And Integration Bets

Order of operations:

1. Survey candidate open-source projects and libraries.
2. Prototype the highest-value integration only after the research looks strong.
3. Keep the rest as design notes until the backend and UX settle.

Research notes:

- [GitHub project survey](docs/research/github-projects.md)
- [Elastic client survey](docs/research/elastic-clients.md)
- [Document parser survey](docs/research/document-parsers.md)
- [UI library survey](docs/research/ui-component-libraries.md)

## Milestone 6: Future Expansion

These are intentionally deferred until the demo path and committee path are stable:

- Cross-index optimization
- Adaptive persona weighting
- Interactive persona creation
- Real-time collaboration
- Auto-tuning suggestions
- Elastic Cloud deployment workflow
- Plugin marketplace and extensibility

## Notes

- Keep new work aligned with the happy-path demo flow first.
- Prefer small, testable changes over broad refactors unless a refactor unlocks multiple backlog items.
- When adding new docs or UI screens, link them from the README so new contributors can find them quickly.
