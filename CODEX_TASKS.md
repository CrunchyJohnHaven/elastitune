# ElastiTune — Final Deploy Task List

> **Last updated:** 2026-03-26
> **Goal:** Ship to GitHub (public repo) and deploy on Replit
>
> **Current state:** All 5 benchmarks working (products, books, workplace, security-siem, tmdb-movies). Overnight run complete: 69,146 experiments, +8% to +1,192% improvements. Continue Optimization bug fixed (cumulative tracking via `originalBaselineScore`, `priorExperimentsRun`, `priorImprovementsKept`). Frontend builds cleanly, backend runs on :8000, frontend on :5173.

---

## P0 — Ship-Blocking (must fix before deploy)

### P0-1: Python linting pass (ruff/flake8)
Run `ruff check` across all backend Python files and fix any errors. Ensure CI-clean output.
- **Files:** `backend/**/*.py`, `overnight_run.py`, `benchmarks/**/*.py`
- **Complexity:** S
- **Codex:** Yes — fully autonomous

### P0-2: Expand .env.example with all required vars
Current `.env.example` only covers LLM and cost settings. Add `ELASTICSEARCH_URL`, `ELASTICSEARCH_API_KEY`, `CORS_ORIGINS`, and any other vars referenced in `backend/config.py`.
- **Files:** `.env.example`, `backend/config.py`
- **Complexity:** S
- **Codex:** Yes — autonomous (read config.py, mirror vars)

### P0-3: Update Dockerfile and docker-compose.yml for Replit
Existing `docker-compose.yml` and `Dockerfile.backend`/`Dockerfile.frontend` need review. Ensure compose brings up ES + backend + frontend together, ports are correct, and it works on Replit (respect `replit.nix`).
- **Files:** `docker-compose.yml`, `Dockerfile.backend`, `Dockerfile.frontend`, `replit.nix`, `docker/nginx.conf`
- **Complexity:** M
- **Codex:** Needs human review — Replit-specific constraints

### P0-4: Verify Continue Optimization shows cumulative progress
Write or run a test that starts a run, stops it, continues, and confirms the UI shows cumulative experiment count and improvement (not reset to 0). Validates the `originalBaselineScore`/`priorExperimentsRun` fix.
- **Files:** `backend/services/run_manager.py`, `frontend/src/hooks/useRunSocket.ts`, `frontend/src/store/useAppStore.ts`, `backend/tests/`
- **Complexity:** M
- **Codex:** Partially — can write the backend test; manual UI verification needed

### P0-5: Ensure all 5 benchmark presets accessible from Connect screen
Verify the Connect screen preset list includes products, books, workplace, security-siem, and tmdb-movies. Check that selecting each one populates the correct index/query config.
- **Files:** `frontend/src/components/connect/ConnectForm.tsx`, `frontend/src/screens/ConnectScreen.tsx`, `backend/api/routes_connect.py`
- **Complexity:** S
- **Codex:** Yes — autonomous (verify preset data, fix if missing)

### P0-6: Graceful fallback when Elasticsearch is unavailable
When ES is down or unreachable, the app should show a clear error message instead of crashing or hanging. Add a health-check gate on connect and surface the error in the UI.
- **Files:** `backend/services/es_service.py`, `backend/api/routes_health.py`, `frontend/src/components/connect/ConnectForm.tsx`
- **Complexity:** S
- **Codex:** Yes — autonomous

### P0-7: Audit and resolve all TODO/FIXME/HACK comments
Scan the entire codebase for leftover TODO/FIXME/HACK markers. Resolve or convert to tracked GitHub issues.
- **Files:** All (`backend/`, `frontend/src/`, `benchmarks/`)
- **Complexity:** S
- **Codex:** Yes — autonomous (current scan shows zero, but re-verify after other changes)

---

## P1 — Polish for Demo

### P1-1: Fix ExplainerPanel "What We Found" loading state
When data is still loading the ExplainerPanel renders a "?" in the header. Show a skeleton/loading state instead.
- **Files:** `frontend/src/components/run/ExplainerPanel.tsx`
- **Complexity:** S
- **Codex:** Yes — autonomous

### P1-2: Add Karpathy-style improvement chart to Report screen
Add a score-over-time line graph to ReportScreen using the `scoreTimeline` data from run results. Show baseline as a horizontal dashed line, with each experiment's score plotted chronologically.
- **Files:** `frontend/src/screens/ReportScreen.tsx`, `frontend/src/components/report/ImprovementGraph.tsx`
- **Complexity:** M
- **Codex:** Yes — autonomous (ImprovementGraph.tsx already exists, may need wiring or enhancement)

