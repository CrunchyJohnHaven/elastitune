# ElastiTune Research Context

Updated: 2026-03-25 / 2026-03-26  
Repository root: `/Users/johnbradley/Desktop/ElastiTune`

## Purpose

This document is a high-signal handoff packet for a strong external model such as ChatGPT Pro. It is intentionally opinionated and practical. It is not meant to be marketing copy. It is meant to help another model or engineer rapidly understand:

1. What ElastiTune is today
2. What is real vs simulated
3. What has already been fixed
4. What is still broken, confusing, or incomplete
5. What the next implementation tasks should be

The user wants this project thoroughly stabilized and simplified. The user is frustrated by catching avoidable bugs. The user also wants the buyer committee mode critiqued and improved, but the search mode and landing/setup experience still need hardening.

At the end of this document there is a direct instruction block for ChatGPT Pro telling it to return a `next_tasks.md` file.

## Executive Summary

ElastiTune is a dual-mode optimization demo/product:

- Search Mode:
  - Connect to Elasticsearch
  - Inspect index/mappings/sample docs
  - Build or upload an evaluation set
  - Run a mutation loop over search-profile knobs
  - Score changes with nDCG@10
  - Show results in a live "mission control" UI
- Committee Mode:
  - Upload a pitch/proposal/deck/brief
  - Parse it into sections
  - Generate or seed a buying committee
  - Score the content per persona
  - Rewrite sections to improve weighted consensus
  - Show live committee reactions and produce a report/export

The repo already has real strengths:

- Good visual ambition
- Strong typing between backend and frontend
- Decent event streaming architecture
- A genuinely interesting product idea in committee mode
- A useful benchmark direction via Elastic's e-commerce sample app

But it also has important weaknesses:

- Search mode was originally simulating live evaluation rather than executing real ES-backed relevance scoring
- Search/committee orchestration are still too centralized inside one large manager
- Some UI counters were derived from transient state and could move backward or appear static
- Landing/setup UX drifted into "too much at once"
- The repo contains older engine-layer code that is confusing because much of it is not the active path
- Committee mode is compelling but still less battle-hardened than search mode

## What Was Recently Fixed

These are important because a future model should not waste time rediscovering them.

### 1. Search evaluation is now wired to real result rankings

Previously, live-mode `_evaluate_profile()` in `backend/services/run_manager.py` used simulated/random ranks.

That was replaced so the run manager now:

- uses actual `ESService.execute_profile_query()`
- collects ranked document IDs from Elasticsearch
- computes real nDCG@10 against `EvalCase.relevantDocIds`
- records missed queries per experiment

Relevant files:

- `backend/services/run_manager.py`
- `backend/services/es_service.py`

Important note:

- The demo mode is still demo mode and replays a polished scenario
- The live search path is the one that now matters for real credibility

### 2. Search snapshots and reports now persist

Search mode gained lightweight SQLite persistence via:

- `backend/services/persistence_service.py`

This persists:

- search connections
- search run snapshots
- search reports

Startup now initializes persistence in:

- `backend/main.py`

Search routes now expose persisted history/report retrieval through:

- `backend/api/routes_runs.py`

Important note:

- This persistence is currently search-mode only
- Committee-mode persistence is still an open follow-up

### 3. Persona generation is more data-aware

Previously, live search runs always used the same security personas, which broke credibility on non-security indexes.

Now:

- LLM-backed persona generation exists in `backend/services/llm_service.py`
- routes build more domain-aware personas in `backend/api/routes_runs.py`
- heuristic fallback can detect product-catalog style data and switch to e-commerce personas
- a more generic fallback also exists for general corpora

This is still not fully polished, but it is significantly better than forcing "SOC Analyst" onto unrelated datasets.

### 4. Landing page was simplified again

The landing screen had drifted into a more complicated, intimidating layout.

The current direction is:

- default emphasis on `Launch Demo`
- a benchmark preset for the local Elastic benchmark
- custom index controls hidden behind an explicit collapsible section
- advanced LLM controls behind a separate collapsible section
- better messaging when backend is unreachable

Relevant files:

- `frontend/src/components/connect/ConnectForm.tsx`
- `frontend/src/screens/ConnectScreen.tsx`
- `frontend/src/lib/api.ts`

### 5. Demo-launch `Failed to fetch` path was hardened

The user saw a raw `Failed to fetch` on launch/demo. Two layers were involved:

- actual backend-side committee integration drift at one point
- poor frontend error normalization

The current frontend now translates network failure to a more useful message:

- `Cannot reach the ElastiTune backend. Make sure the API server is running.`

Relevant file:

- `frontend/src/lib/api.ts`

