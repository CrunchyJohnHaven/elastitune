# ElastiTune

**Autonomous search quality optimizer with live mission-control visualization.**

ElastiTune connects to your Elasticsearch cluster, automatically discovers what's wrong with your search results, tests hundreds of ranking changes, and hands you back a tuned configuration with a measurable before/after improvement — all while you watch.

It also ships with a **Simulated Buying Committee** mode: upload a pitch document, and AI-generated stakeholder personas will score, debate, and rewrite it to maximize consensus.

---

## One-Command Start

```bash
bash run.sh
```

That's it. The script auto-installs dependencies and builds the frontend on first run.

Open **http://localhost:8000** and click **Launch Demo** to see it work immediately — no Elasticsearch cluster required.

---

## What It Does

### Search Mode

1. **Connect** — paste your Elasticsearch URL, API key, and index name
2. **Auto-detect** — ElastiTune reads your mappings, samples documents, detects text fields, vector fields, and data domain
3. **Generate test queries** — builds an evaluation set from your data (or upload your own)
4. **Optimize** — runs experiments: mutating search profile knobs (boosts, match types, fuzziness, vector weights, fusion methods), measuring nDCG@10 after each change, keeping improvements and reverting regressions
5. **Visualize** — 24-36 simulated user personas fire queries in a live canvas, beams light up on searches, scores climb in real time
6. **Report** — exports a before/after profile diff, experiment log, and recommended configuration you can copy straight into your search template

### Committee Mode

1. **Upload** a proposal, pitch deck, or brief (PDF, PPTX, DOCX, TXT)
2. **Generate** a buying committee — AI creates 4-6 stakeholder personas with authority weights, concerns, and decision criteria
3. **Rewrite** — the optimizer rewrites document sections to maximize weighted consensus score across the committee, testing parameter changes like CTA urgency, proof point density, objection preemption, and technical depth
4. **"Do No Harm"** — a rewrite is only kept if no single persona's score drops by more than 5%
5. **Export** — download the optimized document with section-by-section before/after comparison

---

## Quick Start Options

### Option A: Demo Mode (Zero Setup)

```bash
bash run.sh
# Open http://localhost:8000
# Click "Launch Demo"
```

Plays back a realistic 36-experiment optimization run with live persona animation. Takes ~72 seconds.

### Option B: Local Benchmark

Follow the [benchmark pack instructions](benchmarks/elastic-product-store/README.md) to spin up a local Elasticsearch with 931 product documents and a fixed evaluation set. Then connect ElastiTune to `http://127.0.0.1:9200` with index `products-catalog`.

### Option C: Your Own Cluster

Enter your Elasticsearch connection details on the connect screen. ElastiTune will auto-detect everything and generate test queries from your data.

### Option D: Committee Mode

Navigate to **http://localhost:8000/committee**, upload a document, and watch the buying room react.

---

## Running on Replit

This repo includes a `.replit` configuration. Import from GitHub and it should auto-detect the setup:

1. **Import** `git@github.com:CrunchyJohnHaven/elastitune.git`
2. Click **Run** — the `.replit` file triggers `bash run.sh` which handles everything
3. Replit will install Python/Node dependencies, build the frontend, and start the server
4. Access via the Replit webview URL

If you need to rebuild the frontend manually:
```bash
cd frontend && npm run build
```

---

## Architecture

