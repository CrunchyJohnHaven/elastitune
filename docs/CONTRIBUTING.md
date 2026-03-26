# Contributing

This repository is designed to be easy to run locally, demo in a browser, and inspect from the terminal.

## Local Setup

1. Create a Python virtual environment.
2. Install backend requirements.
3. Start Elasticsearch.
4. Start the backend on port `8000`.
5. Start the frontend on port `5173`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python3 -m uvicorn backend.main:app --reload --port 8000
```

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

If you prefer Docker:

```bash
docker compose up --build
```

## Tests

Run the backend tests first because they cover the core run orchestration and persistence logic.

```bash
python3 -m pytest backend/tests -q
```

Run a smoke test against a running backend:

```bash
python3 backend/scripts/smoke_app.py
```

Type-check and build the frontend:

```bash
cd frontend
npx tsc --noEmit
npm run build
```

## Reports

Search mode reports are available at `/api/runs/{runId}/report`.
Committee mode reports are available at `/api/committee/runs/{runId}/report`.

For manual verification, open the report screen after a run completes and confirm:

1. The report data loads.
2. The summary metrics match the live run.
3. Export actions work without re-running the run.

## Troubleshooting

- Port `8000` already in use: stop the existing Python process or change the backend port in your local command.
- Port `5173` already in use: stop the existing Vite process or launch the frontend on another port.
- Elasticsearch connection errors: confirm `ELASTICSEARCH_URL` points to a reachable cluster and that any required API key is set.
- Empty benchmark list: run `python3 benchmarks/setup.py` to create the bundled indices.
- Frontend build errors: run `npx tsc --noEmit` first so TypeScript errors are easier to read.

## Good Pull Requests

- Keep changes focused.
- Update docs when behavior changes.
- Add or update tests for new behavior.
- Preserve both search mode and committee mode unless the change is explicitly scoped to one of them.