### 6. Report improvements

The report now has a more structured summary model and less brittle headline logic.

Notable report work:

- plain-English overview
- recommended next steps
- real duration fields in report payload generation
- report page scrolling bug fixed

Relevant files:

- `backend/models/report.py`
- `backend/services/report_service.py`
- `backend/services/demo_service.py`
- `frontend/src/components/report/ExecutiveSummary.tsx`
- `frontend/src/screens/ReportScreen.tsx`

### 7. Committee mode import/runtime stability was repaired

There was a real committee-side mismatch where `routes_committee.py` expected a persona builder contract that did not cleanly exist on disk / in shape.

Current committee persona builder file:

- `backend/committee/personas.py`

Tests and smoke now pass again after restoring and aligning this path.

## Verified State Right Now

The following were run and succeeded from this checkout:

### Backend tests

```bash
python3 -m pytest backend/tests -q
```

Result at last verification:

- `8 passed`

### Backend smoke test

```bash
python3 backend/scripts/smoke_app.py
```

Result at last verification:

- health ok
- search connect ok
- search run ok
- committee connect ok
- committee run ok
- committee report ok
- committee export ok
- all smoke checks passed

### Backend compile check

```bash
python3 -m compileall backend
```

Passed during earlier stabilization passes.

### Frontend build

```bash
cd frontend && npm run build
```

Latest result:

- build succeeded
- lazy-loaded route chunks produced

### Runtime launch

At the time of writing, both services were launched locally:

- frontend dev server on `http://127.0.0.1:5173`
- backend health on `http://127.0.0.1:8000/api/health`

Playwright was used to confirm:

- landing page loads
- demo launch navigates into a live run

## Important Current User Complaints

These are high-priority because they come directly from the user.

### Complaint 1: Landing page became scary and complicated

The user explicitly said the setup screen had become too complicated and less intuitive than before.

The current simplification work helps, but more likely needs to happen:

- reduce cognitive load further
- privilege one clear "happy path"
- keep advanced controls hidden unless requested
- avoid throwing dense explanatory blocks at first-time users

### Complaint 2: Missed/resolved counters felt wrong

The user observed:

- missed count went up and then down
- the core count felt static

This was traced to transient frontend derivation:

- `RightRail` originally used current persona states to compute `Resolved` and `Missed`
- that meant counts could regress as personas changed state

This has now been changed to cumulative counters derived from persona totals:

- `resolved = successes + partials`
- `missed = failures`

Relevant file:

- `frontend/src/components/layout/RightRail.tsx`

### Complaint 3: Eval-case count felt static

The user objected to a static `127` display during the demo run.

This is partly semantic confusion:

- `127` is the benchmark-set size, not live progress

A new direction was implemented so the center label and top telemetry can communicate live throughput more clearly by showing cumulative `queries tested` rather than only the fixed test-set size.

Relevant files:

- `frontend/src/components/run/FishTankCanvas.tsx`
- `frontend/src/components/layout/TopTelemetryBar.tsx`

Important note:

- This specific counter behavior should still be visually re-checked in-browser after the latest change
- the code builds, but a fresh user-path visual confirmation is still worth doing

### Complaint 4: Elapsed time feels not neat/smooth

The user explicitly said:

- elapsed seconds is not counting up neatly

Likely reasons:

- run metrics are updated on heartbeat intervals rather than every animation frame
- demo mode may publish elapsed time in coarser chunks
- top bar forces a rerender every second, but displayed elapsed may still reflect backend metrics snapshots and not a smooth local derivation from `startedAt`

This is still a valid open issue and should be treated as unresolved polish/UX debt.

Probable fix direction:

- derive a local display clock from `startedAt` plus current client time while run stage is `running`
- use backend metric elapsed seconds as authoritative checkpoint/fallback
- snap to completed elapsed time on completion

Files likely involved:

- `frontend/src/components/layout/TopTelemetryBar.tsx`
- possibly `frontend/src/components/layout/RightRail.tsx`
- possibly `frontend/src/components/run/HeroMetrics.tsx`

## Repo Structure

Top level:

- `README.md`
- `start.sh`
- `backend/`
- `frontend/`
- `benchmarks/`
- `docs/`
- `DEEP_RESEARCH_PROMPT.md`

### Backend structure

- `backend/main.py`
  - FastAPI entrypoint
  - creates `RunManager`
  - mounts API routers
  - serves built frontend in production mode
- `backend/api/`
  - `routes_connect.py`
  - `routes_runs.py`
  - `routes_committee.py`
  - `routes_health.py`
  - `ws_runs.py`
