#!/bin/bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"

# Auto-setup if needed
if [ ! -d "$ROOT/frontend/node_modules" ]; then
  echo "First run detected — installing dependencies..."
  pip install -q -r "$ROOT/backend/requirements.txt"
  cd "$ROOT/frontend" && npm install --silent && cd "$ROOT"
fi

# Auto-build frontend if dist doesn't exist
if [ ! -f "$ROOT/frontend/dist/index.html" ]; then
  echo "Building frontend..."
  cd "$ROOT/frontend" && npm run build && cd "$ROOT"
fi

echo ""
echo "==================================="
echo "  ElastiTune → http://localhost:8000"
echo "==================================="
echo ""

# Single-process mode: FastAPI serves frontend from dist/
cd "$ROOT"
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
