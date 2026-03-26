from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Iterable
from urllib.request import urlopen

from elasticsearch import Elasticsearch, helpers


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = (
    ROOT
    / ".benchmarks"
    / "elastic-product-store"
    / "elasticsearch-labs"
    / "datasets"
    / "workplace-documents.json"
)
REMOTE_DATASET = (
    "https://raw.githubusercontent.com/elastic/elasticsearch-labs/main/"
    "datasets/workplace-documents.json"
)


def ensure_dataset(path: Path) -> Path:
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(REMOTE_DATASET) as response:
        path.write_bytes(response.read())
    return path


def load_documents(path: Path) -> list[dict]:
    return json.loads(path.read_text())


def build_actions(documents: list[dict], index_name: str) -> Iterable[dict]:
    for idx, item in enumerate(documents, start=1):
        yield {
            "_index": index_name,
            "_id": str(idx),
            "_source": {
                "name": item.get("name"),
                "summary": item.get("summary"),
                "content": item.get("content"),
                "url": item.get("url"),
                "category": item.get("category"),
                "created_on": item.get("created_on"),
                "updated_at": item.get("updated_at"),
                "role_permissions": item.get("rolePermissions", []),
            },
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--es-url", default=os.getenv("ELASTICSEARCH_URL", "http://127.0.0.1:9200"))
    parser.add_argument("--api-key", default=os.getenv("ELASTICSEARCH_API_KEY"))
    parser.add_argument("--index-name", default="workplace-docs")
    args = parser.parse_args()

    dataset_path = ensure_dataset(Path(args.dataset))

    documents = load_documents(dataset_path)
    client = Elasticsearch(
        args.es_url,
        api_key=args.api_key or None,
        verify_certs=False,
        ssl_show_warn=False,
    )
    success, failed = helpers.bulk(client, build_actions(documents, args.index_name))
    print(f"Ingested {success} workplace documents into '{args.index_name}'. Failed: {failed}")


if __name__ == "__main__":
    main()
