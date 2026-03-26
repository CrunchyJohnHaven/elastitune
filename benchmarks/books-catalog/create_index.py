from __future__ import annotations

import argparse
import os
from typing import Any, Dict

from elasticsearch import Elasticsearch


def build_mapping() -> Dict[str, Any]:
    return {
        "settings": {
            "index": {
                "number_of_replicas": 0,
                "number_of_shards": 1,
            }
        },
        "mappings": {
            "properties": {
                "title": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "authors": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "description": {"type": "text"},
                "categories": {"type": "keyword"},
                "average_rating": {"type": "float"},
                "ratings_count": {"type": "integer"},
                "review_count": {"type": "integer"},
                "published_year": {"type": "integer"},
                "url": {"type": "keyword"},
            }
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--es-url", default=os.getenv("ELASTICSEARCH_URL", "http://127.0.0.1:9200"))
    parser.add_argument("--api-key", default=os.getenv("ELASTICSEARCH_API_KEY"))
    parser.add_argument("--index-name", default="books-catalog")
    parser.add_argument("--recreate", action="store_true")
    args = parser.parse_args()

    client = Elasticsearch(
        args.es_url,
        api_key=args.api_key or None,
        verify_certs=False,
        ssl_show_warn=False,
    )

    if client.indices.exists(index=args.index_name):
        if not args.recreate:
            print(f"Index '{args.index_name}' already exists.")
            return
        client.indices.delete(index=args.index_name)
        print(f"Deleted existing index '{args.index_name}'.")

    client.indices.create(index=args.index_name, body=build_mapping())
    print(f"Created index '{args.index_name}'.")


if __name__ == "__main__":
    main()
