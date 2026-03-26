# ElastiTune

ElastiTune is a search-quality optimization lab for Elasticsearch. It connects to a search index, builds or accepts a benchmark query set, tests ranking changes automatically, and produces a before/after report with measurable lift.

It also includes a second product mode, Committee Mode, for document rewrites guided by simulated buyer personas.

## Why it exists

- Average benchmark lift in this repo’s overnight run pack: `+335%`
- Built-in benchmark systems: Product Store, Books Catalog, Workplace Docs, Security SIEM, TMDB Movies
- Output: live run view, saved reports, query-by-query before/after previews, shareable HTML export

## Quick start

### Docker Compose

```bash
docker compose up --build
```

This starts:

- Elasticsearch on `http://localhost:9200`
- FastAPI backend on `http://localhost:8000`
- Frontend on `http://localhost`
- Benchmark bootstrap job that loads the bundled indices

### Local dev

```bash
bash setup.sh
bash start.sh
```

Frontend: `http://localhost:5173`  
Backend: `http://localhost:8000`

## Product modes

### Search Mode

1. Connect to an Elasticsearch index or choose a benchmark preset.
2. Build or upload a test-search set.
3. Run experiments across field boosts, match strategy, MSM, fuzziness, hybrid weights, and fusion settings.
4. Keep only improvements based on real nDCG@10 evaluation.
5. Export a report with profile diff, experiment log, per-query before/after results, and reusable query DSL.

### Committee Mode

1. Upload a proposal, brief, or deck.
2. Generate or seed a buying committee.
3. Score sections across personas and rewrite iteratively.
4. Keep rewrites only when the consensus score improves without violating the do-no-harm floor.
5. Export a rewrite report and handoff payload.

## Built-in benchmarks

| Benchmark | Index | Docs | Eval queries |
|---|---|---:|---:|
| Product Store | `products-catalog` | 931 | 8 |
| Books Catalog | `books-catalog` | 2,000 | 12 |
| Workplace Docs | `workplace-docs` | 15 | 12 |
| Security SIEM | `security-siem` | 301 | 18 |
| TMDB Movies | `tmdb` | 8,516 | 12 |

Set them all up locally with:

```bash
python3 benchmarks/setup.py
```

Reset and rebuild:

```bash
python3 benchmarks/setup.py --reset
```

## Architecture

```text
backend/
  api/          REST + WebSocket routes
  committee/    committee-mode ingestion, evaluation, rewrite logic
  models/       Pydantic contracts
  services/     orchestration, Elasticsearch client, persistence, reports
frontend/
  components/   connect, run, report, committee UI
  screens/      landing, run, report, benchmarks
  store/        Zustand app state
benchmarks/
  */            datasets, eval sets, index bootstrap scripts
```

## Testing

```bash
python3 -m pytest backend/tests -q
python3 backend/scripts/smoke_app.py
cd frontend && npx tsc --noEmit && npm run build
```

## Deployment notes

- `docker-compose.yml` provides the easiest local or Replit-adjacent deployment path.
- `.github/workflows/ci.yml` runs backend tests plus frontend typecheck/build on push and pull request.
- `.replit` and `replit.nix` are included for Replit bootstrapping.

## Contributing

1. Keep benchmark and report behavior truthful to the underlying Elasticsearch run.
2. Prefer explainable UI over decorative motion.
3. Run the full verification commands before shipping.
