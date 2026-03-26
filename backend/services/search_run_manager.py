from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..models.contracts import (
    ConnectionSummary,
    EvalCase,
    LlmConfig,
    RunSnapshot,
    SearchProfile,
    SearchProfileChange,
)
from ..models.report import ReportPayload
from ..models.runtime import ConnectionContext, RunContext
from .persistence_service import PersistenceService
from .run_pubsub import RunPubSub
from .task_runner import SearchTaskRunner


class SearchRunManager:
    def __init__(
        self,
        *,
        pubsub: RunPubSub,
        persistence: Optional[PersistenceService] = None,
    ) -> None:
        self.pubsub = pubsub
        self.persistence = persistence
        self.connections: Dict[str, ConnectionContext] = {}
        self.runs: Dict[str, RunContext] = {}
        self.search_task_runner = SearchTaskRunner(self)

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

    async def publish_invariant(
        self,
        run_id: str,
        *,
        name: str,
        message: str,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        await self.pubsub.publish_invariant(
            run_id,
            name=name,
            message=message,
            details=details,
        )

    async def create_connection(
        self,
        connection_id: str,
        ctx: ConnectionContext,
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

    async def create_run(self, run_id: str, ctx: RunContext) -> None:
        self.runs[run_id] = ctx
        self.pubsub.subscribers.setdefault(run_id, set())
        await self._persist_run(run_id)

    async def get_run(self, run_id: str) -> Optional[RunContext]:
        return self.runs.get(run_id)

    async def get_snapshot(self, run_id: str) -> Optional[RunSnapshot]:
        ctx = self.runs.get(run_id)
        if ctx:
            return self._build_snapshot(run_id, ctx)
        if self.persistence:
            return await self.persistence.load_snapshot(run_id)
        return None

    def _build_snapshot(self, run_id: str, ctx: RunContext) -> RunSnapshot:
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
                "optimizerStrategy": ctx.optimizer_strategy,
            },
            startedAt=ctx.started_at,
            completedAt=ctx.completed_at,
        )

    async def start_run_tasks(self, run_id: str) -> None:
        ctx = self.runs.get(run_id)
        if not ctx:
            return

        if ctx.mode == "demo":
            from .demo_service import DemoService

            demo_svc = DemoService()
            task = asyncio.create_task(
                demo_svc.run_demo_orchestrator(ctx, self),
                name=f"demo-orchestrator-{run_id}",
            )
            ctx.tasks.append(task)
            return

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
        ctx.tasks.extend([optimizer_task, persona_task, compression_task, metrics_task])

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

    async def get_report(self, run_id: str) -> Optional[ReportPayload]:
        ctx = self.runs.get(run_id)
        if ctx and ctx.report:
            return ctx.report
        if self.persistence:
            return await self.persistence.load_report(run_id)
        return None

    async def list_runs(
        self,
        *,
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

    async def _persist_run(self, run_id: str) -> None:
        if not self.persistence:
            return
        ctx = self.runs.get(run_id)
        if not ctx:
            return
        await self.persistence.save_snapshot(self._build_snapshot(run_id, ctx))

    async def _persist_search_run(self, run_id: str) -> None:
        await self._persist_run(run_id)

    async def evaluate_profile(
        self,
        ctx: RunContext,
        profile: SearchProfile,
        es_svc: Optional[Any] = None,
    ) -> Tuple[float, List[str], Dict[str, float]]:
        return await self.search_task_runner.evaluate_profile(ctx, profile, es_svc=es_svc)

    async def evaluate_detailed(
        self,
        ctx: RunContext,
        profile: SearchProfile,
        es_svc: Optional[Any] = None,
    ) -> Tuple[float, List[str], Dict[str, float]]:
        return await self.search_task_runner.evaluate_detailed(ctx, profile, es_svc=es_svc)

    async def collect_query_result_previews(
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

    async def pick_next_experiment(
        self,
        ctx: RunContext,
        llm_svc: Optional[Any],
        exp_num: int,
    ) -> Optional[SearchProfileChange]:
        return await self.search_task_runner._pick_next_experiment(ctx, llm_svc, exp_num)

    def compute_ndcg_at_k(
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
