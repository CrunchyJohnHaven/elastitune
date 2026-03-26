from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.elastic_sink_service import ElasticSinkService  # noqa: E402
from backend.services.persistence_service import PersistenceService  # noqa: E402


async def main_async() -> int:
    parser = argparse.ArgumentParser(description="Push persisted ElastiTune runs into Elasticsearch.")
    parser.add_argument("--run-id", required=True, help="Run identifier to push.")
    parser.add_argument(
        "--mode",
        choices=("search", "committee"),
        required=True,
        help="Persisted run mode.",
    )
    args = parser.parse_args()

    sink = ElasticSinkService.from_settings()
    if sink is None:
        raise SystemExit(
            "Elastic sink is disabled. Set ENABLE_ELASTIC_SINK=true and ELASTIC_SINK_URL."
        )

    persistence = PersistenceService()
    await persistence.init()
    try:
        if args.mode == "search":
            report = await persistence.load_report(args.run_id)
            if report is None:
                raise SystemExit(f"Search report '{args.run_id}' not found in SQLite.")
            await sink.index_search_run(report)
        else:
            report = await persistence.load_committee_report(args.run_id)
            export_payload = await persistence.load_committee_export(args.run_id)
            if report is None or export_payload is None:
                raise SystemExit(f"Committee artifacts for '{args.run_id}' not found in SQLite.")
            await sink.index_committee_run(report, export_payload)
    finally:
        await sink.close()
        await persistence.close()
    print(f"Indexed {args.mode} run {args.run_id} into Elasticsearch.")
    return 0


def main() -> int:
    return asyncio.run(main_async())


if __name__ == "__main__":
    raise SystemExit(main())
