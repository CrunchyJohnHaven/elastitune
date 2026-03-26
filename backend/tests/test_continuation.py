from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from backend.main import app
from backend.models.contracts import ExperimentRecord, SearchProfileChange
from backend.services.run_manager import RunManager


class FakeESService:
    def __init__(self, es_url: str, api_key: str | None = None):
        self.es_url = es_url
        self.api_key = api_key

    async def ping(self) -> bool:
        return True

    async def get_cluster_info(self):
        return {"cluster_name": "continuation-test", "version": {"number": "8.15.1"}}

    async def analyze_index(
        self, index: str, vector_field_override=None, max_sample_docs=120
    ):
        return {
            "text_fields": ["title", "description"],
            "vector_field": None,
            "vector_dims": None,
            "sample_docs": [
                {
                    "_id": "doc_1",
                    "title": "Lip pencil",
                    "description": "Glossy lip pencil",
                },
                {
                    "_id": "doc_2",
                    "title": "Serum foundation",
                    "description": "Lightweight foundation",
                },
            ],
            "domain": "general",
        }

    async def count_docs(self, index: str) -> int:
        return 100

    async def build_baseline_profile(self, text_fields, vector_field=None):
        return {
            "lexicalFields": [
                {"field": field, "boost": 2.0 if i == 0 else 1.0}
                for i, field in enumerate(text_fields)
            ],
            "multiMatchType": "best_fields",
            "minimumShouldMatch": "75%",
            "tieBreaker": 0.0,
            "phraseBoost": 0.0,
            "fuzziness": "0",
            "useVector": False,
            "vectorField": None,
            "vectorWeight": 0.35,
            "lexicalWeight": 0.65,
            "fusionMethod": "weighted_sum",
            "rrfRankConstant": 60,
            "knnK": 20,
            "numCandidates": 100,
        }

    async def close(self) -> None:
        return None


class FakeLLMService:
    def __init__(self, config):
        self.available = False


def test_run_continuation_carries_original_baseline_and_cumulative_progress() -> None:
    connect_payload = {
        "mode": "live",
        "esUrl": "http://127.0.0.1:9200",
        "indexName": "products-catalog",
        "autoGenerateEval": False,
        "uploadedEvalSet": [
            {
                "id": "eval_001",
                "query": "lip pencil",
                "relevantDocIds": ["doc_1"],
                "difficulty": "easy",
            }
        ],
    }

    run_payload = {
        "connectionId": "",
        "durationMinutes": 1,
        "maxExperiments": 0,
        "personaCount": 4,
        "autoStopOnPlateau": True,
    }

    no_start = AsyncMock(return_value=None)
    with (
        patch("backend.services.es_service.ESService", FakeESService),
        patch("backend.services.llm_service.LLMService", FakeLLMService),
        patch.object(RunManager, "start_run_tasks", new=no_start),
    ):
        with TestClient(app) as client:
            connect_response = client.post("/api/connect", json=connect_payload)
            assert connect_response.status_code == 200, connect_response.text
            connection_id = connect_response.json()["connectionId"]

            run_payload["connectionId"] = connection_id
            first_response = client.post("/api/runs", json=run_payload)
            assert first_response.status_code == 200, first_response.text
            first_run_id = first_response.json()["runId"]

            manager = app.state.run_manager
            first_ctx = manager.runs[first_run_id]
            first_ctx.metrics.baselineScore = 0.45
            first_ctx.metrics.currentScore = 0.52
            first_ctx.metrics.bestScore = 0.52
            first_ctx.metrics.experimentsRun = 4
            first_ctx.metrics.improvementsKept = 2
            first_ctx.best_score = 0.52
            first_ctx.best_profile.phraseBoost = 2.0
            first_ctx.experiments = [
                ExperimentRecord(
                    experimentId=1,
                    timestamp="2026-03-26T12:00:00Z",
                    hypothesis="Reward exact phrase matches more strongly.",
                    change=SearchProfileChange(
                        path="phraseBoost",
                        before=0.0,
                        after=2.0,
                        label="Phrase boost 0.0 → 2.0",
                    ),
                    beforeScore=0.45,
                    candidateScore=0.52,
                    deltaAbsolute=0.07,
                    deltaPercent=15.56,
                    decision="kept",
                    durationMs=1200,
                    queryFailuresBefore=[],
                    queryFailuresAfter=[],
                )
            ]

            second_response = client.post(
                "/api/runs",
                json={**run_payload, "previousRunId": first_run_id},
            )
            assert second_response.status_code == 200, second_response.text
            second_run_id = second_response.json()["runId"]

            second_ctx = manager.runs[second_run_id]
            assert second_ctx.original_baseline_score == 0.45
            assert second_ctx.prior_experiments_run == 4
            assert second_ctx.prior_improvements_kept == 2

            runner = manager.search_task_runner
            with (
                patch.object(
                    runner,
                    "evaluate_detailed",
                    AsyncMock(
                        side_effect=[
                            (0.52, [], {"eval_001": 0.52}),
                            (0.56, [], {"eval_001": 0.56}),
                        ]
                    ),
                ),
                patch.object(
                    runner,
                    "_collect_query_result_previews",
                    AsyncMock(side_effect=[{}, {}]),
                ),
            ):
                asyncio.run(runner.optimizer_loop(second_run_id))

            expected_improvement = ((0.56 - 0.45) / 0.45) * 100
            assert second_ctx.metrics.originalBaselineScore == 0.45
            assert abs(second_ctx.metrics.improvementPct - expected_improvement) < 0.01
            assert second_ctx.metrics.priorExperimentsRun == 4
            assert second_ctx.metrics.priorImprovementsKept == 2
