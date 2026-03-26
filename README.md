# ElastiTune

Autonomous Elasticsearch search-profile optimizer with a live mission-control dashboard.

![screenshot placeholder](docs/screenshot.png)

## What it does

- Connects to any Elasticsearch index (or a built-in benchmark), then runs controlled experiments across field boosts, match strategy, MSM, fuzziness, hybrid weights, and fusion settings.
- Keeps only changes that improve nDCG@10, producing a measurable before/after lift with full experiment logs.
- Streams every experiment result in real time over a single WebSocket — no polling, no database.
- Includes Committee Mode: simulates a buying-committee of personas to score and iteratively rewrite proposal documents.

## Quick start

**Prerequisites:** Python 3.11+, Node 18+, a running Elasticsearch 8.x instance (or use Docker Compose below).

```bash
# 1. Install backend dependencies
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt

# 2. Configure environment
cp .env.example .env          # edit as needed

# 3. Start backend (port 8000)
python3 -m uvicorn backend.main:app --reload --port 8000

# 4. Start frontend (port 5173) — in a second terminal
cd frontend
npm install
npm run dev
```

Or with Docker Compose (starts Elasticsearch, backend, and frontend together):

```bash
docker compose up --build
```

## Architecture

- **Backend:** FastAPI (Python 3.11), Pydantic v2, AsyncElasticsearch, numpy/scipy, orjson. Runs on port 8000.
- **Frontend:** React 18, TypeScript, Vite, Zustand, Tailwind CSS, HTML5 Canvas, recharts. Dev server on port 5173.
- **Real-time:** One WebSocket per run, text frames via orjson. No database, no Redis, no task queue — all state is in-memory.
- **Production:** `npm run build` outputs a static bundle that FastAPI serves directly from `frontend/dist/`.

## Running tests

```bash
# Backend unit tests
python3 -m pytest backend/tests/ -v

# Backend smoke test (requires running backend)
python3 backend/scripts/smoke_app.py

# Frontend type check + build verification
cd frontend && npx tsc --noEmit && npm run build
```

## Benchmarks

Five benchmark datasets are bundled. Load them all into a local Elasticsearch instance:

```bash
python3 benchmarks/setup.py          # initial load
python3 benchmarks/setup.py --reset  # wipe and reload
```

| Benchmark | Index | Docs | Eval queries |
|---|---|---:|---:|
| Product Store | `products-catalog` | 931 | 8 |
| Books Catalog | `books-catalog` | 2,000 | 12 |
| Workplace Docs | `workplace-docs` | 15 | 16 |
| Security SIEM | `security-siem` | 301 | 18 |
| TMDB Movies | `tmdb` | 8,516 | 12 |

## Deploy to Replit

`replit.nix` and `.replit` are included. Import the repo into Replit, set the environment variables from `.env.example` in the Replit Secrets panel, then run:

```bash
bash setup.sh && bash start.sh
```

The backend will bind to `0.0.0.0` on the port Replit assigns; update `CORS_ORIGINS` in Secrets to match your Replit dev URL.

## Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, Uvicorn, Pydantic v2, AsyncElasticsearch |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Zustand |
| Visualization | HTML5 Canvas, recharts, framer-motion |
| Evaluation | nDCG@10 computed in-process with numpy/scipy |
| Packaging | Docker Compose, Replit |
