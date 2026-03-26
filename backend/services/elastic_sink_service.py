from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any, Optional

from elasticsearch import AsyncElasticsearch

from ..committee.models import CommitteeExportPayload, CommitteeReport
from ..config import settings
from ..models.report import ReportPayload

logger = logging.getLogger(__name__)


@dataclass
class ElasticSinkConfig:
    es_url: str
    api_key: Optional[str]
    search_runs_prefix: str
    search_experiments_prefix: str
    committee_runs_prefix: str


class ElasticSinkService:
    def __init__(self, config: ElasticSinkConfig) -> None:
        kwargs: dict[str, Any] = {
            "verify_certs": False,
            "ssl_show_warn": False,
        }
        if config.api_key:
            kwargs["api_key"] = config.api_key
        self.config = config
        self.client = AsyncElasticsearch(config.es_url, **kwargs)

    @classmethod
    def from_settings(cls) -> Optional["ElasticSinkService"]:
        if not settings.enable_elastic_sink or not settings.elastic_sink_url:
            return None
        return cls(
            ElasticSinkConfig(
                es_url=settings.elastic_sink_url,
                api_key=settings.elastic_sink_api_key or None,
                search_runs_prefix=settings.elastic_sink_search_runs_prefix,
                search_experiments_prefix=settings.elastic_sink_search_experiments_prefix,
                committee_runs_prefix=settings.elastic_sink_committee_runs_prefix,
            )
        )

    async def close(self) -> None:
        try:
            await self.client.close()
        except Exception:
            pass

    async def index_search_run(self, report: ReportPayload) -> None:
        index_name = _dated_index_name(
            self.config.search_runs_prefix,
            report.generatedAt,
        )
        payload = {
            "@timestamp": report.generatedAt,
            "event": {
                "kind": "metric",
                "category": ["database", "search"],
                "action": "search_run_completed",
            },
            "elastitune": {
                "product_mode": "search",
                "run_id": report.runId,
                "mode": report.mode,
                "headline": report.summary.headline,
                "overview": report.summary.overview,
                "connection": {
                    "cluster_name": report.connection.clusterName,
                    "cluster_version": report.connection.clusterVersion,
                    "index_name": report.connection.indexName,
                    "domain": report.connection.detectedDomain,
                },
                "metrics": {
                    "baseline_score": report.summary.baselineScore,
                    "best_score": report.summary.bestScore,
                    "improvement_pct": report.summary.improvementPct,
                    "experiments_run": report.summary.experimentsRun,
                    "improvements_kept": report.summary.improvementsKept,
                    "duration_seconds": report.summary.durationSeconds,
                    "projected_monthly_savings_usd": report.summary.projectedMonthlySavingsUsd,
                },
                "search_profile_before": report.searchProfileBefore.model_dump(),
                "search_profile_after": report.searchProfileAfter.model_dump(),
                "warnings": report.warnings,
            },
        }
        await self.client.index(index=index_name, id=report.runId, document=payload, refresh="wait_for")
        await self._bulk_index_search_experiments(report)

    async def index_committee_run(
        self,
        report: CommitteeReport,
        export_payload: CommitteeExportPayload,
    ) -> None:
        index_name = _dated_index_name(
            self.config.committee_runs_prefix,
            report.generatedAt,
        )
        payload = {
            "@timestamp": report.generatedAt,
            "event": {
                "kind": "metric",
                "category": ["process", "knowledge_base"],
                "action": "committee_run_completed",
            },
            "elastitune": {
                "product_mode": "committee",
                "run_id": report.runId,
                "headline": report.summary.headline,
                "document_name": report.document.documentName,
                "evaluation_mode": report.evaluationMode,
                "industry_profile": export_payload.committeeSummary.get("industryProfileId"),
                "industry_label": export_payload.committeeSummary.get("industryLabel"),
                "metrics": {
                    "baseline_score": report.summary.baselineScore,
                    "best_score": report.summary.bestScore,
                    "improvement_pct": report.summary.improvementPct,
                    "rewrites_tested": report.summary.rewritesTested,
                    "accepted_rewrites": report.summary.acceptedRewrites,
                },
                "personas": [
                    {
                        "name": persona.name,
                        "title": persona.title,
                        "authority_weight": persona.authorityWeight,
                        "current_score": persona.currentScore,
                        "sentiment": persona.sentiment,
                    }
                    for persona in report.personas
                ],
                "warnings": report.warnings,
            },
        }
        await self.client.index(index=index_name, id=report.runId, document=payload, refresh="wait_for")

    async def _bulk_index_search_experiments(self, report: ReportPayload) -> None:
        if not report.experiments:
            return
        index_name = _dated_index_name(
            self.config.search_experiments_prefix,
            report.generatedAt,
        )
        operations: list[dict[str, Any]] = []
        for experiment in report.experiments:
            operations.append(
                {
                    "index": {
                        "_index": index_name,
                        "_id": f"{report.runId}-{experiment.experimentId}",
                    }
                }
            )
            operations.append(
                {
                    "@timestamp": experiment.timestamp,
                    "event": {
                        "kind": "metric",
                        "category": ["search"],
                        "action": "search_experiment_completed",
                    },
                    "elastitune": {
                        "run_id": report.runId,
                        "experiment_id": experiment.experimentId,
                        "hypothesis": experiment.hypothesis,
                        "decision": experiment.decision,
                        "before_score": experiment.beforeScore,
                        "candidate_score": experiment.candidateScore,
                        "delta_absolute": experiment.deltaAbsolute,
                        "delta_percent": experiment.deltaPercent,
                        "duration_ms": experiment.durationMs,
                        "change": experiment.change.model_dump(),
                    },
                }
            )
        try:
            await self.client.bulk(operations=operations, refresh="wait_for")
        except TypeError:
            await self.client.bulk(body=operations, refresh="wait_for")


def _dated_index_name(prefix: str, timestamp: str) -> str:
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        parsed = datetime.utcnow()
    return f"{prefix}-{parsed:%Y.%m}"
