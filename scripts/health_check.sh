#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"
python3 -m pytest backend/tests -q
python3 backend/scripts/smoke_app.py
python3 -m compileall backend

cd "$ROOT_DIR/frontend"
npm run build
