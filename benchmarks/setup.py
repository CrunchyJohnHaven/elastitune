#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from elasticsearch import Elasticsearch


ROOT = Path(__file__).resolve().parents[1]
ES_URL = os.getenv("ELASTICSEARCH_URL", "http://127.0.0.1:9200")
API_KEY = os.getenv("ELASTICSEARCH_API_KEY")

BENCHMARKS = [
    {
        "index": "products-catalog",
        "label": "Product Store",
        "expected_docs": 931,
        "scripts": [
            ["python3", "benchmarks/elastic-product-store/create_index.py"],
            ["python3", "benchmarks/elastic-product-store/ingest_products.py"],
        ],
    },
    {
        "index": "books-catalog",
        "label": "Books Catalog",
        "expected_docs": 2000,
        "scripts": [
            ["python3", "benchmarks/books-catalog/create_index.py"],
            ["python3", "benchmarks/books-catalog/ingest_books.py"],
        ],
    },
    {
        "index": "workplace-docs",
        "label": "Workplace Docs",
        "expected_docs": 15,
        "scripts": [
            ["python3", "benchmarks/workplace-docs/create_index.py"],
            ["python3", "benchmarks/workplace-docs/ingest_docs.py"],
        ],
    },
    {
        "index": "security-siem",
        "label": "Security SIEM",
        "expected_docs": 301,
        "scripts": [
            ["python3", "benchmarks/security-siem/setup.py"],
        ],
    },
    {
        "index": "tmdb",
        "label": "TMDB Movies",
        "expected_docs": 8516,
        "scripts": [
            ["python3", "benchmarks/tmdb-movies/create_index.py"],
            ["python3", "benchmarks/tmdb-movies/ingest_movies.py"],
        ],
    },
]


def client() -> Elasticsearch:
    return Elasticsearch(ES_URL, api_key=API_KEY or None, verify_certs=False, ssl_show_warn=False)


def count_docs(es: Elasticsearch, index: str) -> int:
    try:
        if not es.indices.exists(index=index):
            return 0
        return int(es.count(index=index)["count"])
    except Exception:
        return 0


def run_script(command: list[str]) -> None:
    env = os.environ.copy()
    env.setdefault("ELASTICSEARCH_URL", ES_URL)
    if API_KEY:
        env.setdefault("ELASTICSEARCH_API_KEY", API_KEY)
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Set up all local ElastiTune benchmark indices.")
    parser.add_argument("--reset", action="store_true", help="Delete and recreate matching indices before ingest.")
    parser.add_argument("--only", action="append", dest="only", help="Benchmark index name to set up. May be provided multiple times.")
    args = parser.parse_args()

    es = client()
    if not es.ping():
        raise SystemExit(f"Cannot reach Elasticsearch at {ES_URL}. Start Elasticsearch first.")

    selected = {name for name in (args.only or [])}
    benchmarks = [item for item in BENCHMARKS if not selected or item["index"] in selected]

    rows: list[tuple[str, int, str]] = []
    for item in benchmarks:
        index = item["index"]
        before = count_docs(es, index)
        status = "ready"

        if args.reset and es.indices.exists(index=index):
            es.indices.delete(index=index)
            before = 0
            status = "reset"

        if before < item["expected_docs"]:
            for command in item["scripts"]:
                run_script(command)
            after = count_docs(es, index)
            status = "created" if after >= item["expected_docs"] else "partial"
        else:
            after = before

        rows.append((index, after, status))

    print("\nElastiTune benchmark setup")
    print(f"{'index':<20} {'docs':>8}  status")
    print(f"{'-'*20} {'-'*8}  {'-'*12}")
    for index, docs, status in rows:
        print(f"{index:<20} {docs:>8}  {status}")


if __name__ == "__main__":
    main()