- `backend/services/`
  - `run_manager.py`
  - `es_service.py`
  - `llm_service.py`
  - `demo_service.py`
  - `report_service.py`
  - `persistence_service.py`
- `backend/models/`
  - `contracts.py`
  - `runtime.py`
  - `report.py`
- `backend/committee/`
  - `document_parser.py`
  - `evaluator.py`
  - `industry_profiles.py`
  - `models.py`
  - `personas.py`
  - `reporting.py`
  - `rewrite_engine.py`
  - `runtime.py`
- `backend/engine/`
  - old / partially unused architecture layer
  - contains evaluators, optimizers, query generation, etc.
  - needs cleanup or reintegration decision
- `backend/scripts/smoke_app.py`
- `backend/tests/`

### Frontend structure

- `frontend/src/routes.tsx`
  - `/`
  - `/run/:runId`
  - `/report/:runId`
  - `/committee`
  - `/committee/run/:runId`
  - `/committee/report/:runId`
- `frontend/src/screens/`
  - `ConnectScreen.tsx`
  - `RunScreen.tsx`
  - `ReportScreen.tsx`
  - `CommitteeScreen.tsx`
  - `CommitteeRunScreen.tsx`
  - `CommitteeReportScreen.tsx`
- `frontend/src/components/layout/`
  - `TopTelemetryBar.tsx`
  - `LeftRail.tsx`
  - `RightRail.tsx`
  - `ShellFrame.tsx`
- `frontend/src/components/run/`
  - `FishTankCanvas.tsx`
  - `ExperimentFeed.tsx`
  - `HeroMetrics.tsx`
  - `PersonaDetailCard.tsx`
  - `PersonaList.tsx`
  - `CompressionCard.tsx`
  - `ExplainerPanel.tsx`
  - `IndexSummaryMiniCard.tsx`
  - `RunControlBar.tsx`
- `frontend/src/components/committee/`
  - committee-specific live UI pieces
- `frontend/src/store/`
  - `useAppStore.ts`
  - `useCommitteeStore.ts`
- `frontend/src/lib/`
  - `api.ts`
  - `socket.ts`
  - `format.ts`
  - `theme.ts`

## Search Mode Deep Dive

### Setup flow

Entry point:

- `frontend/src/screens/ConnectScreen.tsx`
- `frontend/src/components/connect/ConnectForm.tsx`

User flows:

1. Launch demo
2. Load benchmark preset
3. Connect own Elasticsearch index

API call:

- `POST /api/connect`

Relevant backend route:

- `backend/api/routes_connect.py`

What `routes_connect.py` does:

1. If demo mode:
   - builds a canned `ConnectionContext` through `DemoService`
2. If live mode:
   - validates connection payload
   - pings Elasticsearch through `ESService`
   - fetches cluster info
   - analyzes index mappings and sample docs
   - detects domain
   - builds sample-doc previews
   - uses uploaded eval set, LLM-generated eval set, or heuristic eval set
   - builds baseline search profile
   - stores a `ConnectionContext`

### Run flow

Entry point:

- `POST /api/runs`

Relevant route:

- `backend/api/routes_runs.py`

Current live-run path:

1. build personas
2. create `RunContext`
3. create run in `RunManager`
4. start background tasks

Inside `RunManager`:

- `_optimizer_loop()`
- `_persona_simulator_loop()`
- `_compression_benchmark()`
- `_metrics_heartbeat()`

### Real scoring

Current real scoring path:

1. `_optimizer_loop()` creates candidate profile
2. `_evaluate_profile()` is called
3. `_evaluate_profile()` uses `ESService.execute_profile_query()`
4. ES results return ranked `_id`s
5. `_compute_ndcg_at_k()` computes nDCG@10 against `relevantDocIds`
6. query misses are stored on experiment records

### Search profile mutation space

Current heuristic search space still includes:

- `minimumShouldMatch`
- `tieBreaker`
- `phraseBoost`
- `multiMatchType`
- `fuzziness`
- `vectorWeight`
- `fusionMethod`
- `rrfRankConstant`
- `knnK`

Current logic still remains fairly simplistic:

- flat exploration
- some LLM suggestions
- plateau stop heuristic

This is a candidate for a more serious optimizer pass later.

### Demo mode

Demo mode is still a polished replay/simulation path through:

- `backend/services/demo_service.py`

It remains useful as a showpiece but should not be confused with a real benchmark.

## Committee Mode Deep Dive

### Setup flow

Entry point:

- `frontend/src/screens/CommitteeScreen.tsx`

API call:

- `POST /api/committee/connect`

Relevant route:

- `backend/api/routes_committee.py`

What happens:

