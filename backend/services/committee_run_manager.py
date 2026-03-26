from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime, timezone
import logging
import random
import time
from typing import Any, Dict, List, Optional, Tuple

from ..committee.evaluator import CommitteeEvaluator
from ..committee.models import (
    CommitteeConnectionResponse,
    CommitteeExportPayload,
    CommitteePersona,
    CommitteePersonaView,
    CommitteeReport,
    CommitteeSnapshot,
    RewriteAttempt,
    ScoreTimelinePoint,
)
from ..committee.reporting import build_export_payload, build_report_async
from ..committee.rewrite_engine import BASE_PARAMETER_VALUES, CommitteeRewriteEngine
from ..committee.runtime import CommitteeConnectionContext, CommitteeRunContext
from ..config import settings
from ..models.contracts import LlmConfig
from .persistence_service import PersistenceService
from .run_pubsub import RunPubSub

logger = logging.getLogger(__name__)


class CommitteeRunManager:
    def __init__(
        self,
        *,
        pubsub: RunPubSub,
        persistence: Optional[PersistenceService] = None,
    ) -> None:
        self.pubsub = pubsub
        self.persistence = persistence
        self.connections: Dict[str, CommitteeConnectionContext] = {}
        self.runs: Dict[str, CommitteeRunContext] = {}

    async def publish(self, run_id: str, event: dict[str, Any]) -> None:
        await self.pubsub.publish(run_id, event)

    async def publish_error(
        self,
        run_id: str,
        *,
        code: str,
        message: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        await self.pubsub.publish_error(
            run_id,
            code=code,
            message=message,
            details=details,
        )

    async def create_connection(
        self,
        connection_id: str,
        ctx: CommitteeConnectionContext,
    ) -> None:
        self.connections[connection_id] = ctx
        if self.persistence and settings.committee_persistence_enabled:
            await self.persistence.save_committee_connection(
                {
                    "connection_id": connection_id,
                    "summary": ctx.summary.model_dump(),
                    "document": _sanitize_committee_document(ctx.document),
                    "personas": [persona.model_dump() for persona in ctx.personas],
                    "profile": {
                        "id": ctx.profile.id,
                        "label": ctx.profile.label,
                    },
                    "evaluation_mode": ctx.evaluation_mode,
                    "llm_config": ctx.llm_config.model_dump()
                    if ctx.llm_config
                    else None,
                    "warnings": ctx.warnings,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )

    async def get_connection(
        self,
        connection_id: str,
    ) -> Optional[CommitteeConnectionContext]:
        ctx = self.connections.get(connection_id)
        if ctx is not None:
            return ctx
        if not self.persistence or not settings.committee_persistence_enabled:
            return None
        payload = await self.persistence.load_committee_connection(connection_id)
        if not payload:
            return None

        from ..committee.industry_profiles import get_industry_profile
        from ..committee.models import CommitteeDocument

        restored = CommitteeConnectionContext(
            connection_id=connection_id,
            document=CommitteeDocument.model_validate(payload["document"]),
            personas=[
                CommitteePersona.model_validate(persona)
                for persona in payload.get("personas", [])
            ],
            profile=get_industry_profile(payload["profile"]["id"]),
            evaluation_mode=payload["evaluation_mode"],
            llm_config=LlmConfig.model_validate(payload["llm_config"])
            if payload.get("llm_config")
            else None,
            warnings=list(payload.get("warnings", [])),
        )
        self.connections[connection_id] = restored
        return restored

    async def create_run(self, run_id: str, ctx: CommitteeRunContext) -> None:
        self.runs[run_id] = ctx
        self.pubsub.subscribers.setdefault(run_id, set())
        await self._persist_run(run_id)

    async def get_run(self, run_id: str) -> Optional[CommitteeRunContext]:
        return self.runs.get(run_id)

    async def get_snapshot(self, run_id: str) -> Optional[CommitteeSnapshot]:
        ctx = self.runs.get(run_id)
        if ctx:
            return self._build_snapshot(run_id, ctx)
        if self.persistence and settings.committee_persistence_enabled:
            return await self.persistence.load_committee_snapshot(run_id)
        return None

    def _build_snapshot(self, run_id: str, ctx: CommitteeRunContext) -> CommitteeSnapshot:
        document = ctx.best_document if ctx.stage == "completed" else ctx.document
        return CommitteeSnapshot(
            runId=run_id,
            stage=ctx.stage,
            summary=ctx.summary,
            document=document.model_copy(update={"rawText": ""}),
            personas=ctx.personas,
            rewrites=ctx.rewrites,
            metrics=ctx.metrics,
            evaluationMode=ctx.evaluation_mode,
            warnings=ctx.warnings,
            startedAt=ctx.started_at,
            completedAt=ctx.completed_at,
        )

    async def start_run_tasks(self, run_id: str) -> None:
        ctx = self.runs.get(run_id)
        if not ctx:
            return
        optimizer_task = asyncio.create_task(
            self._optimizer_loop(run_id),
            name=f"committee-optimizer-{run_id}",
        )
        metrics_task = asyncio.create_task(
            self._metrics_heartbeat(run_id),
            name=f"committee-metrics-{run_id}",
        )
        ctx.tasks.extend([optimizer_task, metrics_task])

    async def stop_run(self, run_id: str) -> None:
        ctx = self.runs.get(run_id)
        if not ctx:
            return
        ctx.cancel_flag.set()
        ctx.stage = "stopping"
        await self._persist_run(run_id)
        await self.publish(
            run_id,
            {"type": "run.stage", "payload": {"runId": run_id, "stage": "stopping"}},
        )

    async def get_report(self, run_id: str) -> Optional[CommitteeReport]:
        ctx = self.runs.get(run_id)
        if ctx and ctx.report:
            return ctx.report
        if self.persistence and settings.committee_persistence_enabled:
            return await self.persistence.load_committee_report(run_id)
        return None

    async def get_export(self, run_id: str) -> Optional[CommitteeExportPayload]:
        ctx = self.runs.get(run_id)
        if ctx:
            return build_export_payload(ctx)
        if self.persistence and settings.committee_persistence_enabled:
            return await self.persistence.load_committee_export(run_id)
        return None

    async def list_runs(
        self,
        *,
        limit: int = 50,
        industry_profile_id: Optional[str] = None,
        completed_only: bool = False,
    ) -> List[Dict[str, Any]]:
        if not self.persistence or not settings.committee_persistence_enabled:
            return []
        return await self.persistence.list_committee_runs(
            limit=limit,
            industry_profile_id=industry_profile_id,
            completed_only=completed_only,
        )

    async def _persist_run(self, run_id: str) -> None:
        if not self.persistence or not settings.committee_persistence_enabled:
            return
        ctx = self.runs.get(run_id)
        if not ctx:
            return
        await self.persistence.save_committee_snapshot(self._build_snapshot(run_id, ctx))
        if ctx.report:
            await self.persistence.save_committee_report(ctx.report)
        if ctx.stage in ("completed", "error"):
            await self.persistence.save_committee_export(build_export_payload(ctx))

    async def _optimizer_loop(self, run_id: str) -> None:
        ctx = self.runs.get(run_id)
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
            ctx.profile,
            llm_svc,
            warnings=ctx.warnings,
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
                previous_personas=None,
                reaction_memory_weight=ctx.reaction_memory_weight,
            )
            baseline_score = evaluator.consensus_score(
                ctx.personas,
                ctx.evaluation_mode,
            )
            ctx.metrics.baselineScore = baseline_score
            ctx.metrics.currentScore = baseline_score
            ctx.metrics.bestScore = baseline_score
            ctx.metrics.scoreTimeline = [ScoreTimelinePoint(t=0.0, score=baseline_score)]
            ctx.best_score = baseline_score
            _update_evaluation_metrics(ctx)
        except Exception as exc:
            logger.error("Committee baseline evaluation failed: %s", exc)
            ctx.warnings.append(f"Baseline evaluation failed: {exc}")
            await self.publish_error(
                run_id,
                code="committee_baseline_failed",
                message="Committee baseline evaluation failed; continuing with fallback scoring.",
                details={"error": str(exc)},
            )
            ctx.metrics.baselineScore = 0.35
            ctx.metrics.currentScore = 0.35
            ctx.metrics.bestScore = 0.35
            ctx.metrics.scoreTimeline = [ScoreTimelinePoint(t=0.0, score=0.35)]
            ctx.best_score = 0.35

        await self._persist_run(run_id)
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
                    candidate_evaluations[(section.id, persona.id)] = (
                        await evaluator.evaluate_section(persona, updated_section)
                    )

                candidate_personas = _build_committee_persona_views(
                    evaluator=evaluator,
                    persona_definitions=ctx.persona_definitions,
                    sections=candidate_sections,
                    evaluations=candidate_evaluations,
                    latest_section_id=section.id,
                    previous_personas={persona.id: persona for persona in ctx.personas},
                    reaction_memory_weight=ctx.reaction_memory_weight,
                )
                candidate_score = evaluator.consensus_score(
                    candidate_personas,
                    ctx.evaluation_mode,
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
                    proposal.parameter_name,
                    deque(maxlen=6),
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
                        t=ctx.metrics.elapsedSeconds,
                        score=ctx.metrics.currentScore,
                    )
                )
                _update_evaluation_metrics(ctx)

                await self._persist_run(run_id)
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

                remaining = 0.85 - (time.monotonic() - iteration_started)
                if remaining > 0 and not ctx.cancel_flag.is_set():
                    await asyncio.sleep(remaining)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Committee optimizer error at rewrite %d: %s", exp_num, exc)
                await self.publish_error(
                    run_id,
                    code="committee_optimizer_error",
                    message="Committee optimizer hit an unexpected error and will continue.",
                    details={"experiment": exp_num + 1, "error": str(exc)},
                )
                await self._persist_run(run_id)
                await asyncio.sleep(1.0)

        if ctx.started_monotonic is not None:
            ctx.metrics.elapsedSeconds = time.monotonic() - ctx.started_monotonic

        ctx.stage = "completed"
        ctx.completed_at = now_ts()
        ctx.report = await build_report_async(ctx)
        export_payload = build_export_payload(ctx)
        await self._persist_run(run_id)
        from .elastic_sink_service import ElasticSinkService

        sink = ElasticSinkService.from_settings()
        if sink is not None and ctx.report is not None:
            try:
                await sink.index_committee_run(ctx.report, export_payload)
            except Exception as exc:
                logger.warning("Elastic sink indexing failed for committee run %s: %s", run_id, exc)
                ctx.warnings.append(f"Elastic sink indexing failed: {exc}")
            finally:
                await sink.close()
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

    async def _metrics_heartbeat(self, run_id: str) -> None:
        ctx = self.runs.get(run_id)
        if not ctx:
            return

        while not ctx.cancel_flag.is_set():
            try:
                if ctx.started_monotonic is not None and ctx.stage in (
                    "running",
                    "starting",
                    "stopping",
                ):
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
                await self.publish_error(
                    run_id,
                    code="committee_metrics_error",
                    message="Committee telemetry heartbeat recovered from an error.",
                    details={"error": str(exc)},
                )
                await asyncio.sleep(1.0)


def _sanitize_committee_document(document: Any) -> dict[str, Any]:
    payload = document.model_dump() if hasattr(document, "model_dump") else dict(document)
    payload["rawText"] = ""
    return payload


def _build_committee_persona_views(
    *,
    evaluator: CommitteeEvaluator,
    persona_definitions: List[Any],
    sections: List[Any],
    evaluations: Dict[tuple[int, str], Any],
    latest_section_id: Optional[int],
    previous_personas: Optional[Dict[str, CommitteePersonaView]],
    reaction_memory_weight: float,
) -> List[CommitteePersonaView]:
    return [
        evaluator.rollup_persona_view(
            persona=persona,
            sections=sections,
            evaluations=evaluations,
            latest_section_id=latest_section_id,
            previous_view=(previous_personas or {}).get(persona.id),
            reaction_memory_weight=reaction_memory_weight,
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
    parameter_history: Dict[str, deque[float]],
    rng: random.Random,
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
