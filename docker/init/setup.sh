#!/bin/bash
set -euo pipefail

echo "Waiting for Elasticsearch..."
until curl -sf "http://elasticsearch:9200" >/dev/null; do
  sleep 3
done

echo "Bootstrapping ElastiTune benchmark indices..."
cd /app
python3 benchmarks/setup.py
echo "Benchmark setup complete."