```
elastitune/
├── backend/             FastAPI (Python 3.11+)
│   ├── api/             REST routes + WebSocket streaming
│   ├── committee/       Document parser, evaluator, rewrite engine
│   ├── engine/          nDCG evaluator, optimizer, persona generator, compression
│   ├── models/          Pydantic v2 contracts
│   ├── services/        RunManager orchestration, ES client, LLM client
│   └── data/demo/       Pre-recorded demo data
├── frontend/            React 18 + TypeScript + Vite
│   └── src/
│       ├── screens/     Connect, Run, Report (search + committee)
│       ├── components/  FishTank canvas, committee space, layout shells
│       ├── store/       Zustand global state
│       └── lib/         API client, WebSocket client, formatters
├── benchmarks/          Eval sets and benchmark tooling
├── run.sh               Single-command start (auto-installs + builds)
├── setup.sh             Explicit setup script
└── start.sh             Dev mode (separate Vite + FastAPI processes)
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, Pydantic v2, AsyncElasticsearch, NumPy, SciPy |
| Frontend | React 18, TypeScript 5.6, Vite, Zustand, Recharts, Framer Motion |
| Visualization | HTML5 Canvas (custom), SVG coalition lines |
| Streaming | WebSocket with exponential backoff reconnection |
| State | In-memory + SQLite for run persistence |

---

## What Gets Tuned

### Search Profile Knobs

These are **query-time parameters** — safe, reversible, no reindexing required:

| Parameter | Range | What It Does |
|-----------|-------|-------------|
| Field boosts | 0.5–3.0 per field | Weight which fields matter most |
| `multi_match` type | best_fields, most_fields, cross_fields, phrase | How terms are matched across fields |
| `minimum_should_match` | 50%–90% | How many query terms must match |
| `tie_breaker` | 0.0–0.5 | How much non-best fields contribute |
| Phrase boost | 0.0–3.0 | Extra weight for exact phrase matches |
| Fuzziness | 0, AUTO | Typo tolerance |
| Vector weight | 0.2–0.6 | Balance between lexical and semantic search |
| Fusion method | weighted_sum, RRF | How to combine lexical + vector results |
| `knnK` | 10–50 | How many vector neighbors to retrieve |

### Committee Rewrite Parameters

| Parameter | Values | What It Controls |
|-----------|--------|-----------------|
| stat_framing | conservative, moderate, aggressive | How boldly statistics are presented |
| proof_point_density | low, medium, high | Density of supporting evidence |
| cta_urgency | soft, firm, direct | Call-to-action assertiveness |
| objection_preemption | none, light, heavy | Pre-emptive objection handling |
| technical_depth | executive, practitioner, mixed | Audience technical level |
| risk_narrative | opportunity, threat, balanced | Risk framing angle |
| social_proof_type | internal, external, analyst | Type of social proof citations |
| specificity | general, vertical_tailored, hyper_specific | How targeted the language is |

---

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and fill in what you need:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `disabled` | `openai_compatible`, `openai`, `anthropic`, or `disabled` |
| `LLM_BASE_URL` | — | e.g. `https://api.openai.com/v1` |
| `LLM_MODEL` | `gpt-4o-mini` | Model name |
| `LLM_API_KEY` | — | API key for LLM provider |
| `COST_PER_GB_MONTH` | `0.095` | $/GB/month for compression savings estimate |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8000` | Server port |

**Without an LLM**, ElastiTune still works — it uses heuristic query generation, persona generation, and experiment selection. The LLM makes all of these smarter but isn't required.

---

## Development

### Two-Server Mode (Hot Reload)

```bash
# Terminal 1: Backend with auto-reload
python3 -m uvicorn backend.main:app --reload --port 8000

# Terminal 2: Frontend with HMR
cd frontend && npm run dev
```

Frontend dev server runs on `:5173` and proxies `/api` and `/ws` to `:8000`.

### Single-Server Mode (Production)

```bash
cd frontend && npm run build && cd ..
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

FastAPI serves the built frontend from `frontend/dist/` at `/`.

### Smoke Test

```bash
python3 backend/scripts/smoke_app.py
```

Runs a lightweight end-to-end pass: health check, demo connection, search run, committee run with document upload, report generation.

---

## API

Interactive docs at **http://localhost:8000/docs** (Swagger UI).

### Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/connect` | Analyze an Elasticsearch index |
| `POST` | `/api/runs` | Start an optimization run |
| `GET` | `/api/runs/{id}` | Get current run snapshot |
| `POST` | `/api/runs/{id}/stop` | Stop a running optimization |
| `GET` | `/api/runs/{id}/report` | Get the final report |
| `WS` | `/ws/runs/{id}` | Stream live events |
| `POST` | `/api/committee/connect` | Upload and parse a document |
| `POST` | `/api/committee/runs` | Start a committee evaluation |
| `GET` | `/api/committee/runs/{id}/export` | Download optimized document |

### WebSocket Events

| Event | Payload | Frequency |
|-------|---------|-----------|
| `snapshot` | Full run state | On connect |
| `experiment.completed` | Experiment result + decision | Per experiment |
| `persona.batch` | Updated persona states | Every 1.5s |
| `metrics.tick` | Score timeline point | Every 2s |
| `compression.updated` | Vector compression analysis | Once |
| `run.stage` | Stage transition | On change |
| `report.ready` | Final report payload | On completion |

---

## Project Status

This is a demo and internal tooling project — functional end-to-end but with known limitations:

- **In-memory state** — runs are persisted to SQLite but the database resets on server restart in some configurations
- **Persona simulation** — personas simulate search behavior based on optimization score, not real user queries
- **LLM-dependent quality** — committee rewrites and smart experiment selection require an LLM; heuristic fallbacks are functional but less intelligent
- **Single-user** — no authentication or multi-tenancy

---

## License

Internal use. Not licensed for redistribution.
