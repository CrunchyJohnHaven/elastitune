# Local Development Workflow

This project is intentionally simple to start locally:

## 1. Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
python3 -m uvicorn backend.main:app --reload --port 8000
```

The backend serves the API on `http://localhost:8000` and the WebSocket transport on `/ws/runs/{runId}`.

## 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite runs on `http://localhost:5173` and proxies `/api` and `/ws` back to the backend.

## 3. Tests

```bash
python3 -m pytest backend/tests/ -v
python3 backend/scripts/smoke_app.py
cd frontend && npx tsc --noEmit && npm run build
```

## 4. Reports

- Search reports are available at `/report/:runId`.
- Committee reports are available at `/committee/report/:runId`.
- Export buttons in the UI generate JSON or HTML artifacts from the in-memory report objects.

## 5. Troubleshooting

- Port conflict on `8000`: stop any existing FastAPI/Uvicorn process or change `PORT` in `.env`.
- Port conflict on `5173`: stop the existing Vite dev server or change the frontend port in `frontend/vite.config.ts`.
- Elasticsearch unavailable: make sure the sample benchmark stack or your own Elasticsearch instance is running before connecting in live mode.
- WebSocket disconnects: refresh the run page after verifying the backend is still healthy.
