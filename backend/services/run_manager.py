from __future__ import annotations

import asyncio
import logging
import math
import random
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

import orjson

from ..models.contracts import (
    CompressionSummary,
    ConnectionSummary,
    EvalCase,
    ExperimentRecord,
    HeroMetrics,
    LlmConfig,
    PersonaViewModel,
    RunSnapshot,
    RunStage,
    SearchProfile,
    SearchProfileChange,
)
from ..models.runtime import ConnectionContext, RunContext
from ..models.report import ReportPayload
from ..committee.evaluator import CommitteeEvaluator
from ..committee.models import CommitteeSnapshot, CommitteePersonaView, RewriteAttempt, ScoreTimelinePoint
from ..committee.reporting import build_export_payload, build_report
from ..committee.rewrite_engine import CommitteeRewriteEngine
from ..committee.runtime import CommitteeConnectionContext, CommitteeRunContext
from ..config import settings
from .persistence_service import PersistenceService
from .report_service import ReportService

logger = logging.getLogger(__name__)


class RunManager:
    """Central coordinator for all runs and WebSocket subscriptions."""

    def __init__(self, persistence: Optional[PersistenceService] = None) -> None:
        self.connections: Dict[str, ConnectionContext] = {}
        self.runs: Dict[str, RunContext] = {}
        self.committee_connections: Dict[str, CommitteeConnectionContext] = {}
        self.committee_runs: Dict[str, CommitteeRunContext] = {}
        self.subscribers: Dict[str, Set[asyncio.Queue]] = {}
        self.persistence = persistence

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    async def create_connection(self, connection_id: str, ctx: ConnectionContext) -> None:
        self.connections[connection_id] = ctx
        if self.persistence:
            await self.persistence.save_connection(
                {
                    "connection_id": connection_id,
                    "mode": ctx.mode,
                    "es_url": ctx.es_url,
                    "api_key": ctx.api_key,
                    "index_name": ctx.index_name,
                    "summary": ctx.summary.model_dump(),
                    "eval_set": [case.model_dump() for case in ctx.eval_set],
                    "baseline_profile": ctx.baseline_profile.model_dump(),
                    "llm_config": ctx.llm_config.model_dump() if ctx.llm_config else None,
                    "text_fields": ctx.text_fields,
                    "sample_docs": ctx.sample_docs,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )

    async def get_connection(self, connection_id: str) -> Optional[ConnectionContext]:
        return self.connections.get(connection_id)

    async def create_committee_connection(
        self,
        connection_id: str,
        ctx: CommitteeConnectionContext,
    ) -> None:
        self.committee_connections[connection_id] = ctx

    async def get_committee_connection(
        self,
        connection_id: str,
    ) -> Optional[CommitteeConnectionContext]:
        return self.committee_connections.get(connection_id)

    # ------------------------------------------------------------------
    # Run management
    # ------------------------------------------------------------------

    async def create_run(self, run_id: str, ctx: RunContext) -> None:
        self.runs[run_id] = ctx
        self.subscribers[run_id] = set()
        await self._persist_search_run(run_id)

    async def get_run(self, run_id: str) -> Optional[RunContext]:
        return self.runs.get(run_id)

    async def create_committee_run(self, run_id: str, ctx: CommitteeRunContext) -> None:
        self.committee_runs[run_id] = ctx
        self.subscribers[run_id] = set()

    async def get_committee_run(self, run_id: str) -> Optional[CommitteeRunContext]:
        return self.committee_runs.get(run_id)

    async def get_snapshot(self, run_id: str) -> Optional[RunSnapshot]:
        ctx = self.runs.get(run_id)
        if not ctx:
            if self.persistence:
                return await self.persistence.load_snapshot(run_id)
            return None
        return self._build_search_snapshot(run_id, ctx)

    def _build_search_snapshot(self, run_id: str, ctx: RunContext) -> RunSnapshot:
        return RunSnapshot(
            runId=run_id,
            mode=ctx.mode,
            stage=ctx.stage,
            summary=ctx.summary,
            searchProfile=ctx.current_profile,
            recommendedProfile=ctx.best_profile,
            metrics=ctx.metrics,
            personas=ctx.personas,
            experiments=ctx.experiments,
            compression=ctx.compression,
            warnings=ctx.warnings,
            startedAt=ctx.started_at,
            completedAt=ctx.completed_at,
        )

    async def get_committee_snapshot(self, run_id: str) -> Optional[CommitteeSnapshot]:
        ctx = self.committee_runs.get(run_id)
        if not ctx:
            return None
        return CommitteeSnapshot(
            runId=run_id,
            stage=ctx.stage,
            summary=ctx.summary,
            document=ctx.best_document if ctx.stage == "completed" else ctx.document,
            personas=ctx.personas,
            rewrites=ctx.rewrites,
            metrics=ctx.metrics,
            evaluationMode=ctx.evaluation_mode,
            warnings=ctx.warnings,
            startedAt=ctx.started_at,
            completedAt=ctx.completed_at,
        )

    async def get_any_snapshot(self, run_id: str) -> Optional[Any]:
        snapshot = await self.get_snapshot(run_id)
        if snapshot is not None:
            return snapshot
        return await self.get_committee_snapshot(run_id)

    async def get_any_run(self, run_id: str) -> Optional[Any]:
        run = await self.get_run(run_id)
        if run is not None:
            return run
        return await self.get_committee_run(run_id)

    async def stop_run(self, run_id: str) -> None:
        ctx = self.runs.get(run_id)
        if ctx:
            ctx.cancel_flag.set()
            ctx.stage = "stopping"
            await self._persist_search_run(run_id)
            await self.publish(
                run_id,
                {
                    "type": "run.stage",
                    "payload": {"runId": run_id, "stage": "stopping"},
                },
            )

    async def stop_committee_run(self, run_id: str) -> None:
        ctx = self.committee_runs.get(run_id)
        if ctx:
            ctx.cancel_flag.set()
            ctx.stage = "stopping"
            await self.publish(
                run_id,
                {
                    "type": "run.stage",
                    "payload": {"runId": run_id, "stage": "stopping"},
                },
            )

    # ------------------------------------------------------------------
    # Pub/Sub
    # ------------------------------------------------------------------

    async def publish(self, run_id: str, event: dict) -> None:
        queues = self.subscribers.get(run_id, set())
        dead: Set[asyncio.Queue] = set()
        for q in list(queues):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead.add(q)
        for q in dead:
            queues.discard(q)

    async def subscribe(self, run_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=512)
        if run_id not in self.subscribers:
            self.subscribers[run_id] = set()
        self.subscribers[run_id].add(q)
        return q

    async def unsubscribe(self, run_id: str, queue: asyncio.Queue) -> None:
        if run_id in self.subscribers:
            self.subscribers[run_id].discard(queue)

    # ------------------------------------------------------------------
    # Task launcher
    # ------------------------------------------------------------------

    async def start_run_tasks(self, run_id: str) -> None:
        """Launch all background tasks for a run."""
        ctx = self.runs.get(run_id)
        if not ctx:
            logger.error("start_run_tasks: run %s not found", run_id)
            return

        if ctx.mode == "demo":
            # Demo mode: just run the demo orchestrator
            from .demo_service import DemoService

            demo_svc = DemoService()
            task = asyncio.create_task(
                demo_svc.run_demo_orchestrator(ctx, self),
                name=f"demo-orchestrator-{run_id}",
            )
            ctx.tasks.append(task)
        else:
            # Live mode: run full optimization pipeline
            optimizer_task = asyncio.create_task(
                self._optimizer_loop(run_id),
                name=f"optimizer-{run_id}",
            )
            persona_task = asyncio.create_task(
                self._persona_simulator_loop(run_id),
                name=f"personas-{run_id}",
            )
            compression_task = asyncio.create_task(
                self._compression_benchmark(run_id),
                name=f"compression-{run_id}",
            )
            metrics_task = asyncio.create_task(
                self._metrics_heartbeat(run_id),
                name=f"metrics-{run_id}",
            )
            ctx.tasks.extend([optimizer_task, persona_task, compression_task, metrics_task])

        # Persona positions remain stable; we no longer run a background orbit loop.

    async def start_committee_run_tasks(self, run_id: str) -> None:
        ctx = self.committee_runs.get(run_id)
        if not ctx:
            logger.error("start_committee_run_tasks: run %s not found", run_id)
            return

        optimizer_task = asyncio.create_task(
            self._committee_optimizer_loop(run_id),
            name=f"committee-optimizer-{run_id}",
        )
        metrics_task = asyncio.create_task(
            self._committee_metrics_heartbeat(run_id),
            name=f"committee-metrics-{run_id}",
        )
        ctx.tasks.extend([optimizer_task, metrics_task])

    # ------------------------------------------------------------------
    # Background tasks (live mode)
    # ------------------------------------------------------------------

    async def _optimizer_loop(self, run_id: str) -> None:
        """Main optimization loop for live mode."""
        ctx = self.runs.get(run_id)
        if not ctx:
            return

        from .es_service import ESService
        from .llm_service import LLMService
        from ..config import settings as cfg

        now_ts = lambda: datetime.now(timezone.utc).isoformat()
        ctx.stage = "running"
        ctx.started_at = now_ts()
        start_time = time.monotonic()

        await self.publish(
            run_id,
            {"type": "run.stage", "payload": {"runId": run_id, "stage": "running"}},
        )

        llm_svc: Optional[LLMService] = None
        if ctx.llm_config and ctx.llm_config.provider != "disabled":
            llm_svc = LLMService(ctx.llm_config)

        plateau_count = 0
        max_plateau = 5
        es_svc: Optional[ESService] = None
        if ctx.es_url:
            es_svc = ESService(es_url=ctx.es_url, api_key=ctx.api_key or None)

        try:
            # Evaluate baseline
            try:
                baseline_score, baseline_failures = await self._evaluate_profile(
                    ctx,
                    ctx.baseline_profile,
                    es_svc=es_svc,
                )
                ctx.metrics.baselineScore = baseline_score
                ctx.metrics.currentScore = baseline_score
                ctx.metrics.bestScore = baseline_score
                ctx._best_score = baseline_score
                ctx._current_query_failures = baseline_failures
            except Exception as exc:
                logger.error("Baseline evaluation failed: %s", exc)
                ctx.warnings.append(f"Baseline evaluation failed: {exc}")
                ctx.metrics.baselineScore = 0.5
                ctx.metrics.currentScore = 0.5
                ctx.metrics.bestScore = 0.5
                ctx._current_query_failures = []

            await self._persist_search_run(run_id)

            for exp_num in range(ctx.max_experiments):
                if ctx.cancel_flag.is_set():
                    break

                elapsed = time.monotonic() - start_time
                if elapsed >= ctx.duration_minutes * 60:
                    logger.info("Run %s reached duration limit", run_id)
                    break

                if ctx.auto_stop_on_plateau and plateau_count >= max_plateau:
                    logger.info("Run %s reached plateau, stopping", run_id)
                    break

                try:
                    change = await self._pick_next_experiment(
                        ctx, llm_svc, exp_num
                    )
                    if not change:
                        await asyncio.sleep(2.0)
                        continue

                    candidate = ctx.current_profile.model_copy(deep=True)
                    _apply_profile_change(candidate, change)

                    t_start = time.monotonic()
                    candidate_score, candidate_failures = await self._evaluate_profile(
                        ctx,
                        candidate,
                        es_svc=es_svc,
                    )
                    duration_ms = int((time.monotonic() - t_start) * 1000)

                    baseline_for_exp = ctx.metrics.currentScore
                    query_failures_before = list(getattr(ctx, "_current_query_failures", []))
                    delta_abs = candidate_score - baseline_for_exp
                    delta_pct = (delta_abs / max(baseline_for_exp, 0.001)) * 100

                    decision: str
                    if delta_abs >= cfg.keep_threshold:
                        decision = "kept"
                        ctx.current_profile = candidate
                        ctx._current_query_failures = candidate_failures
                        if candidate_score > ctx._best_score:
                            ctx._best_score = candidate_score
                            ctx.best_profile = candidate.model_copy(deep=True)
                        plateau_count = 0
                    else:
                        decision = "reverted"
                        plateau_count += 1

                    record = ExperimentRecord(
                        experimentId=exp_num + 1,
                        timestamp=now_ts(),
                        hypothesis=change.label,
                        change=change,
                        baselineScore=baseline_for_exp,
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
                        candidate_score if decision == "kept" else baseline_for_exp
                    )
                    ctx.metrics.bestScore = ctx._best_score
                    ctx.metrics.improvementPct = (
                        (ctx._best_score - ctx.metrics.baselineScore)
                        / max(ctx.metrics.baselineScore, 0.001)
                    ) * 100
                    ctx.metrics.elapsedSeconds = time.monotonic() - start_time
                    if decision == "kept":
                        ctx.metrics.improvementsKept += 1
                    ctx.metrics.scoreTimeline.append(
                        {"t": ctx.metrics.elapsedSeconds, "score": ctx.metrics.currentScore}
                    )

                    await self.publish(
                        run_id,
                        {"type": "experiment.completed", "payload": record.model_dump()},
                    )
                    await self.publish(
                        run_id,
                        {"type": "metrics.tick", "payload": ctx.metrics.model_dump()},
                    )
                    await self._persist_search_run(run_id)

                except asyncio.CancelledError:
                    break
                except Exception as exc:
                    logger.error("Optimizer error at experiment %d: %s", exp_num, exc)
                    await asyncio.sleep(1.0)
        finally:
            if es_svc:
                await es_svc.close()

        # Finalize
        ctx.stage = "completed"
        ctx.completed_at = now_ts()
        ctx.report = ReportService().generate(ctx)
        await self._persist_search_run(run_id)
        if self.persistence and ctx.report:
            await self.persistence.save_report(ctx.report)
        await self.publish(
            run_id,
            {"type": "run.stage", "payload": {"runId": run_id, "stage": "completed"}},
        )

    async def _evaluate_profile(
        self,
        ctx: RunContext,
        profile: SearchProfile,
        es_svc: Optional[Any] = None,
    ) -> Tuple[float, List[str]]:
        """Evaluate a search profile against the eval set, returning nDCG@10 and missed queries."""
        if not ctx.eval_set:
            return 0.5, []

        from .es_service import ESService

        close_after = False
        if es_svc is None:
            if not ctx.es_url or not ctx.index_name:
                return 0.0, [case.query for case in ctx.eval_set]
            es_svc = ESService(es_url=ctx.es_url, api_key=ctx.api_key or None)
            close_after = True

        total_ndcg = 0.0
        evaluated = 0
        missed_queries: List[str] = []

        try:
            for case in ctx.eval_set:
                if not case.relevantDocIds:
                    continue

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
                total_ndcg += ndcg
                evaluated += 1
                if ndcg == 0:
                    missed_queries.append(case.query)
        finally:
            if close_after:
                await es_svc.close()

        return total_ndcg / max(evaluated, 1), missed_queries

    async def _pick_next_experiment(
        self,
        ctx: RunContext,
        llm_svc: Optional[Any],
        exp_num: int,
    ) -> Optional[SearchProfileChange]:
        """Choose the next experiment to run."""
        # Try LLM-guided suggestion first
        if llm_svc and llm_svc.available and exp_num % 3 == 0:
            try:
                suggestion = await llm_svc.suggest_experiment(
                    current_profile=ctx.current_profile.model_dump(),
                    experiment_history=[e.model_dump() for e in ctx.experiments[-5:]],
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

        # Fallback: systematic search space exploration
        return _heuristic_next_experiment(ctx.current_profile, ctx.experiments)

    async def _persona_simulator_loop(self, run_id: str) -> None:
        """Simulate persona search activity for live mode."""
        ctx = self.runs.get(run_id)
        if not ctx:
            return

        rng = random.Random(42)
        now_ts = lambda: datetime.now(timezone.utc).isoformat()

        while not ctx.cancel_flag.is_set() and ctx.stage in ("running", "starting"):
            try:
                # Pick a random batch of personas to "search"
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

                    # Simulate outcome based on current score
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
                    persona.successRate = (persona.successes + persona.partials * 0.5) / max(total, 1)

                # Update aggregate persona success rate
                if ctx.personas:
                    ctx.metrics.personaSuccessRate = sum(
                        p.successRate for p in ctx.personas
                    ) / len(ctx.personas)

                await self.publish(
                    run_id,
                    {
                        "type": "persona.batch",
                        "payload": {
                            "runId": run_id,
                            "personas": [p.model_dump() for p in ctx.personas],
                        },
                    },
                )

                await asyncio.sleep(settings.persona_batch_interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Persona simulator error: %s", exc)
                await asyncio.sleep(2.0)

    async def _persona_animation_loop(self, run_id: str) -> None:
        """Update persona orbital positions for the frontend animation."""
        ctx = self.runs.get(run_id)
        if not ctx:
            return

        now_ts = lambda: datetime.now(timezone.utc).isoformat()
        tick = 0

        while not ctx.cancel_flag.is_set() and ctx.stage not in ("completed", "error"):
            try:
                for p in ctx.personas:
                    p.angle = (p.angle + p.speed) % (2 * math.pi)

                # Publish persona positions every 5 ticks (~2.5s at 500ms interval)
                if tick % 5 == 0 and ctx.stage == "running":
                    await self.publish(
                        run_id,
                        {
                            "type": "persona_positions",
                            "runId": run_id,
                            "positions": [
                                {"id": p.id, "angle": p.angle, "radius": p.radius}
                                for p in ctx.personas
                            ],
                            "ts": now_ts(),
                        },
                    )

                tick += 1
                await asyncio.sleep(0.5)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Persona animation error: %s", exc)
                await asyncio.sleep(1.0)

    async def _compression_benchmark(self, run_id: str) -> None:
        """Simulate compression benchmarking for live mode."""
        ctx = self.runs.get(run_id)
        if not ctx:
            return

        if not ctx.summary.vectorField or not ctx.summary.vectorDims:
            ctx.compression.status = "skipped"
            return

        now_ts = lambda: datetime.now(timezone.utc).isoformat()
        ctx.compression.available = True
        ctx.compression.vectorField = ctx.summary.vectorField
        ctx.compression.vectorDims = ctx.summary.vectorDims
        ctx.compression.status = "running"

        from ..models.contracts import CompressionMethodResult

        # Wait a bit before starting compression benchmark
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
        cost_per_byte_month = settings.cost_per_gb_per_month / (1024 ** 3)

        results = []
        for method_name, size_ratio, recall in methods:
            if ctx.cancel_flag.is_set():
                break

            size_bytes = int(float32_size * size_ratio)
            monthly_cost = size_bytes * cost_per_byte_month
            float32_cost = float32_size * cost_per_byte_month
            size_reduction_pct = (1 - size_ratio) * 100

            results.append(
                CompressionMethodResult(
                    method=method_name,
                    sizeBytes=size_bytes,
                    recallAt10=recall,
                    estimatedMonthlyCostUsd=round(monthly_cost, 2),
                    sizeReductionPct=round(size_reduction_pct, 1),
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

        # Recommend int8 as the best balance
        ctx.compression.bestRecommendation = "int8"
        if results:
            float32_cost = results[0].estimatedMonthlyCostUsd
            int8_result = next((r for r in results if r.method == "int8"), None)
            if int8_result:
                savings = float32_cost - int8_result.estimatedMonthlyCostUsd
                ctx.compression.projectedMonthlySavingsUsd = round(max(savings, 0), 2)
                ctx.metrics.projectedMonthlySavingsUsd = ctx.compression.projectedMonthlySavingsUsd

        await self.publish(
            run_id,
            {
                "type": "compression.updated",
                "payload": ctx.compression.model_dump(),
            },
        )
        await self._persist_search_run(run_id)

    async def _metrics_heartbeat(self, run_id: str) -> None:
        """Periodically publish metrics updates."""
        ctx = self.runs.get(run_id)
        if not ctx:
            return

        now_ts = lambda: datetime.now(timezone.utc).isoformat()
        start_time = time.monotonic()

        while not ctx.cancel_flag.is_set() and ctx.stage in ("running", "starting"):
            try:
                ctx.metrics.elapsedSeconds = time.monotonic() - start_time
                await self.publish(
                    run_id,
                    {
                        "type": "metrics.tick",
                        "payload": ctx.metrics.model_dump(),
                    },
                )
                await asyncio.sleep(settings.metrics_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Metrics heartbeat error: %s", exc)
                await asyncio.sleep(2.0)

    async def _committee_optimizer_loop(self, run_id: str) -> None:
        ctx = self.committee_runs.get(run_id)
        if not ctx:
            return

        from .llm_service import LLMService

        llm_svc: Optional[LLMService] = None
        if ctx.llm_config and ctx.llm_config.provider != "disabled":
            llm_svc = LLMService(ctx.llm_config)

        evaluator = CommitteeEvaluator(ctx.profile, llm_svc, warnings=ctx.warnings)
        rewrite_engine = CommitteeRewriteEngine(ctx.profile, llm_svc, warnings=ctx.warnings)
        now_ts = lambda: datetime.now(timezone.utc).isoformat()

        ctx.stage = "running"
        ctx.started_at = now_ts()
        ctx.started_monotonic = time.monotonic()
        start_time = ctx.started_monotonic

        await self.publish(
            run_id,
            {"type": "run.stage", "payload": {"runId": run_id, "stage": "running"}},
        )

        try:
            ctx.section_evaluations = await evaluator.evaluate_document(
                ctx.persona_definitions,
                ctx.document.sections,
            )
            ctx.personas = _build_committee_persona_views(
                evaluator=evaluator,
                persona_definitions=ctx.persona_definitions,
                sections=ctx.document.sections,
                evaluations=ctx.section_evaluations,
                latest_section_id=None,
            )
            baseline_score = evaluator.consensus_score(ctx.personas, ctx.evaluation_mode)
            ctx.metrics.baselineScore = baseline_score
            ctx.metrics.currentScore = baseline_score
            ctx.metrics.bestScore = baseline_score
            ctx.metrics.scoreTimeline = [ScoreTimelinePoint(t=0.0, score=baseline_score)]
            ctx._best_score = baseline_score
            _update_evaluation_metrics(ctx)
        except Exception as exc:
            logger.error("Committee baseline evaluation failed: %s", exc)
            ctx.warnings.append(f"Baseline evaluation failed: {exc}")
            ctx.metrics.baselineScore = 0.35
            ctx.metrics.currentScore = 0.35
            ctx.metrics.bestScore = 0.35
            ctx.metrics.scoreTimeline = [ScoreTimelinePoint(t=0.0, score=0.35)]
            ctx._best_score = 0.35

        await self.publish(
            run_id,
            {
                "type": "committee.persona.batch",
                "payload": {"runId": run_id, "personas": [persona.model_dump() for persona in ctx.personas]},
            },
        )
        await self.publish(
            run_id,
            {"type": "metrics.tick", "payload": ctx.metrics.model_dump()},
        )

        plateau_count = 0
        parameter_state: Dict[int, Dict[str, str]] = {}
        rng = random.Random(42)

        for exp_num in range(ctx.max_rewrites):
            if ctx.cancel_flag.is_set():
                break

            elapsed = time.monotonic() - start_time
            if elapsed >= ctx.duration_minutes * 60:
                break

            if ctx.auto_stop_on_plateau and plateau_count >= 8:
                break

            try:
                iteration_started = time.monotonic()
                section = rng.choice(ctx.document.sections)
                proposal = await rewrite_engine.propose(section, parameter_state, rng)
                baseline_for_exp = ctx.metrics.currentScore
                before_text = section.content

                candidate_sections = list(ctx.document.sections)
                updated_section = section.model_copy(update={"content": proposal.rewritten_text})
                candidate_sections = [
                    updated_section if item.id == section.id else item
                    for item in candidate_sections
                ]

                eval_start = time.monotonic()
                candidate_evaluations = dict(ctx.section_evaluations)
                for persona in ctx.persona_definitions:
                    candidate_evaluations[(section.id, persona.id)] = await evaluator.evaluate_section(
                        persona,
                        updated_section,
                    )

                candidate_personas = _build_committee_persona_views(
                    evaluator=evaluator,
                    persona_definitions=ctx.persona_definitions,
                    sections=candidate_sections,
                    evaluations=candidate_evaluations,
                    latest_section_id=section.id,
                )
                candidate_score = evaluator.consensus_score(candidate_personas, ctx.evaluation_mode)
                duration_ms = int((time.monotonic() - eval_start) * 1000)

                persona_deltas = {
                    candidate.id: round(candidate.currentScore - current.currentScore, 4)
                    for candidate, current in zip(candidate_personas, ctx.personas)
                }
                worst_drop = min(persona_deltas.values()) if persona_deltas else 0.0
                do_no_harm = worst_drop >= ctx.do_no_harm_floor

                if candidate_score > baseline_for_exp and do_no_harm:
                    decision = "kept"
                    _commit_committee_candidate(
                        ctx,
                        candidate_sections=candidate_sections,
                        candidate_evaluations=candidate_evaluations,
                        candidate_personas=candidate_personas,
                    )
                    parameter_state.setdefault(section.id, {})[proposal.parameter_name] = proposal.new_value
                    plateau_count = 0
                    if candidate_score >= ctx._best_score:
                        ctx._best_score = candidate_score
                        ctx.best_document = ctx.document.model_copy(deep=True)
                else:
                    decision = "reverted"
                    plateau_count += 1

                delta_abs = candidate_score - baseline_for_exp
                delta_pct = (delta_abs / max(baseline_for_exp, 0.001)) * 100
                record = RewriteAttempt(
                    experimentId=exp_num + 1,
                    timestamp=now_ts(),
                    sectionId=section.id,
                    sectionTitle=section.title,
                    parameterName=proposal.parameter_name,
                    oldValue=proposal.old_value,
                    newValue=proposal.new_value,
                    description=proposal.description,
                    baselineScore=round(baseline_for_exp, 4),
                    candidateScore=round(candidate_score, 4),
                    deltaAbsolute=round(delta_abs, 4),
                    deltaPercent=round(delta_pct, 2),
                    decision=decision,
                    doNoHarmSatisfied=do_no_harm,
                    worstPersonaDrop=round(worst_drop, 4),
                    beforeText=before_text,
                    afterText=proposal.rewritten_text,
                    personaDeltas=persona_deltas,
                    durationMs=duration_ms,
                )
                ctx.rewrites.append(record)

                ctx.metrics.rewritesTested = exp_num + 1
                ctx.metrics.currentScore = candidate_score if decision == "kept" else baseline_for_exp
                ctx.metrics.bestScore = ctx._best_score
                if decision == "kept":
                    ctx.metrics.acceptedRewrites += 1
                ctx.metrics.elapsedSeconds = time.monotonic() - start_time
                ctx.metrics.currentSectionId = section.id
                ctx.metrics.currentSectionTitle = section.title
                if ctx.metrics.baselineScore > 0:
                    ctx.metrics.improvementPct = round(
                        ((ctx._best_score - ctx.metrics.baselineScore) / ctx.metrics.baselineScore) * 100,
                        2,
                    )
                ctx.metrics.scoreTimeline.append(
                    ScoreTimelinePoint(t=ctx.metrics.elapsedSeconds, score=ctx.metrics.currentScore)
                )
                _update_evaluation_metrics(ctx)

                await self.publish(
                    run_id,
                    {"type": "rewrite.completed", "payload": record.model_dump()},
                )
                await self.publish(
                    run_id,
                    {
                        "type": "committee.persona.batch",
                        "payload": {
                            "runId": run_id,
                            "personas": [persona.model_dump() for persona in ctx.personas],
                        },
                    },
                )
                await self.publish(
                    run_id,
                    {"type": "metrics.tick", "payload": ctx.metrics.model_dump()},
                )

                min_iteration_seconds = 0.85
                remaining = min_iteration_seconds - (time.monotonic() - iteration_started)
                if remaining > 0 and not ctx.cancel_flag.is_set():
                    await asyncio.sleep(remaining)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Committee optimizer error at rewrite %d: %s", exp_num, exc)
                await asyncio.sleep(1.0)

        if ctx.started_monotonic is not None:
            ctx.metrics.elapsedSeconds = time.monotonic() - ctx.started_monotonic

        ctx.stage = "completed"
        ctx.completed_at = now_ts()
        ctx.report = build_report(ctx)
        await self.publish(
            run_id,
            {"type": "metrics.tick", "payload": ctx.metrics.model_dump()},
        )
        await self.publish(
            run_id,
            {"type": "committee.report.ready", "payload": ctx.report.model_dump()},
        )
        await self.publish(
            run_id,
            {"type": "run.stage", "payload": {"runId": run_id, "stage": "completed"}},
        )

    async def _committee_metrics_heartbeat(self, run_id: str) -> None:
        ctx = self.committee_runs.get(run_id)
        if not ctx:
            return

        while not ctx.cancel_flag.is_set():
            try:
                if ctx.started_monotonic is not None and ctx.stage in ("running", "starting", "stopping"):
                    ctx.metrics.elapsedSeconds = time.monotonic() - ctx.started_monotonic
                    await self.publish(
                        run_id,
                        {"type": "metrics.tick", "payload": ctx.metrics.model_dump()},
                    )

                if ctx.stage in ("completed", "error"):
                    break

                await asyncio.sleep(1.0)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Committee metrics heartbeat error: %s", exc)
                await asyncio.sleep(1.0)

    async def get_committee_export(self, run_id: str) -> Optional[dict]:
        ctx = self.committee_runs.get(run_id)
        if not ctx:
            return None
        return build_export_payload(ctx).model_dump()

    async def get_report(self, run_id: str) -> Optional[ReportPayload]:
        ctx = self.runs.get(run_id)
        if ctx and ctx.report:
            return ctx.report
        if self.persistence:
            return await self.persistence.load_report(run_id)
        return None

    async def list_search_runs(self, limit: int = 50) -> List[Dict[str, Any]]:
        if not self.persistence:
            return []
        return await self.persistence.list_runs(limit=limit)

    async def _persist_search_run(self, run_id: str) -> None:
        if not self.persistence:
            return
        ctx = self.runs.get(run_id)
        if not ctx:
            return
        await self.persistence.save_snapshot(self._build_search_snapshot(run_id, ctx))

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_committee_persona_views(
    evaluator: CommitteeEvaluator,
    persona_definitions: List[Any],
    sections: List[Any],
    evaluations: Dict[tuple[int, str], Any],
    latest_section_id: Optional[int],
) -> List[CommitteePersonaView]:
    return [
        evaluator.rollup_persona_view(
            persona=persona,
            sections=sections,
            evaluations=evaluations,
            latest_section_id=latest_section_id,
        )
        for persona in persona_definitions
    ]


def _update_evaluation_metrics(ctx: CommitteeRunContext) -> None:
    evaluations = list(ctx.section_evaluations.values())
    ai_evaluations = sum(1 for evaluation in evaluations if evaluation.source == "llm")
    heuristic_evaluations = sum(1 for evaluation in evaluations if evaluation.source == "heuristic")
    total = ai_evaluations + heuristic_evaluations
    ctx.metrics.aiEvaluations = ai_evaluations
    ctx.metrics.heuristicEvaluations = heuristic_evaluations
    ctx.metrics.llmCoveragePct = round((ai_evaluations / total) * 100, 1) if total else 0.0


def _commit_committee_candidate(
    ctx: CommitteeRunContext,
    *,
    candidate_sections: List[Any],
    candidate_evaluations: Dict[Tuple[int, str], Any],
    candidate_personas: List[CommitteePersonaView],
) -> None:
    ctx.document = ctx.document.model_copy(update={"sections": candidate_sections})
    ctx.section_evaluations = candidate_evaluations
    ctx.personas = candidate_personas

def _apply_profile_change(profile: SearchProfile, change: SearchProfileChange) -> None:
    """Apply a SearchProfileChange to a SearchProfile in-place."""
    try:
        if hasattr(profile, change.path):
            setattr(profile, change.path, change.after)
    except Exception as exc:
        logger.warning("Failed to apply change %s=%r: %s", change.path, change.after, exc)


# Search space for heuristic experiments
_SEARCH_SPACE: List[Dict[str, Any]] = [
    {"path": "minimumShouldMatch", "values": ["50%", "60%", "70%", "75%", "80%", "85%", "90%"]},
    {"path": "tieBreaker", "values": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]},
    {"path": "phraseBoost", "values": [0.0, 0.5, 1.0, 1.5, 2.0, 3.0]},
    {"path": "multiMatchType", "values": ["best_fields", "most_fields", "cross_fields", "phrase"]},
    {"path": "fuzziness", "values": ["0", "AUTO"]},
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


def _heuristic_next_experiment(
    profile: SearchProfile, history: List[ExperimentRecord]
) -> Optional[SearchProfileChange]:
    """Pick the next experiment from a systematic search space grid."""
    tried: Dict[str, set] = {}
    for exp in history:
        path = exp.change.path
        if path not in tried:
            tried[path] = set()
        tried[path].add(str(exp.change.after))

    rng = random.Random(len(history))
    # Shuffle to avoid always trying the same field
    space = list(_SEARCH_SPACE)
    rng.shuffle(space)

    for item in space:
        path = item["path"]
        current_val = getattr(profile, path, None)
        tried_vals = tried.get(path, set())

        for val in item["values"]:
            if str(val) not in tried_vals and val != current_val:
                label = f"{_FIELD_LABELS.get(path, path)} {current_val!r} → {val!r}"
                return SearchProfileChange(
                    path=path,
                    before=current_val,
                    after=val,
                    label=label,
                )

    return None