### P1-3: ReportScreen cumulative chain display for continued runs
When viewing a report from a continued run, show the full chain of improvements across all legs, not just the latest leg.
- **Files:** `frontend/src/screens/ReportScreen.tsx`, `frontend/src/components/report/ExecutiveSummary.tsx`
- **Complexity:** M
- **Codex:** Yes — autonomous

### P1-4: Benchmark result badges on Connect screen presets
Show the last-run result on each benchmark preset card (e.g., "Last run: +94%, 1,200 experiments").
- **Files:** `frontend/src/components/connect/ConnectForm.tsx`, `frontend/src/screens/ConnectScreen.tsx`, `backend/api/routes_connect.py`
- **Complexity:** M
- **Codex:** Partially — backend endpoint may need a "last run summary" query; UI is autonomous

### P1-5: Mobile/responsive layout for demo
Ensure the Connect, Run, and Report screens render reasonably on tablet and phone viewports. Focus on the Run screen's three-column layout collapsing gracefully.
- **Files:** `frontend/src/styles.css`, `frontend/src/components/run/*.tsx`, `frontend/src/components/layout/*.tsx`
- **Complexity:** M
- **Codex:** Partially — can generate CSS; visual QA needs human review

---

## P2 — Feature Completions

### P2-1: Wire connectionConfig in ReportScreen for Continue from Report
The "Continue Optimizing" button on the Report screen should reconnect using the saved `connectionConfig` so the user doesn't have to re-enter ES details.
- **Files:** `frontend/src/screens/ReportScreen.tsx`, `frontend/src/store/useAppStore.ts`
- **Complexity:** S
- **Codex:** Yes — autonomous

### P2-2: Export Report as PDF
Add a "Download PDF" button to ReportScreen that generates a PDF of the executive summary, improvement graph, and experiment table.
- **Files:** `frontend/src/screens/ReportScreen.tsx`, new utility `frontend/src/lib/exportPdf.ts`
- **Complexity:** M
- **Codex:** Yes — autonomous (use html2canvas + jspdf or similar)

### P2-3: Comparison view between two runs
Build out the existing `CompareScreen.tsx` to allow selecting two completed runs and viewing a side-by-side diff of their search profiles, scores, and experiments.
- **Files:** `frontend/src/screens/CompareScreen.tsx`, `backend/api/routes_runs.py`
- **Complexity:** L
- **Codex:** Partially — scaffold is autonomous; data model and UX need human review

### P2-4: Vector/hybrid search optimization
Extend the optimizer to support kNN and hybrid search strategies, not just lexical BM25. Requires new search space dimensions and evaluator updates.
- **Files:** `backend/engine/optimizer.py`, `backend/engine/optimizer_search_space.py`, `backend/engine/evaluator.py`
- **Complexity:** L
- **Codex:** Needs human review — algorithm design decisions required

### P2-5: Scheduled re-optimization (cron-based)
Allow users to schedule periodic re-optimization runs (e.g., nightly). Backend cron job triggers a run against stored config.
- **Files:** `backend/services/run_manager.py`, new `backend/services/scheduler_service.py`, `backend/api/routes_runs.py`
- **Complexity:** L
- **Codex:** Partially — can scaffold; scheduling infra needs human review

---

## P3 — Future Vision

### P3-1: ElastiProbe security mode
Proactive SIEM search testing — generate adversarial queries that test detection rule coverage, report gaps.
- **Files:** New `backend/engine/security_probe.py`, `backend/api/routes_security.py`
- **Complexity:** L
- **Codex:** Needs human review — security domain expertise

### P3-2: Multi-index optimization
Optimize search across multiple related indices simultaneously (e.g., logs + metrics + traces).
- **Files:** `backend/engine/optimizer.py`, `backend/services/es_service.py`
- **Complexity:** L
- **Codex:** Needs human review — cross-index scoring model

### P3-3: Elastic Cloud API integration
Direct deployment of optimized search profiles to Elastic Cloud via their management API.
- **Files:** New `backend/services/elastic_cloud_service.py`, `backend/api/routes_connect.py`
- **Complexity:** L
- **Codex:** Needs human review — API auth and deployment safety

### P3-4: Plugin architecture for custom evaluators
Allow users to register custom scoring functions (e.g., domain-specific relevance) that plug into the optimization loop.
- **Files:** `backend/engine/evaluator.py`, new `backend/engine/plugin_loader.py`
- **Complexity:** L
- **Codex:** Needs human review — API design

### P3-5: A/B test deployment workflow
Deploy two search profiles side-by-side in production, route traffic, and measure real-user impact.
- **Files:** New `backend/services/ab_test_service.py`, `frontend/src/screens/ABTestScreen.tsx`
- **Complexity:** L
- **Codex:** Needs human review — production safety concerns
