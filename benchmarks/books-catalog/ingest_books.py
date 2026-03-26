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
    / "supporting-blog-content"
    / "navigating-an-elastic-vector-database"
    / "data"
    / "books.json"
)
REMOTE_DATASET = (
    "https://raw.githubusercontent.com/elastic/elasticsearch-labs/main/"
    "supporting-blog-content/navigating-an-elastic-vector-database/data/books.json"
)


def ensure_dataset(path: Path) -> Path:
    if path.exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(REMOTE_DATASET) as response:
        path.write_bytes(response.read())
    return path


def load_books(path: Path, limit: int | None) -> list[dict]:
    data = json.loads(path.read_text())
    if limit is not None:
        return data[:limit]
    return data


def build_actions(books: list[dict], index_name: str) -> Iterable[dict]:
    for idx, item in enumerate(books, start=1):
        yield {
            "_index": index_name,
            "_id": str(idx),
            "_source": {
                "title": item.get("book_title"),
                "authors": item.get("author_name"),
                "description": item.get("book_description"),
                "categories": item.get("genres", []),
                "average_rating": item.get("rating_score"),
                "ratings_count": item.get("rating_votes"),
                "review_count": item.get("review_number"),
                "published_year": item.get("year_published"),
                "url": item.get("url"),
            },
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--es-url", default=os.getenv("ELASTICSEARCH_URL", "http://127.0.0.1:9200"))
    parser.add_argument("--api-key", default=os.getenv("ELASTICSEARCH_API_KEY"))
    parser.add_argument("--index-name", default="books-catalog")
    parser.add_argument("--limit", type=int, default=2000)
    args = parser.parse_args()

    dataset_path = ensure_dataset(Path(args.dataset))

    books = load_books(dataset_path, args.limit)
    client = Elasticsearch(
        args.es_url,
        api_key=args.api_key or None,
        verify_certs=False,
        ssl_show_warn=False,
    )
    success, failed = helpers.bulk(client, build_actions(books, args.index_name))
    print(f"Ingested {success} books into '{args.index_name}'. Failed: {failed}")


if __name__ == "__main__":
    main()