1. upload a document
2. parse document bytes
3. build committee personas
4. create `CommitteeConnectionContext`
5. optionally preview summary/personas
6. start run

### Committee parser

Current parser lives in:

- `backend/committee/document_parser.py`

It supports:

- pdf
- pptx
- docx
- text-ish fallback

Important:

- output is canonicalized into section-oriented content
- not native slide-perfect regeneration
- parse warnings are surfaced

### Committee persona generation

Current file:

- `backend/committee/personas.py`

Behavior:

- derive industry profile from document content
- optionally coerce provided personas
- optionally use LLM-generated personas
- otherwise fall back to deterministic profile-based personas

This path is now stable enough to test, but it is still not a fully mature simulation engine.

### Committee evaluation and rewrite loop

Key files:

- `backend/committee/evaluator.py`
- `backend/committee/rewrite_engine.py`
- `backend/services/run_manager.py`

Current logic:

1. evaluate document baseline across personas
2. pick a section and rewrite proposal
3. re-evaluate affected section/personas
4. compute weighted consensus score
5. apply do-no-harm constraint
6. keep or revert rewrite

### Committee UI

Key files:

- `frontend/src/components/committee/CommitteeSpaceCanvas.tsx`
- `frontend/src/components/committee/CommitteeLeftRail.tsx`
- `frontend/src/components/committee/CommitteeRightRail.tsx`
- `frontend/src/components/committee/CommitteeTopBar.tsx`

The UI concept is strong:

- central document hub
- personas around it
- reaction fragments
- rewrite stream
- score timeline

The implementation is much better than a static report, but still needs product/UX refinement.

## Benchmark Harness

This is one of the strongest parts of the new direction.

Location:

- `benchmarks/elastic-product-store/`

Purpose:

- turn a real Elastic-owned sample app/data shape into a repeatable ElastiTune proof target

Important files:

- `benchmarks/elastic-product-store/setup_target.py`
- `benchmarks/elastic-product-store/create_index.py`
- `benchmarks/elastic-product-store/ingest_products.py`
- `benchmarks/elastic-product-store/eval-set.json`
- `benchmarks/elastic-product-store/README.md`

Expected local benchmark target:

- ES URL: `http://127.0.0.1:9200`
- Index: `products-catalog`
- Eval set: fixed JSON benchmark

This benchmark direction is much stronger than a generic self-contained demo because it can plausibly support:

- baseline score
- optimized score
- profile diff
- visible search-result improvements on real queries

## Known Architectural Problems

These are important. Another model should not romanticize the current structure.

### 1. `run_manager.py` is still a god object

The file owns:

- search run lifecycle
- committee run lifecycle
- scoring
- persona simulation
- compression benchmark flow
- publication
- snapshot handling

This is too much.

Recommended split:

- `search_run_manager.py`
- `committee_run_manager.py`
- maybe a thin shared publisher/subscription coordinator

### 2. Old engine layer is confusing

The `backend/engine/` directory contains prior architecture pieces:

- `optimizer.py`
- `evaluator.py`
- `field_detection.py`
- `persona_generator.py`
- `synthetic_queries.py`
- etc.

Some of this logic is useful. Some appears superseded. Right now the existence of both `engine/` and `services/` creates confusion over what the active system really is.

Recommended action:

- either delete/reduce dead engine files
- or intentionally reintegrate the ones that are now better than the service-layer inline implementations

### 3. Styling is still heavily inline

The frontend still leans very hard on inline style objects. This makes:

- large components harder to read
- visual consistency harder to maintain
- redesign passes noisier

A future cleanup should decide whether to:

- keep inline but aggressively centralize theme tokens and component primitives
- or migrate selective parts to CSS modules / styled primitives

### 4. Duplicate store patterns

`useAppStore` and `useCommitteeStore` use similar patterns. Not urgent, but there is likely room for better shared abstractions.

### 5. Committee mode still depends heavily on heuristic fallbacks

The heuristic path is acceptable for a demo but not truly authoritative. The UI should probably communicate evaluation source quality more explicitly.

## Open Issues and Suspicious Areas

This section is intentionally blunt.

### Search-mode open issues

- elapsed time display still feels uneven
- counter semantics still need visual QA after the latest cumulative counter changes
- compression benchmark remains simulated/theoretical
- optimizer search strategy remains simple
- top bar / center bar semantics should be made crystal clear

### Committee-mode open issues

- not yet persisted like search mode
- still tied too tightly into the shared run manager
- heuristic path is not clearly labeled as lower-confidence
- needs a sharper setup UX and likely a better preview contract
- should probably have a stronger report/export story for real internal use

### Setup / launch open issues

