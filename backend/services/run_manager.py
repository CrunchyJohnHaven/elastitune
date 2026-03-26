from __future__ import annotations

import asyncio
from collections import deque
import logging
import random
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple


from ..models.contracts import (
    ConnectionSummary,
    EvalCase,
    ExperimentRecord,
    LlmConfig,
    RunSnapshot,
    SearchProfile,
    SearchProfileChange,
)
from ..models.runtime import ConnectionContext, RunContext
from ..models.report import ReportPayload
from ..committee.evaluator import CommitteeEvaluator
from ..committee.models import (
    CommitteeSnapshot,
    CommitteePersonaView,
    RewriteAttempt,
    ScoreTimelinePoint,
)
from ..committee.reporting import build_export_payload, build_report
from ..committee.rewrite_engine import BASE_PARAMETER_VALUES, CommitteeRewriteEngine
from ..committee.runtime import CommitteeConnectionContext, CommitteeRunContext
from ..engine.optimizer_search_space import generate_security_field_mutations
from .persistence_service import PersistenceService
from .task_runner import SearchTaskRunner

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
        self.search_task_runner = SearchTaskRunner(self)

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    async def create_connection(
        self, connection_id: str, ctx: ConnectionContext
    ) -> None:
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
                    "llm_config": ctx.llm_config.model_dump()
                    if ctx.llm_config
                    else None,
                    "text_fields": ctx.text_fields,
                    "sample_docs": ctx.sample_docs,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )

    async def get_connection(self, connection_id: str) -> Optional[ConnectionContext]:
        ctx = self.connections.get(connection_id)
        if ctx is not None:
            return ctx
        if not self.persistence:
            return None

        payload = await self.persistence.load_connection(connection_id)
        if not payload:
            return None

        restored = ConnectionContext(
            connection_id=payload["connection_id"],
            mode=payload["mode"],
            summary=ConnectionSummary.model_validate(payload["summary"]),
            eval_set=[
                EvalCase.model_validate(case) for case in payload.get("eval_set", [])
            ],
            baseline_profile=SearchProfile.model_validate(payload["baseline_profile"]),
            llm_config=LlmConfig.model_validate(payload["llm_config"])
            if payload.get("llm_config")
            else None,
            es_url=payload.get("es_url"),
            api_key=payload.get("api_key"),
            index_name=payload.get("index_name"),
            text_fields=payload.get("text_fields"),
            sample_docs=payload.get("sample_docs"),
        )
        self.connections[connection_id] = restored
        return restored

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
            runConfig={
                "durationMinutes": ctx.duration_minutes,
                "maxExperiments": ctx.max_experiments,
                "personaCount": len(ctx.personas),
                "autoStopOnPlateau": ctx.auto_stop_on_plateau,
            },
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
                self.search_task_runner.optimizer_loop(run_id),
                name=f"optimizer-{run_id}",
            )
            persona_task = asyncio.create_task(
                self.search_task_runner.persona_simulator_loop(run_id),
                name=f"personas-{run_id}",
            )
            compression_task = asyncio.create_task(
                self.search_task_runner.compression_benchmark(run_id),
                name=f"compression-{run_id}",
            )
            metrics_task = asyncio.create_task(
                self.search_task_runner.metrics_heartbeat(run_id),
                name=f"metrics-{run_id}",
            )
            ctx.tasks.extend(
                [optimizer_task, persona_task, compression_task, metrics_task]
            )

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
        await self.search_task_runner.optimizer_loop(run_id)

    async def _evaluate_profile(
        self,
        ctx: RunContext,
        profile: SearchProfile,
        es_svc: Optional[Any] = None,
    ) -> Tuple[float, List[str], Dict[str, float]]:
        """Evaluate a search profile against the eval set, returning (nDCG@10, missed queries, per-query scores)."""
        return await self.search_task_runner.evaluate_profile(
            ctx,
            profile,
            es_svc=es_svc,
        )

    async def evaluate_detailed(
        self,
        ctx: RunContext,
        profile: SearchProfile,
        es_svc: Optional[Any] = None,
    ) -> Tuple[float, List[str], Dict[str, float]]:
        return await self.search_task_runner.evaluate_detailed(
            ctx,
            profile,
            es_svc=es_svc,
        )

    async def _collect_query_result_previews(
        self,
        ctx: RunContext,
        profile: SearchProfile,
        es_svc: Optional[Any] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        return await self.search_task_runner.collect_query_result_previews(
            ctx,
            profile,
            es_svc=es_svc,
        )

    async def _pick_next_experiment(
        self,
        ctx: RunContext,
        llm_svc: Optional[Any],
        exp_num: int,
    ) -> Optional[SearchProfileChange]:
        return await self.search_task_runner._pick_next_experiment(
            ctx,
            llm_svc,
            exp_num,
        )

    async def _persona_simulator_loop(self, run_id: str) -> None:
        await self.search_task_runner.persona_simulator_loop(run_id)

    async def _compression_benchmark(self, run_id: str) -> None:
        await self.search_task_runner.compression_benchmark(run_id)

    async def _metrics_heartbeat(self, run_id: str) -> None:
        await self.search_task_runner.metrics_heartbeat(run_id)

    async def _committee_optimizer_loop(self, run_id: str) -> None:
        ctx = self.committee_runs.get(run_id)
        if not ctx:
            return

        from .llm_service import LLMService

        llm_svc: Optional[LLMService] = None
        if ctx.llm_config and ctx.llm_config.provider != "disabled":
            llm_svc = LLMService(ctx.llm_config)

        evaluator = CommitteeEvaluator(
            ctx.profile,
            llm_svc,
            warnings=ctx.warnings,
            thresholds=ctx.score_thresholds,
        )
        rewrite_engine = CommitteeRewriteEngine(
            ctx.profile, llm_svc, warnings=ctx.warnings
        )

        def now_ts() -> str:
            return datetime.now(timezone.utc).isoformat()

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
            baseline_score = evaluator.consensus_score(
                ctx.personas, ctx.evaluation_mode
            )
            ctx.metrics.baselineScore = baseline_score
            ctx.metrics.currentScore = baseline_score
            ctx.metrics.bestScore = baseline_score
            ctx.metrics.scoreTimeline = [
                ScoreTimelinePoint(t=0.0, score=baseline_score)
            ]
            ctx.best_score = baseline_score
            _update_evaluation_metrics(ctx)
        except Exception as exc:
            logger.error("Committee baseline evaluation failed: %s", exc)
            ctx.warnings.append(f"Baseline evaluation failed: {exc}")
            ctx.metrics.baselineScore = 0.35
            ctx.metrics.currentScore = 0.35
            ctx.metrics.bestScore = 0.35
            ctx.metrics.scoreTimeline = [ScoreTimelinePoint(t=0.0, score=0.35)]
            ctx.best_score = 0.35

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

        parameter_state: Dict[int, Dict[str, str]] = {}
        parameter_history: Dict[str, deque[float]] = {
            name: deque(maxlen=6)
            for name in {**BASE_PARAMETER_VALUES, **ctx.profile.parameter_values}
        }
        plateau_window: deque[tuple[float, str]] = deque(maxlen=12)
        rng = random.Random(42)

        for exp_num in range(ctx.max_rewrites):
            if ctx.cancel_flag.is_set():
                break

            elapsed = time.monotonic() - start_time
            if elapsed >= ctx.duration_minutes * 60:
                break

            if ctx.auto_stop_on_plateau and _committee_plateau_reached(plateau_window):
                break

            try:
                iteration_started = time.monotonic()
                section = _select_committee_section(ctx, rng)
                parameter_name = _select_committee_parameter(parameter_history, rng)
                proposal = await rewrite_engine.propose(
                    section,
                    parameter_state,
                    rng,
                    parameter_name=parameter_name,
                )
                baseline_for_exp = ctx.metrics.currentScore
                before_text = section.content

                candidate_sections = list(ctx.document.sections)
                updated_section = section.model_copy(
                    update={"content": proposal.rewritten_text}
                )
                candidate_sections = [
                    updated_section if item.id == section.id else item
                    for item in candidate_sections
                ]

                eval_start = time.monotonic()
                candidate_evaluations = dict(ctx.section_evaluations)
                for persona in ctx.persona_definitions:
                    candidate_evaluations[
                        (section.id, persona.id)
                    ] = await evaluator.evaluate_section(
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
                candidate_score = evaluator.consensus_score(
                    candidate_personas, ctx.evaluation_mode
                )
                duration_ms = int((time.monotonic() - eval_start) * 1000)

                current_persona_map = {persona.id: persona for persona in ctx.personas}
                persona_deltas = {
                    candidate.id: round(
                        candidate.currentScore
                        - current_persona_map[candidate.id].currentScore,
                        4,
                    )
                    for candidate in candidate_personas
                    if candidate.id in current_persona_map
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
                    parameter_state.setdefault(section.id, {})[
                        proposal.parameter_name
                    ] = proposal.new_value
                    if candidate_score >= ctx.best_score:
                        ctx.best_score = candidate_score
                        ctx.best_document = ctx.document.model_copy(deep=True)
                else:
                    decision = "reverted"

                delta_abs = candidate_score - baseline_for_exp
                delta_pct = (delta_abs / max(baseline_for_exp, 0.001)) * 100
                parameter_history.setdefault(
                    proposal.parameter_name, deque(maxlen=6)
                ).append(delta_abs)
                plateau_window.append((ctx.best_score, proposal.parameter_name))
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
                ctx.metrics.currentScore = (
                    candidate_score if decision == "kept" else baseline_for_exp
                )
                ctx.metrics.bestScore = ctx.best_score
                if decision == "kept":
                    ctx.metrics.acceptedRewrites += 1
                ctx.metrics.elapsedSeconds = time.monotonic() - start_time
                ctx.metrics.currentSectionId = section.id
                ctx.metrics.currentSectionTitle = section.title
                if ctx.metrics.baselineScore > 0:
                    ctx.metrics.improvementPct = round(
                        (
                            (ctx.best_score - ctx.metrics.baselineScore)
                            / ctx.metrics.baselineScore
                        )
                        * 100,
                        2,
                    )
                ctx.metrics.scoreTimeline.append(
                    ScoreTimelinePoint(
                        t=ctx.metrics.elapsedSeconds, score=ctx.metrics.currentScore
                    )
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
                            "personas": [
                                persona.model_dump() for persona in ctx.personas
                            ],
                        },
                    },
                )
                await self.publish(
                    run_id,
                    {"type": "metrics.tick", "payload": ctx.metrics.model_dump()},
                )

                min_iteration_seconds = 0.85
                remaining = min_iteration_seconds - (
                    time.monotonic() - iteration_started
                )
                if remaining > 0 and not ctx.cancel_flag.is_set():
                    await asyncio.sleep(remaining)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(
                    "Committee optimizer error at rewrite %d: %s", exp_num, exc
                )
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
                if ctx.started_monotonic is not None and ctx.stage in (
                    "running",
                    "starting",
                    "stopping",
                ):
                    ctx.metrics.elapsedSeconds = (
                        time.monotonic() - ctx.started_monotonic
                    )
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

    async def list_search_runs(
        self,
        limit: int = 50,
        index_name: Optional[str] = None,
        completed_only: bool = False,
    ) -> List[Dict[str, Any]]:
        if not self.persistence:
            return []
        return await self.persistence.list_runs(
            limit=limit,
            index_name=index_name,
            completed_only=completed_only,
        )

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
        return self.search_task_runner._compute_ndcg_at_k(
            relevant_doc_ids,
            ranked_doc_ids,
            k=k,
        )


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
    heuristic_evaluations = sum(
        1 for evaluation in evaluations if evaluation.source == "heuristic"
    )
    total = ai_evaluations + heuristic_evaluations
    ctx.metrics.aiEvaluations = ai_evaluations
    ctx.metrics.heuristicEvaluations = heuristic_evaluations
    ctx.metrics.llmCoveragePct = (
        round((ai_evaluations / total) * 100, 1) if total else 0.0
    )


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


def _select_committee_section(ctx: CommitteeRunContext, rng: random.Random) -> Any:
    section_scores: Dict[int, float] = {}
    if ctx.personas:
        for persona in ctx.personas:
            for rollup in persona.perSection:
                section_scores.setdefault(rollup.sectionId, 0.0)
                section_scores[rollup.sectionId] += rollup.compositeScore
        persona_count = max(len(ctx.personas), 1)
        section_scores = {
            section_id: total / persona_count
            for section_id, total in section_scores.items()
        }

    weighted_sections = []
    for section in ctx.document.sections:
        avg_score = section_scores.get(section.id, 0.5)
        content_weight = min(max(len(section.content), 120), 900) / 900
        score_room = max(0.08, 1.08 - avg_score)
        weight = score_room * (1.0 + content_weight * 0.45)
        weighted_sections.append((section, weight))

    total_weight = sum(weight for _, weight in weighted_sections) or 1.0
    pick = rng.random() * total_weight
    running = 0.0
    for section, weight in weighted_sections:
        running += weight
        if pick <= running:
            return section
    return ctx.document.sections[-1]


def _select_committee_parameter(
    parameter_history: Dict[str, deque[float]], rng: random.Random
) -> str:
    weighted_parameters = []
    for name, history in parameter_history.items():
        if not history:
            weight = 1.2
        else:
            average_delta = sum(history) / len(history)
            positive_hits = sum(1 for delta in history if delta > 0)
            recent_negative_streak = len(history) >= 3 and all(
                delta <= 0 for delta in list(history)[-3:]
            )
            weight = 1.0 + max(average_delta, 0.0) * 24 + positive_hits * 0.45
            if recent_negative_streak:
                weight *= 0.55
        weighted_parameters.append((name, max(weight, 0.2)))

    total_weight = sum(weight for _, weight in weighted_parameters) or 1.0
    pick = rng.random() * total_weight
    running = 0.0
    for name, weight in weighted_parameters:
        running += weight
        if pick <= running:
            return name
    return weighted_parameters[-1][0]


def _committee_plateau_reached(window: deque[tuple[float, str]]) -> bool:
    if len(window) < window.maxlen:
        return False
    scores = [item[0] for item in window]
    parameters = {item[1] for item in window}
    return (max(scores) - min(scores)) < 0.003 and len(parameters) >= 3


def _apply_profile_change(profile: SearchProfile, change: SearchProfileChange) -> None:
    """Apply a SearchProfileChange to a SearchProfile in-place."""
    import re as _re

    try:
        # Handle field boost paths like "lexicalFields[0].boost"
        m = _re.match(r"lexicalFields\[(\d+)\]\.boost", change.path)
        if m:
            idx = int(m.group(1))
            if idx < len(profile.lexicalFields):
                profile.lexicalFields[idx] = profile.lexicalFields[idx].model_copy(
                    update={"boost": change.after}
                )
            return
        if hasattr(profile, change.path):
            setattr(profile, change.path, change.after)
    except Exception as exc:
        logger.warning(
            "Failed to apply change %s=%r: %s", change.path, change.after, exc
        )


# ---------------------------------------------------------------------------
# Search space definitions
# ---------------------------------------------------------------------------

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

# Continuous ranges for random perturbation (phase 2+)
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
    """
    Multi-phase experiment generator — never runs out of ideas.

    Phase 1 (grid sweep):  Systematic grid search of all single-param values.
    Phase 2 (random perturbation):  Random single-param jitter around current best.
    Phase 3 (multi-param combos):  Simultaneous 2-param random mutations.
    Phases 2 & 3 alternate forever — the optimizer can think for as long as you let it.
    """
    tried: Dict[str, set] = {}
    for exp in history:
        path = exp.change.path
        if path not in tried:
            tried[path] = set()
        tried[path].add(str(exp.change.after))

    n = len(history)
    rng = random.Random(n)

    # ------------------------------------------------------------------
    # Phase 1: grid sweep (first pass over all discrete values)
    # ------------------------------------------------------------------
    grid_result = _grid_sweep(profile, tried, rng)
    if grid_result is not None:
        return grid_result

    # ------------------------------------------------------------------
    # Phase 2+: random perturbation — never exhausts
    # ------------------------------------------------------------------
    return _random_perturbation(profile, history, rng)


def _grid_sweep(
    profile: SearchProfile,
    tried: Dict[str, set],
    rng: random.Random,
) -> Optional[SearchProfileChange]:
    """Phase 1: systematic grid search of all values."""
    security_candidates = generate_security_field_mutations(profile)
    rng.shuffle(security_candidates)
    for candidate in security_candidates:
        if str(candidate.after) not in tried.get(candidate.path, set()):
            return candidate

    space = list(_GRID_LEXICAL)
    if profile.useVector:
        space.extend(_GRID_VECTOR)

    for i, field_entry in enumerate(profile.lexicalFields):
        boost_path = f"lexicalFields[{i}].boost"
        space.append(
            {
                "path": boost_path,
                "values": _BOOST_VALUES,
                "_field_index": i,
                "_field_name": field_entry.get("field", f"field_{i}"),
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
            for val in item["values"]:
                if str(val) not in tried_vals and val != current_val:
                    return SearchProfileChange(
                        path=path,
                        before=current_val,
                        after=val,
                        label=f"{field_name} boost {current_val} → {val}",
                    )
        else:
            current_val = getattr(profile, path, None)
            for val in item["values"]:
                if str(val) not in tried_vals and val != current_val:
                    return SearchProfileChange(
                        path=path,
                        before=current_val,
                        after=val,
                        label=f"{_FIELD_LABELS.get(path, path)} {current_val!r} → {val!r}",
                    )
    return None


def _random_perturbation(
    profile: SearchProfile,
    history: List[ExperimentRecord],
    rng: random.Random,
) -> SearchProfileChange:
    """
    Phase 2+: random perturbation around the current profile.
    Never returns None — can always generate a new experiment.
    """
    n = len(history)

    # Alternate between single-param and multi-param mutations
    reverted_signatures = {
        (exp.change.path, str(exp.change.after))
        for exp in history
        if exp.decision == "reverted"
    }

    if n % 5 < 3:
        # Single-param random jitter
        return _single_random_mutation(profile, reverted_signatures, rng)
    else:
        # Multi-param combo: apply 2 random changes at once (reported as one)
        return _combo_mutation(profile, reverted_signatures, rng)


def _single_random_mutation(
    profile: SearchProfile,
    reverted_signatures: set[tuple[str, str]],
    rng: random.Random,
) -> SearchProfileChange:
    """Randomly perturb one parameter."""
    # Collect all possible mutation targets
    candidates: List[SearchProfileChange] = []

    # Field boosts: jitter current value by ±0.25 to ±2.0
    for i, field_entry in enumerate(profile.lexicalFields):
        current = field_entry["boost"]
        delta = rng.choice([-2.0, -1.0, -0.5, -0.25, 0.25, 0.5, 1.0, 2.0])
        new_val = round(max(0.1, min(10.0, current + delta)), 2)
        if new_val != current:
            candidates.append(
                SearchProfileChange(
                    path=f"lexicalFields[{i}].boost",
                    before=current,
                    after=new_val,
                    label=f"{field_entry.get('field', f'field_{i}')} boost {current} → {new_val}",
                )
            )

    # Continuous params
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

    # Discrete params
    for param in _DISCRETE_PARAMS:
        current = getattr(profile, param["path"], None)
        other_vals = [v for v in param["values"] if v != current]
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

    # Vector params (if enabled)
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
                other_vals = [v for v in param["values"] if v != current]
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
            elif "min" in param:
                current = getattr(profile, param["path"], param["min"])
                step = param.get("step", 1)
                possible = list(range(param["min"], param["max"] + 1, step))
                other_vals = [v for v in possible if v != current]
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

    filtered_candidates = [
        candidate
        for candidate in candidates
        if (candidate.path, str(candidate.after)) not in reverted_signatures
    ]
    if filtered_candidates:
        return rng.choice(filtered_candidates)
    if candidates:
        return rng.choice(candidates)

    # Absolute fallback: flip fuzziness
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
    """
    Aggressive random mutation — bigger swings to explore distant regions
    of the search space. Uses wider ranges than the gentle single-param jitter.
    """
    candidates: List[SearchProfileChange] = []

    # Big field boost swings
    for i, field_entry in enumerate(profile.lexicalFields):
        current = field_entry["boost"]
        # Try values far from current
        new_val = round(rng.uniform(0.1, 8.0), 1)
        if abs(new_val - current) > 0.5:
            candidates.append(
                SearchProfileChange(
                    path=f"lexicalFields[{i}].boost",
                    before=current,
                    after=new_val,
                    label=f"{field_entry.get('field', f'field_{i}')} boost {current} → {new_val} (explore)",
                )
            )

    # Wide tie_breaker sweep
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

    # Wide phrase boost sweep
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

    # Random minimumShouldMatch
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
    other_msm = [v for v in all_msm if v != current_msm]
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

    filtered_candidates = [
        candidate
        for candidate in candidates
        if (candidate.path, str(candidate.after)) not in reverted_signatures
    ]
    if filtered_candidates:
        return rng.choice(filtered_candidates)
    if candidates:
        return rng.choice(candidates)

    return _single_random_mutation(profile, reverted_signatures, rng)


def _hypothesis_text(change: SearchProfileChange) -> str:
    path = change.path
    before = change.before
    after = change.after

    if path.startswith("lexicalFields[") and "boost" in path:
        field_name = change.label.split(" boost", 1)[0]
        if isinstance(before, (int, float)) and isinstance(after, (int, float)):
            if after > before:
                return f"Increase {field_name} influence so stronger {field_name} matches rise earlier in the ranking."
            return f"Reduce {field_name} influence to let other fields carry more of the ranking signal."

    if path == "multiMatchType":
        descriptions = {
            "cross_fields": "Treat terms as shared across fields so fragmented matches can still rank well.",
            "most_fields": "Reward documents that match across many fields rather than one dominant field.",
            "phrase": "Favor ordered phrase matches when exact wording should matter most.",
            "best_fields": "Bias toward the single strongest field match to sharpen precision.",
        }
        return descriptions.get(
            str(after),
            f"Change the multi-match strategy to {after} and measure the ranking tradeoff.",
        )

    if path == "minimumShouldMatch":
        try:
            before_pct = int(str(before).replace("%", ""))
            after_pct = int(str(after).replace("%", ""))
            if after_pct > before_pct:
                return "Tighten term matching so weaker partial matches fall away and exact intent carries more weight."
            return "Relax term matching so the engine can recover relevant documents that only match part of the query."
        except Exception:
            return (
                "Adjust term-matching strictness to rebalance recall versus precision."
            )

    if path == "phraseBoost":
        if isinstance(before, (int, float)) and isinstance(after, (int, float)):
            if after > before:
                return "Reward exact phrase matches more strongly when users search with high-intent wording."
            return "Reduce phrase strictness so near-matches are less likely to be over-penalized."

    if path == "fuzziness":
        if str(after) == "AUTO":
            return "Allow tolerant matching so typos, variants, and inflections still surface relevant results."
        return "Turn off fuzzy matching to sharpen exact lexical precision and reduce noisy recall."

    if path == "tieBreaker":
        return "Rebalance how much supporting field matches contribute once one field already matches strongly."

    if path == "vectorWeight":
        if (
            isinstance(before, (int, float))
            and isinstance(after, (int, float))
            and after > before
        ):
            return "Lean harder on semantic similarity to catch concept matches beyond exact wording."
        return "Pull ranking back toward lexical evidence so exact field matches dominate over semantic recall."

    if path == "fusionMethod":
        if str(after) == "rrf":
            return "Switch to reciprocal-rank fusion to blend lexical and vector rankings more conservatively."
        return "Use weighted-score fusion to let relative relevance scores drive the blend directly."

    if path == "rrfRankConstant":
        return "Adjust how aggressively reciprocal-rank fusion rewards higher-ranked documents from each retriever."

    if path == "knnK":
        return "Widen the semantic candidate set to see whether more vector neighbors improve final recall."

    return f"Test whether changing {path} from {before} to {after} improves ranked relevance without hurting the broader query set."
