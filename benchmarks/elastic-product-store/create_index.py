from __future__ import annotations

import argparse
import os
from typing import Any, Dict

from elasticsearch import Elasticsearch


def build_mapping(hybrid: bool) -> Dict[str, Any]:
    properties: Dict[str, Any] = {
        "id": {"type": "keyword"},
        "brand": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
        "name": {"type": "text"},
        "price": {"type": "float"},
        "price_sign": {"type": "keyword"},
        "currency": {"type": "keyword"},
        "image_link": {"type": "keyword"},
        "description": {"type": "text"},
        "rating": {"type": "keyword"},
        "category": {"type": "keyword"},
        "product_type": {"type": "keyword"},
        "tag_list": {"type": "keyword"},
    }

    if hybrid:
        properties["description_embeddings"] = {"type": "dense_vector", "dims": 384}

    return {
        "settings": {
            "index": {
                "number_of_replicas": 0,
                "number_of_shards": 1,
            }
        },
        "mappings": {"properties": properties},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--es-url", default=os.getenv("ELASTICSEARCH_URL", "http://127.0.0.1:9200"))
    parser.add_argument("--api-key", default=os.getenv("ELASTICSEARCH_API_KEY"))
    parser.add_argument("--index-name", default="products-catalog")
    parser.add_argument("--hybrid", action="store_true")
    args = parser.parse_args()

    client = Elasticsearch(args.es_url, api_key=args.api_key or None, verify_certs=False, ssl_show_warn=False)
    mapping = build_mapping(args.hybrid)

    if client.indices.exists(index=args.index_name):
        print(f"Index '{args.index_name}' already exists.")
        return

    client.indices.create(index=args.index_name, body=mapping)
    print(f"Created index '{args.index_name}' ({'hybrid' if args.hybrid else 'lexical'} mode).")


if __name__ == "__main__":
    main()
