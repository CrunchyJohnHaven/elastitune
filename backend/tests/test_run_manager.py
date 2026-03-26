from __future__ import annotations

import asyncio

from backend.api.routes_runs import _build_personas
from backend.models.contracts import EvalCase
from backend.models.runtime import RunContext
from backend.services.demo_service import DemoService
from backend.services.run_manager import RunManager


class FakeESService:
    def __init__(self, results_by_query: dict[str, list[str]]):
        self.results_by_query = results_by_query

    async def execute_profile_query(self, index: str, query_text: str, profile, size: int = 10):
        return self.results_by_query.get(query_text, [])[:size]


def test_evaluate_profile_uses_real_rankings_for_ndcg() -> None:
    async def scenario() -> None:
        connection = DemoService().create_connection("conn_eval")
        connection.mode = "live"
        connection.es_url = "http://localhost:9200"
        connection.index_name = "products-catalog"
        connection.eval_set = [
            EvalCase(id="eval_001", query="lip pencil", relevantDocIds=["doc_2", "doc_9"]),
            EvalCase(id="eval_002", query="serum foundation", relevantDocIds=["doc_4"]),
        ]

        ctx = RunContext(
            run_id="run_eval",
            connection=connection,
            personas=[],
            max_experiments=1,
            duration_minutes=1,
            auto_stop_on_plateau=True,
        )

        score, misses = await RunManager()._evaluate_profile(
            ctx,
            ctx.baseline_profile,
            es_svc=FakeESService(
                {
                    "lip pencil": ["doc_9", "doc_3", "doc_2"],
                    "serum foundation": [],
                }
            ),
        )

        assert round(score, 4) == 0.4599
        assert misses == ["serum foundation"]

    asyncio.run(scenario())


def test_live_personas_adapt_to_product_catalog_without_llm() -> None:
    async def scenario() -> None:
        personas = await _build_personas(
            persona_count=6,
            mode="live",
            domain="general",
            sample_docs=[
                {
                    "_id": "1048",
                    "title": "Hydrating Lip Pencil",
                    "description": "Creamy lip color with long-wear finish",
                    "brand": "Acme Beauty",
                    "price": "19.00",
                },
                {
                    "_id": "1043",
                    "title": "Serum Foundation",
                    "description": "Lightweight foundation for sensitive skin",
                    "sku": "FND-1043",
                },
            ],
            text_fields=["title", "description", "brand"],
            llm_config=None,
        )

        roles = {persona.role for persona in personas}
        assert "SOC Analyst" not in roles
        assert roles & {"Online Shopper", "Category Merchandiser", "Customer Support Lead"}

    asyncio.run(scenario())
