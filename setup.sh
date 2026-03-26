#!/bin/bash
set -e
echo "=== ElastiTune Setup ==="

# Backend deps
echo "[1/3] Installing Python dependencies..."
pip install -q -r backend/requirements.txt

# Frontend deps + build
echo "[2/3] Installing frontend dependencies..."
cd frontend && npm install --silent

echo "[3/3] Building frontend..."
npm run build
cd ..

echo ""
echo "Setup complete. Run with: bash run.sh"
