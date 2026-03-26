from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from .api.routes_connect import _build_heuristic_eval_set
from .api.routes_runs import _build_personas
from .models.contracts import ConnectionSummary, EvalCase, LlmConfig, SearchProfile
from .models.runtime import ConnectionContext, RunContext
from .services.es_service import ESService
from .services.run_manager import RunManager


def _load_eval_set(path: str) -> list[EvalCase]:
    with Path(path).open() as handle:
        return [EvalCase.model_validate(item) for item in json.load(handle)]


async def _build_connection(
    es_url: str,
    api_key: str | None,
    index_name: str,
    eval_set_path: str | None,
) -> ConnectionContext:
    es = ESService(es_url=es_url, api_key=api_key)
    try:
        cluster_info = await es.get_cluster_info()
        analysis = await es.analyze_index(index=index_name)
        eval_set = _load_eval_set(eval_set_path) if eval_set_path else _build_heuristic_eval_set(
            analysis["sample_docs"], analysis["text_fields"], analysis["domain"]
        )
        profile = SearchProfile(
            **await es.build_baseline_profile(
                text_fields=analysis["text_fields"],
                vector_field=analysis["vector_field"],
            )
        )
        summary = ConnectionSummary(
            clusterName=cluster_info.get("cluster_name", "cli"),
            clusterVersion=cluster_info.get("version", {}).get("number"),
            indexName=index_name,
            docCount=await es.count_docs(index_name),
            detectedDomain=analysis["domain"],
            primaryTextFields=analysis["text_fields"],
            vectorField=analysis["vector_field"],
            vectorDims=analysis["vector_dims"],
            sampleDocs=[],
            baselineEvalCount=len(eval_set),
            baselineReady=bool(eval_set),
        )
        return ConnectionContext(
            connection_id=f"cli-{index_name}",
            mode="live",
            summary=summary,
            eval_set=eval_set,
            baseline_profile=profile,
            llm_config=LlmConfig(provider="disabled"),
            es_url=es_url,
            api_key=api_key,
            index_name=index_name,
            text_fields=analysis["text_fields"],
            sample_docs=analysis["sample_docs"],
        )
    finally:
        await es.close()


async def _run_single(args: argparse.Namespace) -> dict:
    connection = await _build_connection(args.es_url, args.api_key, args.index, args.eval_set)
    personas = await _build_personas(
        persona_count=args.persona_count,
        mode="live",
        domain=connection.summary.detectedDomain,
        sample_docs=connection.sample_docs,
        text_fields=connection.text_fields,
        llm_config=None,
    )
    ctx = RunContext(
        run_id=f"cli-run-{args.index}",
        connection=connection,
        personas=personas,
        max_experiments=args.max_experiments,
        duration_minutes=args.duration_minutes,
        auto_stop_on_plateau=True,
    )
    manager = RunManager()
    await manager.create_run(ctx.run_id, ctx)
    await manager.start_run_tasks(ctx.run_id)
    await asyncio.gather(*ctx.tasks)
    assert ctx.report is not None
    return json.loads(ctx.report.model_dump_json())


async def _probe(args: argparse.Namespace) -> dict:
    connection = await _build_connection(args.es_url, args.api_key, args.index, args.eval_set)
    ctx = RunContext(
        run_id=f"probe-{args.index}",
        connection=connection,
        personas=[],
        max_experiments=0,
        duration_minutes=1,
        auto_stop_on_plateau=True,
    )
    manager = RunManager()
    baseline, misses, per_query = await manager.evaluate_detailed(ctx, connection.baseline_profile)
    return {
        "index": args.index,
        "baseline_score": baseline,
        "missed_queries": misses,
        "per_query_scores": per_query,
    }


async def _optimize_many(args: argparse.Namespace) -> dict:
    results = []
    for index in args.indices:
        run_args = argparse.Namespace(
            es_url=args.es_url,
            api_key=args.api_key,
            index=index,
            eval_set=args.eval_set,
            max_experiments=args.max_experiments,
            duration_minutes=args.duration_minutes,
            persona_count=args.persona_count,
        )
        results.append(await _run_single(run_args))
    return {"runs": results}


def main() -> None:
    parser = argparse.ArgumentParser(prog="elastitune")
    sub = parser.add_subparsers(dest="command", required=True)

    optimize = sub.add_parser("optimize")
    optimize.add_argument("--es-url", default="http://127.0.0.1:9200")
    optimize.add_argument("--api-key")
    optimize.add_argument("--index", required=True)
    optimize.add_argument("--eval-set")
    optimize.add_argument("--max-experiments", type=int, default=30)
    optimize.add_argument("--duration-minutes", type=int, default=5)
    optimize.add_argument("--persona-count", type=int, default=24)

    probe = sub.add_parser("probe")
    probe.add_argument("--es-url", default="http://127.0.0.1:9200")
    probe.add_argument("--api-key")
    probe.add_argument("--index", required=True)
    probe.add_argument("--eval-set")

    optimize_many = sub.add_parser("optimize-many")
    optimize_many.add_argument("--es-url", default="http://127.0.0.1:9200")
    optimize_many.add_argument("--api-key")
    optimize_many.add_argument("--indices", nargs="+", required=True)
    optimize_many.add_argument("--eval-set")
    optimize_many.add_argument("--max-experiments", type=int, default=20)
    optimize_many.add_argument("--duration-minutes", type=int, default=3)
    optimize_many.add_argument("--persona-count", type=int, default=16)

    args = parser.parse_args()
    if args.command == "optimize":
        result = asyncio.run(_run_single(args))
    elif args.command == "probe":
        result = asyncio.run(_probe(args))
    else:
        result = asyncio.run(_optimize_many(args))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
