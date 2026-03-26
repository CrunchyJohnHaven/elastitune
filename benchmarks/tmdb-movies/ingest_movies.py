from __future__ import annotations

import argparse
import json
import os
import zipfile
from pathlib import Path
from typing import Iterable
from urllib.request import urlopen

from elasticsearch import Elasticsearch, helpers


ROOT = Path(__file__).resolve().parent
DEFAULT_DATASET = ROOT / "tmdb_dump_2020-12-29.json"
DEFAULT_ZIP = ROOT / "tmdb_es.json.zip"
REMOTE_ZIP = "https://raw.githubusercontent.com/o19s/es-tmdb/master/tmdb_es.json.zip"


def ensure_dataset(dataset_path: Path) -> Path:
    if dataset_path.exists():
        return dataset_path
    if not DEFAULT_ZIP.exists():
        with urlopen(REMOTE_ZIP) as response:
            DEFAULT_ZIP.write_bytes(response.read())
    if DEFAULT_ZIP.exists():
        with zipfile.ZipFile(DEFAULT_ZIP) as archive:
            for member in archive.namelist():
                if member.endswith(".json"):
                    archive.extract(member, ROOT)
                    extracted = ROOT / member
                    if extracted.exists():
                        return extracted
    raise SystemExit(
        f"TMDB dataset not found at {dataset_path}. Download {REMOTE_ZIP} or restore the bundled dataset."
    )


def load_movies(path: Path, limit: int | None) -> list[dict]:
    data = json.loads(path.read_text())
    if limit is not None:
        return data[:limit]
    return data


def _to_text_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item]
    if value:
        return [str(value)]
    return []


def build_actions(movies: list[dict], index_name: str) -> Iterable[dict]:
    for item in movies:
        movie_id = str(item.get("id") or item.get("movie_id") or item.get("tmdb_id"))
        if not movie_id:
            continue
        yield {
            "_index": index_name,
            "_id": movie_id,
            "_source": {
                "title": item.get("title") or item.get("original_title"),
                "overview": item.get("overview") or item.get("description") or "",
                "genres": _to_text_list(item.get("genres")),
                "keywords": ", ".join(_to_text_list(item.get("keywords"))),
                "cast": ", ".join(_to_text_list(item.get("cast"))[:8]),
                "director": item.get("director"),
                "release_date": item.get("release_date"),
                "vote_average": item.get("vote_average") or 0.0,
                "vote_count": item.get("vote_count") or 0,
                "popularity": item.get("popularity") or 0.0,
                "original_language": item.get("original_language"),
            },
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET))
    parser.add_argument("--es-url", default=os.getenv("ELASTICSEARCH_URL", "http://127.0.0.1:9200"))
    parser.add_argument("--api-key", default=os.getenv("ELASTICSEARCH_API_KEY"))
    parser.add_argument("--index-name", default="tmdb")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    dataset_path = ensure_dataset(Path(args.dataset))
    movies = load_movies(dataset_path, args.limit)
    client = Elasticsearch(args.es_url, api_key=args.api_key or None, verify_certs=False, ssl_show_warn=False)
    success, failed = helpers.bulk(client, build_actions(movies, args.index_name))
    print(f"Ingested {success} movies into '{args.index_name}'. Failed: {failed}")


if __name__ == "__main__":
    main()
