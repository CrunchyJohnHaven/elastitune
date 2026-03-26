from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app


class FakeESService:
    def __init__(self, es_url: str, api_key: str | None = None):
        self.es_url = es_url
        self.api_key = api_key

    async def ping(self) -> bool:
        return True

    async def get_cluster_info(self):
        return {"cluster_name": "local-benchmark", "version": {"number": "8.15.1"}}

    async def analyze_index(self, index: str, vector_field_override=None, max_sample_docs=120):
        return {
            "text_fields": ["title", "description"],
            "vector_field": None,
            "vector_dims": None,
            "sample_docs": [
                {"_id": "doc_1", "title": "Lip pencil", "description": "Glossy lip pencil"},
                {"_id": "doc_2", "title": "Foundation", "description": "Serum foundation"},
            ],
            "domain": "general",
        }

    async def count_docs(self, index: str) -> int:
        return 931

    async def build_baseline_profile(self, text_fields, vector_field=None):
        return {
            "lexicalFields": [{"field": field, "boost": 2.0 if i == 0 else 1.0} for i, field in enumerate(text_fields)],
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


def test_live_connect_uses_uploaded_eval_set_for_baseline_count() -> None:
    payload = {
        "mode": "live",
        "esUrl": "http://127.0.0.1:9200",
        "indexName": "products-catalog",
        "autoGenerateEval": False,
        "uploadedEvalSet": [
            {
                "id": "eval_001",
                "query": "lip pencil",
                "relevantDocIds": ["1048", "892"],
                "difficulty": "easy",
            },
            {
                "id": "eval_002",
                "query": "serum foundation",
                "relevantDocIds": ["1043", "1042"],
                "difficulty": "easy",
            },
        ],
    }

    with patch("backend.services.es_service.ESService", FakeESService), patch(
        "backend.services.llm_service.LLMService", FakeLLMService
    ):
        with TestClient(app) as client:
            response = client.post("/api/connect", json=payload)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["summary"]["baselineEvalCount"] == 2
    assert body["summary"]["baselineReady"] is True
    assert body["summary"]["docCount"] == 931
    assert body["summary"]["indexName"] == "products-catalog"
