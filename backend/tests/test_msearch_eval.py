from __future__ import annotations

import asyncio

from backend.config import settings
from backend.models.contracts import EvalCase
from backend.models.runtime import RunContext
from backend.services.demo_service import DemoService
from backend.services.run_manager import RunManager


class FakeMsearchService:
    async def msearch_profile_queries(self, index: str, eval_cases, profile, size: int = 10):
        return {
            "eval_001": ["doc_9", "doc_3", "doc_2"],
            "eval_002": [],
        }


def test_msearch_eval_path_matches_expected_ndcg() -> None:
    async def scenario() -> None:
        original = settings.use_msearch_eval
        settings.use_msearch_eval = True
        try:
            connection = DemoService().create_connection("conn_eval")
            connection.mode = "live"
            connection.es_url = "http://localhost:9200"
            connection.index_name = "products-catalog"
            connection.eval_set = [
                EvalCase(
                    id="eval_001",
                    query="lip pencil",
                    relevantDocIds=["doc_2", "doc_9"],
                ),
                EvalCase(
                    id="eval_002",
                    query="serum foundation",
                    relevantDocIds=["doc_4"],
                ),
            ]

            ctx = RunContext(
                run_id="run_eval",
                connection=connection,
                personas=[],
                max_experiments=1,
                duration_minutes=1,
                auto_stop_on_plateau=True,
            )

            score, misses, per_query = await RunManager()._evaluate_profile(
                ctx,
                ctx.baseline_profile,
                es_svc=FakeMsearchService(),
            )

            assert round(score, 4) == 0.4599
            assert misses == ["serum foundation"]
            assert round(per_query["eval_001"], 4) == 0.9197
        finally:
            settings.use_msearch_eval = original

    asyncio.run(scenario())
