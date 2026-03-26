from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Iterable

from elasticsearch import Elasticsearch, helpers


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = (
    ROOT
    / ".benchmarks"
    / "elastic-product-store"
    / "elasticsearch-labs"
    / "supporting-blog-content"
    / "hybrid-search-for-an-e-commerce-product-catalogue"
    / "product-store-search"
    / "files"
    / "dataset"
    / "products.json"
)


def load_products(path: Path, limit: int | None) -> list[dict]:
    with path.open() as handle:
        data = json.load(handle)
    if limit is not None:
        return data[:limit]
    return data


def build_actions(products: list[dict], index_name: str, hybrid: bool) -> Iterable[dict]:
    encoder = None
    if hybrid:
        from sentence_transformers import SentenceTransformer

        encoder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    for item in products:
        source = {
            "id": item["id"],
            "brand": item.get("brand"),
            "name": item.get("name"),
            "price": item.get("price"),
            "price_sign": item.get("price_sign"),
            "currency": item.get("currency"),
            "image_link": item.get("image_link"),
            "description": item.get("description"),
            "rating": item.get("rating"),
            "category": item.get("category"),
            "product_type": item.get("product_type"),
            "tag_list": item.get("tag_list", []),
        }
        if hybrid and encoder is not None:
            source["description_embeddings"] = encoder.encode(item.get("description", "")).tolist()

        yield {
            "_index": index_name,
            "_id": item["id"],
            "_source": source,
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--es-url", default=os.getenv("ELASTICSEARCH_URL", "http://127.0.0.1:9200"))
    parser.add_argument("--api-key", default=os.getenv("ELASTICSEARCH_API_KEY"))
    parser.add_argument("--index-name", default="products-catalog")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--hybrid", action="store_true")
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        raise SystemExit(
            f"Dataset not found at {dataset_path}. Run setup_target.py first or pass --dataset explicitly."
        )

    products = load_products(dataset_path, args.limit)
    client = Elasticsearch(args.es_url, api_key=args.api_key or None, verify_certs=False, ssl_show_warn=False)
    success, failed = helpers.bulk(client, build_actions(products, args.index_name, args.hybrid))
    print(f"Ingested {success} documents into '{args.index_name}'. Failed: {failed}")


if __name__ == "__main__":
    main()
