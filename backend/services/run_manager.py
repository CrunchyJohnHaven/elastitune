from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from ..committee.models import CommitteeExportPayload, CommitteeReport, CommitteeSnapshot
from ..committee.runtime import CommitteeConnectionContext, CommitteeRunContext
from ..engine.optimizer_search_space import build_hypothesis_text
from ..models.contracts import (
    ExperimentRecord,
    RunSnapshot,
    SearchProfile,
    SearchProfileChange,
)
from ..models.report import ReportPayload
from ..models.runtime import ConnectionContext, RunContext
from .committee_run_manager import CommitteeRunManager
from .persistence_service import PersistenceService
from .run_pubsub import RunPubSub
from .search_run_manager import SearchRunManager
from .task_runner import (
    _apply_profile_change,
    _heuristic_next_experiment,
    _random_perturbation,
)


class RunManager:
    """Facade that preserves the historical interface while using split managers."""

    def __init__(self, persistence: Optional[PersistenceService] = None) -> None:
        self.persistence = persistence
        self.pubsub = RunPubSub()
        self.search = SearchRunManager(pubsub=self.pubsub, persistence=persistence)
        self.committee = CommitteeRunManager(pubsub=self.pubsub, persistence=persistence)
        self.search_task_runner = self.search.search_task_runner
        self.connections = self.search.connections
        self.runs = self.search.runs
        self.committee_connections = self.committee.connections
        self.committee_runs = self.committee.runs
        self.subscribers = self.pubsub.subscribers

    async def publish(self, run_id: str, event: dict[str, Any]) -> None:
        await self.pubsub.publish(run_id, event)

    async def subscribe(self, run_id: str):
        return await self.pubsub.subscribe(run_id)

    async def unsubscribe(self, run_id: str, queue) -> None:
        await self.pubsub.unsubscribe(run_id, queue)

    async def create_connection(self, connection_id: str, ctx: ConnectionContext) -> None:
        await self.search.create_connection(connection_id, ctx)

    async def get_connection(self, connection_id: str) -> Optional[ConnectionContext]:
        return await self.search.get_connection(connection_id)

    async def create_committee_connection(
        self,
        connection_id: str,
        ctx: CommitteeConnectionContext,
    ) -> None:
        await self.committee.create_connection(connection_id, ctx)

    async def get_committee_connection(
        self,
        connection_id: str,
    ) -> Optional[CommitteeConnectionContext]:
        return await self.committee.get_connection(connection_id)

    async def create_run(self, run_id: str, ctx: RunContext) -> None:
        await self.search.create_run(run_id, ctx)

    async def get_run(self, run_id: str) -> Optional[RunContext]:
        return await self.search.get_run(run_id)

    async def create_committee_run(self, run_id: str, ctx: CommitteeRunContext) -> None:
        await self.committee.create_run(run_id, ctx)

    async def get_committee_run(self, run_id: str) -> Optional[CommitteeRunContext]:
        return await self.committee.get_run(run_id)

    async def get_snapshot(self, run_id: str) -> Optional[RunSnapshot]:
        return await self.search.get_snapshot(run_id)

    async def get_committee_snapshot(
        self,
        run_id: str,
    ) -> Optional[CommitteeSnapshot]:
        return await self.committee.get_snapshot(run_id)

    async def get_any_snapshot(self, run_id: str) -> Optional[Any]:
        search_snapshot = await self.get_snapshot(run_id)
        if search_snapshot is not None:
            return search_snapshot
        return await self.get_committee_snapshot(run_id)

    async def get_any_run(self, run_id: str) -> Optional[Any]:
        search_run = await self.get_run(run_id)
        if search_run is not None:
            return search_run
        return await self.get_committee_run(run_id)

    async def start_run_tasks(self, run_id: str) -> None:
        await self.search.start_run_tasks(run_id)

    async def start_committee_run_tasks(self, run_id: str) -> None:
        await self.committee.start_run_tasks(run_id)

    async def stop_run(self, run_id: str) -> None:
        await self.search.stop_run(run_id)

    async def stop_committee_run(self, run_id: str) -> None:
        await self.committee.stop_run(run_id)

    async def get_committee_export(
        self,
        run_id: str,
    ) -> Optional[dict[str, Any]]:
        payload = await self.committee.get_export(run_id)
        return payload.model_dump() if payload else None

    async def get_committee_report(
        self,
        run_id: str,
    ) -> Optional[CommitteeReport]:
        return await self.committee.get_report(run_id)

    async def get_report(self, run_id: str) -> Optional[ReportPayload]:
        return await self.search.get_report(run_id)

    async def list_search_runs(
        self,
        limit: int = 50,
        index_name: Optional[str] = None,
        completed_only: bool = False,
    ) -> List[Dict[str, Any]]:
        return await self.search.list_runs(
            limit=limit,
            index_name=index_name,
            completed_only=completed_only,
        )

    async def list_committee_runs(
        self,
        limit: int = 50,
        industry_profile_id: Optional[str] = None,
        completed_only: bool = False,
    ) -> List[Dict[str, Any]]:
        return await self.committee.list_runs(
            limit=limit,
            industry_profile_id=industry_profile_id,
            completed_only=completed_only,
        )

    async def _persist_search_run(self, run_id: str) -> None:
        await self.search._persist_run(run_id)

    async def _persist_committee_run(self, run_id: str) -> None:
        await self.committee._persist_run(run_id)

    async def _evaluate_profile(
        self,
        ctx: RunContext,
        profile: SearchProfile,
        es_svc: Optional[Any] = None,
    ) -> Tuple[float, List[str], Dict[str, float]]:
        return await self.search.evaluate_profile(ctx, profile, es_svc=es_svc)

    async def evaluate_detailed(
        self,
        ctx: RunContext,
        profile: SearchProfile,
        es_svc: Optional[Any] = None,
    ) -> Tuple[float, List[str], Dict[str, float]]:
        return await self.search.evaluate_detailed(ctx, profile, es_svc=es_svc)

    async def _collect_query_result_previews(
        self,
        ctx: RunContext,
        profile: SearchProfile,
        es_svc: Optional[Any] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        return await self.search.collect_query_result_previews(ctx, profile, es_svc=es_svc)

    async def _pick_next_experiment(
        self,
        ctx: RunContext,
        llm_svc: Optional[Any],
        exp_num: int,
    ) -> Optional[SearchProfileChange]:
        return await self.search.pick_next_experiment(ctx, llm_svc, exp_num)

    def _compute_ndcg_at_k(
        self,
        relevant_doc_ids: List[str],
        ranked_doc_ids: List[str],
        k: int = 10,
    ) -> float:
        return self.search.compute_ndcg_at_k(relevant_doc_ids, ranked_doc_ids, k=k)


def _hypothesis_text(change: SearchProfileChange) -> str:
    return build_hypothesis_text(change)
