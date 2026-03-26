#!/bin/bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

# Auto-setup: install Python deps if not already present
if ! python3 -c "import fastapi" 2>/dev/null; then
  echo "[ElastiTune] Installing Python dependencies..."
  pip install -q -r "$ROOT/backend/requirements.txt" || {
    echo "[ElastiTune] ERROR: Failed to install Python dependencies." >&2
    exit 1
  }
fi

# Auto-setup: install Node deps if node_modules is missing
if [ ! -d "$ROOT/frontend/node_modules" ]; then
  echo "[ElastiTune] Installing frontend Node dependencies..."
  cd "$ROOT/frontend" && npm install --silent || {
    echo "[ElastiTune] ERROR: npm install failed. Make sure Node.js is installed." >&2
    exit 1
  }
  cd "$ROOT"
fi

# Auto-build frontend if dist doesn't exist
if [ ! -f "$ROOT/frontend/dist/index.html" ]; then
  echo "[ElastiTune] Building frontend (dist not found)..."
  cd "$ROOT/frontend" && npm run build || {
    echo "[ElastiTune] ERROR: Frontend build failed. Check the output above." >&2
    exit 1
  }
  cd "$ROOT"
fi

# Validate that the Elasticsearch URL env var is set
if [ -z "$ES_URL" ]; then
  echo "[ElastiTune] WARNING: ES_URL is not set. Defaulting to http://127.0.0.1:9200"
  export ES_URL="http://127.0.0.1:9200"
fi

echo ""
echo "==================================="
echo "  ElastiTune is starting up"
echo "  URL : http://0.0.0.0:8000"
echo "  ES  : $ES_URL"
echo "==================================="
echo ""

# Single-process mode: FastAPI serves the built frontend from dist/
cd "$ROOT"
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
