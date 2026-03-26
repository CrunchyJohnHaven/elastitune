# ElastiTune Roadmap

> **Last updated:** 2026-03-26
> **Goal:** Keep the docs and backlog aligned with the current dual-mode product.

This roadmap mirrors the 5.4 review backlog and groups work by milestone rather than by owner.

## Milestone 1: Documentation And Onboarding

- Refresh the README and point people to the happy path.
- Document local development and testing in `docs/CONTRIBUTING.md`.
- Add benchmark guidance in `docs/BENCHMARKS.md`.
- Add a committee mode explainer in `docs/committee.md`.
- Document the API surface in `docs/api-reference.md`.
- Publish the human demo narrative in `docs/demo-narrative.md`.
- Keep the task list current for future reviews.

## Milestone 2: Core Search And Committee Foundations

- Split `backend/services/run_manager.py` into clearer search and committee responsibilities.
- Add persistence and history for committee runs.
- Tighten run orchestration, concurrency, and recovery behavior.
- Keep the search and committee contracts strongly typed and stable.

## Milestone 3: Frontend Experience

- Smooth the run telemetry and history presentation.
- Improve loading, skeleton, and error states.
- Tighten accessibility and theme consistency.
- Continue extracting large components into smaller, easier-to-scan pieces.

## Milestone 4: Integrations And Extensibility

- Research and prototype Kibana integration.
- Evaluate official Elastic clients and parsing libraries.
- Prototype a vector-search path and stronger recommendation heuristics if the product direction justifies it.

## Milestone 5: Long-Term Vision

- Cross-index optimization.
- Adaptive persona weighting.
- Interactive persona creation.
- Real-time collaboration.
- Auto-tuning suggestions.
- Elastic Cloud deployment workflow.
- Plugin APIs for metrics, personas, and connectors.

## Detailed Backlog

### Docs And Onboarding

- `DOC-1` Revise `README.md` to highlight dual mode, the happy path, and the executive summary.
- `DOC-2` Add an architecture diagram and reference it from the docs.
- `DOC-3` Add `docs/CONTRIBUTING.md` with local dev workflow and troubleshooting.
- `DOC-4` Add `docs/BENCHMARKS.md` for the benchmark harness.
- `DOC-5` Add `docs/committee.md` for personas and committee mode.
- `DOC-6` Add `docs/api-reference.md` with actual request and response models.
- `DOC-7` Keep this task list aligned with the next milestone set.
- `DOC-8` Add `docs/demo-narrative.md` with a presenter-friendly script.
- `DOC-10` Add issue templates for bugs, features, and docs improvements.

### Bugs And UX Polish

- `BUG-1` Keep cumulative resolved and missed counts stable in the right rail.
- `BUG-2` Smooth elapsed time in the telemetry bar.
- `BUG-3` Clarify query count labels and tooltips.
- `BUG-4` Simplify the landing page and collapse advanced options.
- `BUG-5` Normalize network and HTTP errors into friendly messages.
- `BUG-6` Add skeletons and loading states to run and report screens.
- `BUG-8` Improve accessibility and centralize theme tokens.
- `BUG-9` Tighten demo mode guardrails so live indices cannot be called accidentally.
- `BUG-10` Fix test warnings and keep the backend test suite clean.

### Backend Architecture And Performance

- `ARCH-1` Split the run manager by mode.
- `ARCH-2` Clean up the old engine layer.
- `ARCH-3` Replace the simulated compression benchmark with a real benchmark.
- `ARCH-4` Improve the optimizer search strategy.
- `ARCH-5` Make persona simulation more realistic.
- `ARCH-6` Add committee run history endpoints and UI support.
- `ARCH-7` Audit WebSocket publishing and concurrency.
- `ARCH-8` Add fault tolerance and recovery around external calls.
- `ARCH-9` Harden user input against injection and unsafe payloads.
- `ARCH-10` Expand backend test coverage.

### Frontend Enhancements

- `FE-1` Refine the top telemetry bar.
- `FE-2` Unify styling tokens.
- `FE-3` Consolidate shared store logic where it helps.
- `FE-4` Add reusable skeleton components.
- `FE-5` Improve accessibility and focus handling.
- `FE-6` Add persistent run history pages.
- `FE-7` Update the guided tour to match the simplified flow.
- `FE-8` Refactor large components into smaller pieces.
- `FE-9` Remove dead frontend code.
- `FE-10` Improve error boundaries and retry flows.

### Kibana And Ecosystem

- `KBN-1` Research Kibana plugin architecture.
- `KBN-2` Prototype a Kibana plugin.
- `KBN-3` Define the event schema for Kibana.
- `KBN-4` Evaluate Beats and Logstash ingestion.
- `KBN-5` Document security and authentication settings.

### GitHub And Library Research

- `GH-1` Survey relevant open-source projects.
- `GH-2` Evaluate Elastic clients.
- `GH-3` Identify document parsing libraries.
- `GH-4` Recommend UI component libraries.

### Future Vision

- `X-1` Cross-index optimization.
- `X-2` Adaptive persona weighting.
- `X-3` Interactive persona creation.
- `X-4` Real-time collaboration.
- `X-5` Auto-tuning suggestions.
- `X-6` Elastic Cloud deployment workflow.
- `X-7` Enterprise security personas.
- `X-8` AI-assisted document rewriting.
- `X-9` Synthetic query generation improvements.
- `X-10` Plugin marketplace and extensibility.