- `start.sh` works but is basic
- local runtime can drift if multiple backend servers are already bound to `8000`
- frontend still depends on backend health/proxy behavior and can show odd socket-state transitions

### Visual clarity open issues

- demo is still security-themed by default
- metric labels can still be misread
- some state is visually "alive" but semantically ambiguous

## High-Value Next Directions

These are the best ROI tasks if someone serious takes over.

### Priority 1

- finish and verify the cumulative/live counter semantics in the run UI
- smooth elapsed-time display locally
- add committee persistence
- add a real `/runs` history screen on the frontend for persisted search runs

### Priority 2

- split `run_manager.py`
- make compression benchmarking real
- improve optimizer strategy
- simplify landing page even further
- tighten benchmark onboarding into a more guided quickstart

### Priority 3

- clean up `backend/engine/`
- unify styling strategy
- unify run-store patterns where it helps
- improve error surfaces and skeleton/loading states

## File-by-File Areas Another Model Should Inspect First

If another model has limited context budget, start here in this order:

1. `backend/services/run_manager.py`
2. `backend/api/routes_connect.py`
3. `backend/api/routes_runs.py`
4. `backend/services/es_service.py`
5. `backend/services/persistence_service.py`
6. `backend/committee/personas.py`
7. `backend/api/routes_committee.py`
8. `frontend/src/components/connect/ConnectForm.tsx`
9. `frontend/src/screens/ConnectScreen.tsx`
10. `frontend/src/components/layout/TopTelemetryBar.tsx`
11. `frontend/src/components/layout/RightRail.tsx`
12. `frontend/src/components/run/FishTankCanvas.tsx`
13. `frontend/src/components/report/ExecutiveSummary.tsx`
14. `frontend/src/screens/CommitteeScreen.tsx`
15. `frontend/src/components/committee/CommitteeRightRail.tsx`

## Suggested Human Demo Narrative

If this is being used in front of internal Elastic stakeholders or prospects, the strongest current story is:

1. Start with demo mode to show the shape of the system quickly
2. Then switch to the local benchmark preset using the Elastic product-store index
3. Emphasize that live search scoring is now based on real ranked results, not canned animation
4. Show the report with profile diff and before/after lift
5. Position committee mode as the same optimization engine extended to stakeholder persuasion simulation

Avoid:

- overselling the committee mode as fully enterprise-ready
- pretending every visual metric is already perfect
- leading with advanced setup knobs

## ChatGPT Pro Instruction Block

The next model should treat this repository as an active product-hardening task, not a brainstorming exercise.

### Primary goal

Produce a file named `next_tasks.md` at the project root that lays out the best next execution plan for stabilizing and simplifying ElastiTune across both:

- search mode
- committee mode

### Required output expectations

Your response should:

1. Inspect the codebase directly, not only this document
2. Validate whether the claims in this document are still true
3. Prioritize tasks by impact and risk reduction
4. Prefer implementation-ready tasks over vague product ideas
5. Explicitly separate:
   - already fixed
   - still broken
   - likely broken but unverified
6. Return a `next_tasks.md` file that includes:
   - an executive summary
   - current verified status
   - top bugs
   - top UX simplifications
   - top architecture refactors
   - benchmark-path improvements
   - committee-mode improvements
   - a phased implementation plan
   - exact files/modules to touch per phase
   - recommended tests for each phase

### Specific priorities to evaluate

Please evaluate and propose next tasks for:

- elapsed-time smoothing in the run UI
- making all run counters semantically correct and monotonic where appropriate
- search run history UI
- committee-mode persistence
- committee setup simplification
- compression benchmark realism
- `run_manager.py` decomposition
- dead-code cleanup in `backend/engine/`
- benchmark setup UX and reproducibility

### Constraints

- Do not assume demo mode equals real mode
- Do not remove the visual ambition of the product
- Do simplify setup and reduce intimidation for first-time users
- Do preserve the benchmark direction
- Do be explicit when something is still heuristic or simulated

### Deliverable format

Write `next_tasks.md` in markdown at the repo root.

That file should be optimized for execution by another coding model or engineer, not for executive presentation.

It should contain:

- concise summary
- ranked task list
- implementation notes
- risks / assumptions
- verification checklist

## Closing Note

ElastiTune is no longer just a mockup. It now has enough real substrate that it can become a serious internal demo and potentially a credible evaluation tool. But it is still at the stage where clarity, trust, and correctness matter more than additional visual cleverness.

The best next work is not "make it flashier."  
The best next work is:

- stabilize the semantics
- simplify the UX
- persist the evidence
- make both product modes feel intentionally engineered rather than partially converged

