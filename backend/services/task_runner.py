from __future__ import annotations

import asyncio
import logging
import math
import random
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ..config import settings
from ..engine.optimizer_search_space import (
    build_hypothesis_text,
    generate_security_field_mutations,
)
from ..models.contracts import ExperimentRecord, SearchProfile, SearchProfileChange

if TYPE_CHECKING:
    from .run_manager import RunManager
    from ..models.runtime import RunContext

logger = logging.getLogger(__name__)


class SearchTaskRunner:
    def __init__(self, manager: "RunManager") -> None:
        self.manager = manager

    async def optimizer_loop(self, run_id: str) -> None:
        ctx = self.manager.runs.get(run_id)
        if not ctx:
            return

        from .es_service import ESService
        from .llm_service import LLMService

        def now_ts() -> str:
            return datetime.now(timezone.utc).isoformat()

        ctx.stage = "running"
        ctx.started_at = now_ts()
        start_time = time.monotonic()

        await self.manager.publish(
            run_id,
            {"type": "run.stage", "payload": {"runId": run_id, "stage": "running"}},
        )

        llm_svc: Optional[LLMService] = None
        if ctx.llm_config and ctx.llm_config.provider != "disabled":
            llm_svc = LLMService(ctx.llm_config)

        plateau_count = 0
        max_plateau = 15
        es_svc: Optional[ESService] = None
        if ctx.es_url:
            es_svc = ESService(es_url=ctx.es_url, api_key=ctx.api_key or None)

        try:
            try:
                (
                    baseline_score,
                    baseline_failures,
                    baseline_per_query,
                ) = await self.evaluate_detailed(
                    ctx,
                    ctx.baseline_profile,
                    es_svc=es_svc,
                )
                ctx.metrics.baselineScore = baseline_score
                ctx.metrics.currentScore = baseline_score
                ctx.metrics.bestScore = baseline_score
                ctx.best_score = baseline_score
                ctx._current_query_failures = baseline_failures
                if ctx.original_baseline_score is not None:
                    ctx.metrics.originalBaselineScore = ctx.original_baseline_score
                    ctx.metrics.priorExperimentsRun = ctx.prior_experiments_run
                    ctx.metrics.priorImprovementsKept = ctx.prior_improvements_kept
                    orig = ctx.original_baseline_score
                    ctx.metrics.improvementPct = (
                        (baseline_score - orig) / max(orig, 0.001)
                    ) * 100
                for query_id, query_score in baseline_per_query.items():
                    ctx.per_query_scores[query_id] = {
                        "baseline": query_score,
                        "best": query_score,
                    }
                baseline_previews = await self._collect_query_result_previews(
                    ctx,
                    ctx.baseline_profile,
                    es_svc=es_svc,
                )
                for query_id, previews in baseline_previews.items():
                    ctx.per_query_results[query_id] = {
                        "baseline": previews,
                        "best": previews,
                    }
            except Exception as exc:
                logger.error("Baseline evaluation failed: %s", exc)
                ctx.warnings.append(f"Baseline evaluation failed: {exc}")
                ctx.metrics.baselineScore = 0.5
                ctx.metrics.currentScore = 0.5
                ctx.metrics.bestScore = 0.5
                ctx._current_query_failures = []

            await self.manager._persist_search_run(run_id)

            for exp_num in range(ctx.max_experiments):
                if ctx.cancel_flag.is_set():
                    break
                elapsed = time.monotonic() - start_time
                if elapsed >= ctx.duration_minutes * 60:
                    break
                if ctx.auto_stop_on_plateau and plateau_count >= max_plateau:
                    break

                try:
                    change = await self._pick_next_experiment(ctx, llm_svc, exp_num)
                    if not change:
                        await asyncio.sleep(2.0)
                        continue

                    candidate = ctx.current_profile.model_copy(deep=True)
                    _apply_profile_change(candidate, change)

                    iteration_started = time.monotonic()
                    (
                        candidate_score,
                        candidate_failures,
                        candidate_per_query,
                    ) = await self.evaluate_detailed(
                        ctx,
                        candidate,
                        es_svc=es_svc,
                    )
                    duration_ms = int((time.monotonic() - iteration_started) * 1000)
                    before_score = ctx.metrics.currentScore
                    query_failures_before = list(ctx._current_query_failures)
                    delta_abs = candidate_score - before_score
                    delta_pct = (delta_abs / max(before_score, 0.001)) * 100

                    if delta_abs >= settings.keep_threshold:
                        decision = "kept"
                        ctx.current_profile = candidate
                        ctx._current_query_failures = candidate_failures
                        if candidate_score > ctx.best_score:
                            ctx.best_score = candidate_score
                            ctx.best_profile = candidate.model_copy(deep=True)
                            for query_id, query_score in candidate_per_query.items():
                                if query_id in ctx.per_query_scores:
                                    ctx.per_query_scores[query_id]["best"] = max(
                                        ctx.per_query_scores[query_id].get("best", 0.0),
                                        query_score,
                                    )
                                else:
                                    ctx.per_query_scores[query_id] = {
                                        "baseline": query_score,
                                        "best": query_score,
                                    }
                        plateau_count = 0
                    else:
                        decision = "reverted"
                        plateau_count += 1

                    record = ExperimentRecord(
                        experimentId=exp_num + 1,
                        timestamp=now_ts(),
                        hypothesis=build_hypothesis_text(change),
                        change=change,
                        beforeScore=before_score,
                        candidateScore=candidate_score,
                        deltaAbsolute=round(delta_abs, 6),
                        deltaPercent=round(delta_pct, 4),
                        decision=decision,
                        durationMs=duration_ms,
                        queryFailuresBefore=query_failures_before[:10],
                        queryFailuresAfter=candidate_failures[:10],
                    )
                    ctx.experiments.append(record)

                    ctx.metrics.experimentsRun = exp_num + 1
                    ctx.metrics.currentScore = (
                        candidate_score if decision == "kept" else before_score
                    )
                    ctx.metrics.bestScore = ctx.best_score
                    ref_baseline = (
                        ctx.metrics.originalBaselineScore
                        if ctx.metrics.originalBaselineScore is not None
                        else ctx.metrics.baselineScore
                    )
                    ctx.metrics.improvementPct = (
                        (ctx.best_score - ref_baseline) / max(ref_baseline, 0.001)
                    ) * 100
                    ctx.metrics.elapsedSeconds = time.monotonic() - start_time
                    if decision == "kept":
                        ctx.metrics.improvementsKept += 1
                    ctx.metrics.scoreTimeline.append(
                        {
                            "t": ctx.metrics.elapsedSeconds,
                            "score": ctx.metrics.currentScore,
                        }
                    )

                    await self.manager.publish(
                        run_id,
                        {
                            "type": "experiment.completed",
                            "payload": record.model_dump(),
                        },
                    )
                    await self.manager.publish(
                        run_id,
                        {"type": "metrics.tick", "payload": ctx.metrics.model_dump()},
                    )
                    if (exp_num + 1) % 10 == 0 or exp_num == ctx.max_experiments - 1:
                        await self.manager._persist_search_run(run_id)

                    if duration_ms < 500:
                        await asyncio.sleep(1.8)
                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    logger.error("Optimizer error at experiment %d: %s", exp_num, exc)
                    await asyncio.sleep(1.0)

            try:
                (
                    final_best_score,
                    final_failures,
                    final_per_query,
                ) = await self.evaluate_detailed(
                    ctx,
                    ctx.best_profile,
                    es_svc=es_svc,
                )
                ctx.best_score = final_best_score
                ctx.metrics.bestScore = final_best_score
                ctx.metrics.currentScore = final_best_score
                ref_baseline_final = (
                    ctx.metrics.originalBaselineScore
                    if ctx.metrics.originalBaselineScore is not None
                    else ctx.metrics.baselineScore
                )
                ctx.metrics.improvementPct = (
                    (final_best_score - ref_baseline_final)
                    / max(ref_baseline_final, 0.001)
                ) * 100
                ctx._current_query_failures = final_failures
                for query_id, query_score in final_per_query.items():
                    baseline_score = ctx.per_query_scores.get(query_id, {}).get(
                        "baseline", query_score
                    )
                    ctx.per_query_scores[query_id] = {
                        "baseline": baseline_score,
                        "best": query_score,
                    }
                best_previews = await self._collect_query_result_previews(
                    ctx,
                    ctx.best_profile,
                    es_svc=es_svc,
                )
                for query_id, previews in best_previews.items():
                    existing = ctx.per_query_results.get(query_id, {})
                    ctx.per_query_results[query_id] = {
                        "baseline": existing.get("baseline", previews),
                        "best": previews,
                    }
            except Exception as exc:
                logger.warning(
                    "Final best-profile evaluation failed for run %s: %s", run_id, exc
                )
                ctx.warnings.append(f"Final best-profile evaluation failed: {exc}")
        finally:
            if es_svc:
                await es_svc.close()

        from .report_service import ReportService

        ctx.stage = "completed"
        ctx.completed_at = now_ts()
        ctx.report = await ReportService().generate_async(ctx)
        await self.manager._persist_search_run(run_id)
        if self.manager.persistence and ctx.report:
            await self.manager.persistence.save_report(ctx.report)
        if ctx.report:
            from .elastic_sink_service import ElasticSinkService

            sink = ElasticSinkService.from_settings()
            if sink is not None:
                try:
                    await sink.index_search_run(ctx.report)
                except Exception as exc:
                    logger.warning("Elastic sink indexing failed for search run %s: %s", run_id, exc)
                    ctx.warnings.append(f"Elastic sink indexing failed: {exc}")
                finally:
                    await sink.close()
        await self.manager.publish(
            run_id,
            {"type": "run.stage", "payload": {"runId": run_id, "stage": "completed"}},
        )

    async def evaluate_profile(
        self,
        ctx: "RunContext",
        profile: SearchProfile,
        es_svc: Optional[Any] = None,
    ) -> tuple[float, List[str], Dict[str, float]]:
        if not ctx.eval_set:
            return 0.5, [], {}

        from .es_service import ESService

        close_after = False
        if es_svc is None:
            if not ctx.es_url or not ctx.index_name:
                return 0.0, [case.query for case in ctx.eval_set], {}
            es_svc = ESService(es_url=ctx.es_url, api_key=ctx.api_key or None)
            close_after = True

        if settings.use_msearch_eval and hasattr(es_svc, "msearch_profile_queries"):
            try:
                ranked_results = await es_svc.msearch_profile_queries(
                    index=ctx.index_name or ctx.summary.indexName,
                    eval_cases=ctx.eval_set,
                    profile=profile,
                    size=10,
                )
                total_ndcg = 0.0
                missed_queries: List[str] = []
                per_query_scores: Dict[str, float] = {}
                for case in ctx.eval_set:
                    ranked_doc_ids = ranked_results.get(case.id, [])
                    ndcg = self._compute_ndcg_at_k(case.relevantDocIds, ranked_doc_ids, k=10)
                    per_query_scores[case.id] = ndcg
                    total_ndcg += ndcg
                    if ndcg == 0:
                        missed_queries.append(case.query)
                return total_ndcg / max(len(ctx.eval_set), 1), missed_queries, per_query_scores
            except Exception as exc:
                logger.warning("msearch evaluation failed, falling back to per-query scoring: %s", exc)

        async def evaluate_case(case: Any) -> tuple[str, float, Optional[str]]:
            if not case.relevantDocIds:
                return case.id, 0.0, None
            try:
                ranked_doc_ids = await es_svc.execute_profile_query(
                    index=ctx.index_name or ctx.summary.indexName,
                    query_text=case.query,
                    profile=profile,
                    size=10,
                )
            except Exception as exc:
                logger.warning("Query evaluation failed for '%s': %s", case.query, exc)
                ranked_doc_ids = []
            ndcg = self._compute_ndcg_at_k(case.relevantDocIds, ranked_doc_ids, k=10)
            return case.id, ndcg, case.query if ndcg == 0 else None

        total_ndcg = 0.0
        evaluated = 0
        missed_queries: List[str] = []
        per_query_scores: Dict[str, float] = {}
        semaphore = asyncio.Semaphore(10)

        async def limited(case: Any) -> tuple[str, float, Optional[str]]:
            async with semaphore:
                return await evaluate_case(case)

        try:
            results = await asyncio.gather(*(limited(case) for case in ctx.eval_set))
            for query_id, ndcg, missed_query in results:
                per_query_scores[query_id] = ndcg
                total_ndcg += ndcg
                evaluated += 1
                if missed_query:
                    missed_queries.append(missed_query)
        finally:
            if close_after:
                await es_svc.close()

        return total_ndcg / max(evaluated, 1), missed_queries, per_query_scores

    async def evaluate_detailed(
        self,
        ctx: "RunContext",
        profile: SearchProfile,
        es_svc: Optional[Any] = None,
    ) -> tuple[float, List[str], Dict[str, float]]:
        return await self.evaluate_profile(ctx, profile, es_svc=es_svc)

    async def collect_query_result_previews(
        self,
        ctx: "RunContext",
        profile: SearchProfile,
        es_svc: Optional[Any] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        return await self._collect_query_result_previews(ctx, profile, es_svc=es_svc)

    async def _collect_query_result_previews(
        self,
        ctx: "RunContext",
        profile: SearchProfile,
        es_svc: Optional[Any] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        if not ctx.eval_set:
            return {}

        from .es_service import ESService

        close_after = False
        if es_svc is None:
            if not ctx.es_url or not ctx.index_name:
                return {}
            es_svc = ESService(es_url=ctx.es_url, api_key=ctx.api_key or None)
            close_after = True

        semaphore = asyncio.Semaphore(10)

        async def fetch(case: Any) -> tuple[str, List[Dict[str, Any]]]:
            async with semaphore:
                try:
                    hits = await es_svc.execute_profile_query_with_hits(
                        index=ctx.index_name or ctx.summary.indexName,
                        query_text=case.query,
                        profile=profile,
                        size=5,
                    )
                    return case.id, hits
                except Exception as exc:
                    logger.warning(
                        "Preview collection failed for '%s': %s", case.query, exc
                    )
                    return case.id, []

        try:
            return dict(await asyncio.gather(*(fetch(case) for case in ctx.eval_set)))
        finally:
            if close_after:
                await es_svc.close()

    async def _pick_next_experiment(
        self,
        ctx: "RunContext",
        llm_svc: Optional[Any],
        exp_num: int,
    ) -> Optional[SearchProfileChange]:
        if llm_svc and llm_svc.available and exp_num % 3 == 0:
            try:
                suggestion = await llm_svc.suggest_experiment(
                    current_profile=ctx.current_profile.model_dump(),
                    experiment_history=[
                        experiment.model_dump() for experiment in ctx.experiments[-5:]
                    ],
                    domain=ctx.summary.detectedDomain,
                    current_score=ctx.metrics.currentScore,
                )
                if suggestion and isinstance(suggestion, dict):
                    return SearchProfileChange(
                        path=suggestion.get("path", "tieBreaker"),
                        before=suggestion.get("before", 0.0),
                        after=suggestion.get("after", 0.1),
                        label=suggestion.get("label", "LLM suggested change"),
                    )
            except Exception as exc:
                logger.warning("LLM suggestion failed: %s", exc)

        combined_history = [*ctx.prior_experiments, *ctx.experiments]
        if ctx.optimizer_strategy == "adaptive_evolutionary":
            return _adaptive_evolutionary_experiment(ctx.current_profile, combined_history)
        return _heuristic_next_experiment(ctx.current_profile, combined_history)

    async def persona_simulator_loop(self, run_id: str) -> None:
        ctx = self.manager.runs.get(run_id)
        if not ctx:
            return

        rng = random.Random(42)
        while not ctx.cancel_flag.is_set() and ctx.stage in ("running", "starting"):
            try:
                batch_size = min(3, len(ctx.personas))
                if batch_size == 0:
                    await asyncio.sleep(settings.persona_batch_interval_seconds)
                    continue

                selected = rng.sample(ctx.personas, batch_size)
                for persona in selected:
                    if not persona.queries:
                        continue

                    query = rng.choice(persona.queries)
                    persona.lastQuery = query
                    persona.state = "searching"
                    persona.totalSearches += 1

                    base = ctx.metrics.currentScore
                    roll = rng.random()
                    if roll < base:
                        persona.state = "success"
                        persona.successes += 1
                        persona.lastResultRank = rng.randint(1, 3)
                    elif roll < base + 0.2:
                        persona.state = "partial"
                        persona.partials += 1
                        persona.lastResultRank = rng.randint(4, 8)
                    else:
                        persona.state = "failure"
                        persona.failures += 1
                        persona.lastResultRank = None

                    total = persona.totalSearches
                    persona.successRate = (
                        persona.successes + persona.partials * 0.5
                    ) / max(total, 1)

                if ctx.personas:
                    ctx.metrics.personaSuccessRate = sum(
                        persona.successRate for persona in ctx.personas
                    ) / len(ctx.personas)

                await self.manager.publish(
                    run_id,
                    {
                        "type": "persona.batch",
                        "payload": {
                            "runId": run_id,
                            "personas": [persona.model_dump() for persona in selected],
                        },
                    },
                )
                await asyncio.sleep(settings.persona_batch_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Persona simulator error: %s", exc)
                await asyncio.sleep(2.0)

    async def compression_benchmark(self, run_id: str) -> None:
        ctx = self.manager.runs.get(run_id)
        if not ctx:
            return
        if not ctx.summary.vectorField or not ctx.summary.vectorDims:
            ctx.compression.status = "skipped"
            return

        from ..models.contracts import CompressionMethodResult

        ctx.compression.available = True
        ctx.compression.vectorField = ctx.summary.vectorField
        ctx.compression.vectorDims = ctx.summary.vectorDims
        ctx.compression.status = "running"

        try:
            await asyncio.wait_for(ctx.cancel_flag.wait(), timeout=10.0)
            return
        except asyncio.TimeoutError:
            pass

        methods = [
            ("float32", 1.0, 1.0),
            ("int8", 0.25, 0.987),
            ("int4", 0.125, 0.971),
            ("rotated_int4", 0.125, 0.979),
        ]

        dims = ctx.summary.vectorDims or 768
        doc_count = ctx.summary.docCount
        float32_size = dims * 4 * doc_count
        cost_per_byte_month = settings.cost_per_gb_per_month / (1024**3)
        results = []
        for method_name, size_ratio, recall in methods:
            if ctx.cancel_flag.is_set():
                break
            size_bytes = int(float32_size * size_ratio)
            monthly_cost = size_bytes * cost_per_byte_month
            results.append(
                CompressionMethodResult(
                    method=method_name,
                    sizeBytes=size_bytes,
                    recallAt10=recall,
                    estimatedMonthlyCostUsd=round(monthly_cost, 2),
                    sizeReductionPct=round((1 - size_ratio) * 100, 1),
                    status="done",
                )
            )
            try:
                await asyncio.wait_for(ctx.cancel_flag.wait(), timeout=3.0)
                break
            except asyncio.TimeoutError:
                pass

        ctx.compression.methods = results
        ctx.compression.status = "done"
        ctx.compression.bestRecommendation = "int8"
        if results:
            int8_result = next(
                (result for result in results if result.method == "int8"), None
            )
            if int8_result:
                savings = (
                    results[0].estimatedMonthlyCostUsd
                    - int8_result.estimatedMonthlyCostUsd
                )
                ctx.compression.projectedMonthlySavingsUsd = round(max(savings, 0), 2)
                ctx.metrics.projectedMonthlySavingsUsd = (
                    ctx.compression.projectedMonthlySavingsUsd
                )

        await self.manager.publish(
            run_id,
            {"type": "compression.updated", "payload": ctx.compression.model_dump()},
        )
        await self.manager._persist_search_run(run_id)

    async def metrics_heartbeat(self, run_id: str) -> None:
        ctx = self.manager.runs.get(run_id)
        if not ctx:
            return
        start_time = time.monotonic()
        while not ctx.cancel_flag.is_set() and ctx.stage in ("running", "starting"):
            try:
                ctx.metrics.elapsedSeconds = time.monotonic() - start_time
                await self.manager.publish(
                    run_id,
                    {"type": "metrics.tick", "payload": ctx.metrics.model_dump()},
                )
                await asyncio.sleep(settings.metrics_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Metrics heartbeat error: %s", exc)
                await asyncio.sleep(2.0)

    def _compute_ndcg_at_k(
        self,
        relevant_doc_ids: List[str],
        ranked_doc_ids: List[str],
        k: int = 10,
    ) -> float:
        relevant = [str(doc_id) for doc_id in relevant_doc_ids if str(doc_id)]
        if not relevant:
            return 0.0
        relevant_set = set(relevant)
        dcg = 0.0
        for rank, doc_id in enumerate(ranked_doc_ids[:k], start=1):
            if str(doc_id) in relevant_set:
                dcg += 1.0 / math.log2(rank + 1)
        ideal_count = min(len(relevant_set), k)
        ideal_dcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_count + 1))
        if ideal_dcg == 0:
            return 0.0
        return dcg / ideal_dcg


def _apply_profile_change(profile: SearchProfile, change: SearchProfileChange) -> None:
    import re as _re

    match = _re.match(r"lexicalFields\[(\d+)\]\.boost", change.path)
    if match:
        index = int(match.group(1))
        if index < len(profile.lexicalFields):
            profile.lexicalFields[index] = profile.lexicalFields[index].model_copy(
                update={"boost": change.after}
            )
        return
    if hasattr(profile, change.path):
        setattr(profile, change.path, change.after)


_GRID_LEXICAL: List[Dict[str, Any]] = [
    {
        "path": "multiMatchType",
        "values": ["best_fields", "most_fields", "cross_fields", "phrase"],
    },
    {
        "path": "minimumShouldMatch",
        "values": ["50%", "60%", "70%", "75%", "80%", "85%", "90%", "100%"],
    },
    {"path": "tieBreaker", "values": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]},
    {"path": "phraseBoost", "values": [0.0, 0.5, 1.0, 1.5, 2.0, 3.0]},
    {"path": "fuzziness", "values": ["0", "AUTO"]},
]
_GRID_VECTOR: List[Dict[str, Any]] = [
    {"path": "vectorWeight", "values": [0.2, 0.3, 0.35, 0.4, 0.5, 0.6]},
    {"path": "fusionMethod", "values": ["weighted_sum", "rrf"]},
    {"path": "rrfRankConstant", "values": [20, 40, 60, 80, 100]},
    {"path": "knnK", "values": [10, 15, 20, 30, 50]},
]
_FIELD_LABELS: Dict[str, str] = {
    "minimumShouldMatch": "Minimum should match",
    "tieBreaker": "Tie breaker",
    "phraseBoost": "Phrase boost",
    "multiMatchType": "Multi-match type",
    "fuzziness": "Fuzziness",
    "vectorWeight": "Vector weight",
    "fusionMethod": "Fusion method",
    "rrfRankConstant": "RRF rank constant",
    "knnK": "KNN k",
}
_BOOST_VALUES = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
_CONTINUOUS_PARAMS: List[Dict[str, Any]] = [
    {"path": "tieBreaker", "min": 0.0, "max": 0.7, "round": 2, "label": "Tie breaker"},
    {
        "path": "phraseBoost",
        "min": 0.0,
        "max": 5.0,
        "round": 1,
        "label": "Phrase boost",
    },
]
_DISCRETE_PARAMS: List[Dict[str, Any]] = [
    {
        "path": "multiMatchType",
        "values": ["best_fields", "most_fields", "cross_fields", "phrase"],
        "label": "Multi-match type",
    },
    {
        "path": "minimumShouldMatch",
        "values": [
            "50%",
            "55%",
            "60%",
            "65%",
            "70%",
            "75%",
            "80%",
            "85%",
            "90%",
            "95%",
            "100%",
        ],
        "label": "Minimum should match",
    },
    {"path": "fuzziness", "values": ["0", "AUTO"], "label": "Fuzziness"},
]
_VECTOR_CONTINUOUS: List[Dict[str, Any]] = [
    {
        "path": "vectorWeight",
        "min": 0.1,
        "max": 0.8,
        "round": 2,
        "label": "Vector weight",
    },
]
_VECTOR_DISCRETE: List[Dict[str, Any]] = [
    {
        "path": "fusionMethod",
        "values": ["weighted_sum", "rrf"],
        "label": "Fusion method",
    },
    {
        "path": "rrfRankConstant",
        "min": 10,
        "max": 120,
        "step": 10,
        "label": "RRF rank constant",
    },
    {"path": "knnK", "min": 5, "max": 80, "step": 5, "label": "KNN k"},
]


def _heuristic_next_experiment(
    profile: SearchProfile, history: List[ExperimentRecord]
) -> Optional[SearchProfileChange]:
    tried: Dict[str, set] = {}
    for experiment in history:
        tried.setdefault(experiment.change.path, set()).add(
            str(experiment.change.after)
        )
    rng = random.Random(len(history))
    grid_result = _grid_sweep(profile, tried, rng)
    if grid_result is not None:
        return grid_result
    return _random_perturbation(profile, history, rng)


def _grid_sweep(
    profile: SearchProfile,
    tried: Dict[str, set],
    rng: random.Random,
) -> Optional[SearchProfileChange]:
    security_candidates = generate_security_field_mutations(profile)
    rng.shuffle(security_candidates)
    for candidate in security_candidates:
        if str(candidate.after) not in tried.get(candidate.path, set()):
            return candidate

    space = list(_GRID_LEXICAL)
    if profile.useVector:
        space.extend(_GRID_VECTOR)
    for index, field_entry in enumerate(profile.lexicalFields):
        space.append(
            {
                "path": f"lexicalFields[{index}].boost",
                "values": _BOOST_VALUES,
                "_field_index": index,
                "_field_name": field_entry.get("field", f"field_{index}"),
            }
        )
    rng.shuffle(space)

    for item in space:
        path = item["path"]
        tried_vals = tried.get(path, set())
        if path.startswith("lexicalFields["):
            field_idx = item["_field_index"]
            current_val = profile.lexicalFields[field_idx]["boost"]
            field_name = item["_field_name"]
            for value in item["values"]:
                if str(value) not in tried_vals and value != current_val:
                    return SearchProfileChange(
                        path=path,
                        before=current_val,
                        after=value,
                        label=f"{field_name} boost {current_val} → {value}",
                    )
        else:
            current_val = getattr(profile, path, None)
            for value in item["values"]:
                if str(value) not in tried_vals and value != current_val:
                    return SearchProfileChange(
                        path=path,
                        before=current_val,
                        after=value,
                        label=f"{_FIELD_LABELS.get(path, path)} {current_val!r} → {value!r}",
                    )
    return None


def _random_perturbation(
    profile: SearchProfile,
    history: List[ExperimentRecord],
    rng: random.Random,
) -> SearchProfileChange:
    reverted_signatures = {
        (experiment.change.path, str(experiment.change.after))
        for experiment in history
        if experiment.decision == "reverted"
    }
    if len(history) % 5 < 3:
        return _single_random_mutation(profile, reverted_signatures, rng)
    return _combo_mutation(profile, reverted_signatures, rng)


def _adaptive_evolutionary_experiment(
    profile: SearchProfile,
    history: List[ExperimentRecord],
) -> SearchProfileChange:
    positive_history = [
        experiment
        for experiment in history
        if experiment.decision == "kept" and experiment.deltaAbsolute > 0
    ]
    rng = random.Random(len(history) * 17 + 7)
    if not positive_history:
        return _heuristic_next_experiment(profile, history) or _random_perturbation(
            profile,
            history,
            rng,
        )

    scored_paths: Dict[str, float] = {}
    for experiment in positive_history:
        scored_paths[experiment.change.path] = scored_paths.get(experiment.change.path, 0.0) + max(
            experiment.deltaAbsolute,
            0.001,
        )

    ordered_paths = sorted(
        scored_paths.items(),
        key=lambda item: item[1],
        reverse=True,
    )
    reverted_signatures = {
        (experiment.change.path, str(experiment.change.after))
        for experiment in history
        if experiment.decision == "reverted"
    }

    for path, _score in ordered_paths[:5]:
        candidate = _mutate_specific_path(profile, path, rng)
        if candidate and (candidate.path, str(candidate.after)) not in reverted_signatures:
            return candidate

    return _random_perturbation(profile, history, rng)


def _mutate_specific_path(
    profile: SearchProfile,
    path: str,
    rng: random.Random,
) -> Optional[SearchProfileChange]:
    if path.startswith("lexicalFields[") and path.endswith("].boost"):
        start = path.index("[") + 1
        end = path.index("]")
        index = int(path[start:end])
        if index >= len(profile.lexicalFields):
            return None
        current = profile.lexicalFields[index]["boost"]
        delta = rng.choice([-1.0, -0.5, -0.25, 0.25, 0.5, 1.0])
        new_val = round(max(0.1, min(10.0, current + delta)), 2)
        if new_val == current:
            return None
        field_name = profile.lexicalFields[index].get("field", f"field_{index}")
        return SearchProfileChange(
            path=path,
            before=current,
            after=new_val,
            label=f"{field_name} boost {current} → {new_val} (adaptive)",
        )

    if path in {"tieBreaker", "phraseBoost", "vectorWeight"}:
        ranges = {
            "tieBreaker": (0.0, 0.7, 2),
            "phraseBoost": (0.0, 5.0, 1),
            "vectorWeight": (0.1, 0.8, 2),
        }
        low, high, rounding = ranges[path]
        current = getattr(profile, path, low)
        candidate = round(rng.uniform(low, high), rounding)
        if candidate == current:
            return None
        return SearchProfileChange(
            path=path,
            before=current,
            after=candidate,
            label=f"{_FIELD_LABELS.get(path, path)} {current} → {candidate} (adaptive)",
        )

    if path in {"multiMatchType", "minimumShouldMatch", "fuzziness", "fusionMethod"}:
        discrete_values = {
            "multiMatchType": ["best_fields", "most_fields", "cross_fields", "phrase"],
            "minimumShouldMatch": [
                "50%",
                "55%",
                "60%",
                "65%",
                "70%",
                "75%",
                "80%",
                "85%",
                "90%",
                "95%",
                "100%",
            ],
            "fuzziness": ["0", "AUTO"],
            "fusionMethod": ["weighted_sum", "rrf"],
        }
        current = getattr(profile, path, None)
        options = [value for value in discrete_values[path] if value != current]
        if not options:
            return None
        candidate = rng.choice(options)
        return SearchProfileChange(
            path=path,
            before=current,
            after=candidate,
            label=f"{_FIELD_LABELS.get(path, path)} {current!r} → {candidate!r} (adaptive)",
        )

    if path in {"rrfRankConstant", "knnK"}:
        params = {
            "rrfRankConstant": (10, 120, 10),
            "knnK": (5, 80, 5),
        }
        low, high, step = params[path]
        current = getattr(profile, path, low)
        options = [value for value in range(low, high + 1, step) if value != current]
        if not options:
            return None
        candidate = rng.choice(options)
        return SearchProfileChange(
            path=path,
            before=current,
            after=candidate,
            label=f"{_FIELD_LABELS.get(path, path)} {current} → {candidate} (adaptive)",
        )
    return None


def _single_random_mutation(
    profile: SearchProfile,
    reverted_signatures: set[tuple[str, str]],
    rng: random.Random,
) -> SearchProfileChange:
    candidates: List[SearchProfileChange] = []
    for index, field_entry in enumerate(profile.lexicalFields):
        current = field_entry["boost"]
        delta = rng.choice([-2.0, -1.0, -0.5, -0.25, 0.25, 0.5, 1.0, 2.0])
        new_val = round(max(0.1, min(10.0, current + delta)), 2)
        if new_val != current:
            candidates.append(
                SearchProfileChange(
                    path=f"lexicalFields[{index}].boost",
                    before=current,
                    after=new_val,
                    label=f"{field_entry.get('field', f'field_{index}')} boost {current} → {new_val}",
                )
            )

    for param in _CONTINUOUS_PARAMS:
        current = getattr(profile, param["path"], 0.0)
        new_val = round(rng.uniform(param["min"], param["max"]), param["round"])
        if new_val != current:
            candidates.append(
                SearchProfileChange(
                    path=param["path"],
                    before=current,
                    after=new_val,
                    label=f"{param['label']} {current} → {new_val}",
                )
            )

    for param in _DISCRETE_PARAMS:
        current = getattr(profile, param["path"], None)
        other_vals = [value for value in param["values"] if value != current]
        if other_vals:
            new_val = rng.choice(other_vals)
            candidates.append(
                SearchProfileChange(
                    path=param["path"],
                    before=current,
                    after=new_val,
                    label=f"{param['label']} {current!r} → {new_val!r}",
                )
            )

    if profile.useVector:
        for param in _VECTOR_CONTINUOUS:
            current = getattr(profile, param["path"], 0.35)
            new_val = round(rng.uniform(param["min"], param["max"]), param["round"])
            if new_val != current:
                candidates.append(
                    SearchProfileChange(
                        path=param["path"],
                        before=current,
                        after=new_val,
                        label=f"{param['label']} {current} → {new_val}",
                    )
                )
        for param in _VECTOR_DISCRETE:
            if "values" in param:
                current = getattr(profile, param["path"], None)
                other_vals = [value for value in param["values"] if value != current]
                if other_vals:
                    new_val = rng.choice(other_vals)
                    candidates.append(
                        SearchProfileChange(
                            path=param["path"],
                            before=current,
                            after=new_val,
                            label=f"{param['label']} {current!r} → {new_val!r}",
                        )
                    )
            else:
                current = getattr(profile, param["path"], param["min"])
                possible = list(
                    range(param["min"], param["max"] + 1, param.get("step", 1))
                )
                other_vals = [value for value in possible if value != current]
                if other_vals:
                    new_val = rng.choice(other_vals)
                    candidates.append(
                        SearchProfileChange(
                            path=param["path"],
                            before=current,
                            after=new_val,
                            label=f"{param['label']} {current} → {new_val}",
                        )
                    )

    filtered = [
        candidate
        for candidate in candidates
        if (candidate.path, str(candidate.after)) not in reverted_signatures
    ]
    if filtered:
        return rng.choice(filtered)
    if candidates:
        return rng.choice(candidates)
    current_fuzz = profile.fuzziness
    new_fuzz = "AUTO" if current_fuzz == "0" else "0"
    return SearchProfileChange(
        path="fuzziness",
        before=current_fuzz,
        after=new_fuzz,
        label=f"Fuzziness {current_fuzz!r} → {new_fuzz!r}",
    )


def _combo_mutation(
    profile: SearchProfile,
    reverted_signatures: set[tuple[str, str]],
    rng: random.Random,
) -> SearchProfileChange:
    candidates: List[SearchProfileChange] = []
    for index, field_entry in enumerate(profile.lexicalFields):
        current = field_entry["boost"]
        new_val = round(rng.uniform(0.1, 8.0), 1)
        if abs(new_val - current) > 0.5:
            candidates.append(
                SearchProfileChange(
                    path=f"lexicalFields[{index}].boost",
                    before=current,
                    after=new_val,
                    label=f"{field_entry.get('field', f'field_{index}')} boost {current} → {new_val} (explore)",
                )
            )

    current_tb = profile.tieBreaker
    new_tb = round(rng.uniform(0.0, 0.8), 2)
    if new_tb != current_tb:
        candidates.append(
            SearchProfileChange(
                path="tieBreaker",
                before=current_tb,
                after=new_tb,
                label=f"Tie breaker {current_tb} → {new_tb} (explore)",
            )
        )

    current_pb = profile.phraseBoost
    new_pb = round(rng.uniform(0.0, 6.0), 1)
    if new_pb != current_pb:
        candidates.append(
            SearchProfileChange(
                path="phraseBoost",
                before=current_pb,
                after=new_pb,
                label=f"Phrase boost {current_pb} → {new_pb} (explore)",
            )
        )

    all_msm = [
        "50%",
        "55%",
        "60%",
        "65%",
        "70%",
        "75%",
        "80%",
        "85%",
        "90%",
        "95%",
        "100%",
    ]
    current_msm = profile.minimumShouldMatch
    other_msm = [value for value in all_msm if value != current_msm]
    if other_msm:
        new_msm = rng.choice(other_msm)
        candidates.append(
            SearchProfileChange(
                path="minimumShouldMatch",
                before=current_msm,
                after=new_msm,
                label=f"Minimum should match {current_msm!r} → {new_msm!r} (explore)",
            )
        )

    filtered = [
        candidate
        for candidate in candidates
        if (candidate.path, str(candidate.after)) not in reverted_signatures
    ]
    if filtered:
        return rng.choice(filtered)
    if candidates:
        return rng.choice(candidates)
    return _single_random_mutation(profile, reverted_signatures, rng)
