from __future__ import annotations

import asyncio
import math
from typing import Any, Dict, List, Optional

from backend.models.contracts import (
    ConnectionSummary,
    EvalCase,
    PersonaViewModel,
    SearchProfile,
)
from backend.models.runtime import ConnectionContext, RunContext
from backend.services.demo_service import DemoService
from backend.services.run_manager import RunManager
from backend.services.task_runner import SearchTaskRunner


# ---------------------------------------------------------------------------
# Fake ES services
# ---------------------------------------------------------------------------


class FakeESService:
    """Fake ES service that returns predetermined doc IDs per query."""

    def __init__(self, results_by_query: Dict[str, List[str]]):
        self.results_by_query = results_by_query

    async def execute_profile_query(
        self, index: str, query_text: str, profile: Any, size: int = 10
    ) -> List[str]:
        return self.results_by_query.get(query_text, [])[:size]

    async def execute_profile_query_with_hits(
        self, index: str, query_text: str, profile: Any, size: int = 5
    ) -> List[Dict[str, Any]]:
        doc_ids = self.results_by_query.get(query_text, [])[:size]
        return [{"_id": doc_id, "_score": 1.0 / (i + 1)} for i, doc_id in enumerate(doc_ids)]


class FailingESService:
    """ES service that raises on every query."""

    async def execute_profile_query(
        self, index: str, query_text: str, profile: Any, size: int = 10
    ) -> List[str]:
        raise ConnectionError("Elasticsearch unreachable")

    async def execute_profile_query_with_hits(
        self, index: str, query_text: str, profile: Any, size: int = 5
    ) -> List[Dict[str, Any]]:
        raise ConnectionError("Elasticsearch unreachable")


class PartialFailESService:
    """ES service that fails only for specific queries."""

    def __init__(
        self,
        results_by_query: Dict[str, List[str]],
        fail_queries: set[str],
    ):
        self.results_by_query = results_by_query
        self.fail_queries = fail_queries

    async def execute_profile_query(
        self, index: str, query_text: str, profile: Any, size: int = 10
    ) -> List[str]:
        if query_text in self.fail_queries:
            raise ConnectionError(f"Query failed: {query_text}")
        return self.results_by_query.get(query_text, [])[:size]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_run_context(
    run_id: str = "run_test",
    eval_set: Optional[List[EvalCase]] = None,
    es_url: Optional[str] = "http://localhost:9200",
    index_name: str = "test-index",
    personas: Optional[List[PersonaViewModel]] = None,
    vector_field: Optional[str] = None,
    vector_dims: Optional[int] = None,
) -> RunContext:
    connection = DemoService().create_connection("conn_test")
    connection.mode = "live"
    connection.es_url = es_url
    connection.index_name = index_name
    if eval_set is not None:
        connection.eval_set = eval_set
    connection.summary = ConnectionSummary(
        clusterName="test-cluster",
        indexName=index_name,
        docCount=10000,
        detectedDomain="general",
        primaryTextFields=["title", "description"],
        vectorField=vector_field,
        vectorDims=vector_dims,
    )
    return RunContext(
        run_id=run_id,
        connection=connection,
        personas=personas or [],
        max_experiments=1,
        duration_minutes=1,
        auto_stop_on_plateau=True,
    )


# ===========================================================================
# 1. evaluate_profile — FakeESService, nDCG computation, gather batching
# ===========================================================================


def test_evaluate_profile_computes_ndcg_with_fake_es() -> None:
    async def scenario() -> None:
        ctx = _make_run_context(
            eval_set=[
                EvalCase(id="q1", query="lip pencil", relevantDocIds=["doc_2", "doc_9"]),
                EvalCase(id="q2", query="serum foundation", relevantDocIds=["doc_4"]),
            ],
        )
        manager = RunManager()
        runner = SearchTaskRunner(manager)

        fake_es = FakeESService(
            {
                "lip pencil": ["doc_9", "doc_3", "doc_2"],
                "serum foundation": [],
            }
        )
        score, misses, per_query = await runner.evaluate_profile(
            ctx, ctx.baseline_profile, es_svc=fake_es
        )

        # q1: doc_9 at rank 1, doc_2 at rank 3 → DCG = 1/log2(2) + 1/log2(4)
        # iDCG for 2 relevant = 1/log2(2) + 1/log2(3)
        expected_q1 = (1.0 / math.log2(2) + 1.0 / math.log2(4)) / (
            1.0 / math.log2(2) + 1.0 / math.log2(3)
        )
        assert round(per_query["q1"], 4) == round(expected_q1, 4)

        # q2: no results → nDCG = 0
        assert per_query["q2"] == 0.0

        # average of the two
        expected_avg = (expected_q1 + 0.0) / 2
        assert round(score, 4) == round(expected_avg, 4)

        # serum foundation missed
        assert misses == ["serum foundation"]

    asyncio.run(scenario())


def test_evaluate_profile_all_relevant_at_top() -> None:
    """Perfect ranking should yield nDCG = 1.0."""

    async def scenario() -> None:
        ctx = _make_run_context(
            eval_set=[
                EvalCase(id="q1", query="shoes", relevantDocIds=["a", "b"]),
            ],
        )
        runner = SearchTaskRunner(RunManager())
        fake_es = FakeESService({"shoes": ["a", "b", "c", "d"]})
        score, misses, per_query = await runner.evaluate_profile(
            ctx, ctx.baseline_profile, es_svc=fake_es
        )
        assert score == 1.0
        assert per_query["q1"] == 1.0
        assert misses == []

    asyncio.run(scenario())


def test_evaluate_profile_gather_batching() -> None:
    """Verify all eval cases are evaluated concurrently via asyncio.gather."""

    async def scenario() -> None:
        eval_set = [
            EvalCase(id=f"q{i}", query=f"query_{i}", relevantDocIds=[f"doc_{i}"])
            for i in range(20)
        ]
        results_by_query = {f"query_{i}": [f"doc_{i}"] for i in range(20)}
        ctx = _make_run_context(eval_set=eval_set)
        runner = SearchTaskRunner(RunManager())
        fake_es = FakeESService(results_by_query)

        score, misses, per_query = await runner.evaluate_profile(
            ctx, ctx.baseline_profile, es_svc=fake_es
        )

        assert len(per_query) == 20
        # Every query finds its relevant doc at rank 1 → nDCG = 1.0
        assert score == 1.0
        assert misses == []

    asyncio.run(scenario())


# ===========================================================================
# 2. evaluate_profile — empty eval set returns 0.5
# ===========================================================================


def test_evaluate_profile_empty_eval_set_returns_default() -> None:
    async def scenario() -> None:
        ctx = _make_run_context(eval_set=[])
        runner = SearchTaskRunner(RunManager())
        score, misses, per_query = await runner.evaluate_profile(
            ctx, ctx.baseline_profile, es_svc=FakeESService({})
        )
        assert score == 0.5
        assert misses == []
        assert per_query == {}

    asyncio.run(scenario())


# ===========================================================================
# 3. evaluate_profile — error handling when ES query fails
# ===========================================================================


def test_evaluate_profile_es_failure_returns_zero_ndcg() -> None:
    """When ES fails for all queries, results are 0 nDCG (not an exception)."""

    async def scenario() -> None:
        ctx = _make_run_context(
            eval_set=[
                EvalCase(id="q1", query="shoes", relevantDocIds=["a"]),
                EvalCase(id="q2", query="hats", relevantDocIds=["b"]),
            ],
        )
        runner = SearchTaskRunner(RunManager())
        failing_es = FailingESService()

        score, misses, per_query = await runner.evaluate_profile(
            ctx, ctx.baseline_profile, es_svc=failing_es
        )

        # ES returned empty results due to errors → nDCG = 0 for each query
        assert score == 0.0
        assert "shoes" in misses
        assert "hats" in misses
        assert per_query["q1"] == 0.0
        assert per_query["q2"] == 0.0

    asyncio.run(scenario())


def test_evaluate_profile_partial_es_failure() -> None:
    """When ES fails for one query but succeeds for another."""

    async def scenario() -> None:
        ctx = _make_run_context(
            eval_set=[
                EvalCase(id="q1", query="shoes", relevantDocIds=["a"]),
                EvalCase(id="q2", query="hats", relevantDocIds=["b"]),
            ],
        )
        runner = SearchTaskRunner(RunManager())
        partial_es = PartialFailESService(
            results_by_query={"shoes": ["a", "c"]},
            fail_queries={"hats"},
        )

        score, misses, per_query = await runner.evaluate_profile(
            ctx, ctx.baseline_profile, es_svc=partial_es
        )

        # q1 succeeds: doc "a" at rank 1 → nDCG = 1.0
        assert per_query["q1"] == 1.0
        # q2 fails → empty results → nDCG = 0
        assert per_query["q2"] == 0.0
        assert "hats" in misses
        assert "shoes" not in misses
        # average = 0.5
        assert score == 0.5

    asyncio.run(scenario())


def test_evaluate_profile_no_es_url_returns_zero() -> None:
    """When es_url is None and no es_svc provided, returns 0.0."""

    async def scenario() -> None:
        ctx = _make_run_context(
            es_url=None,
            eval_set=[
                EvalCase(id="q1", query="shoes", relevantDocIds=["a"]),
            ],
        )
        # Clear out es_url and index_name to trigger early return
        ctx.es_url = None
        ctx.index_name = None
        runner = SearchTaskRunner(RunManager())

        score, misses, per_query = await runner.evaluate_profile(
            ctx, ctx.baseline_profile, es_svc=None
        )

        assert score == 0.0
        assert "shoes" in misses
        assert per_query == {}

    asyncio.run(scenario())


# ===========================================================================
# 4. _compute_ndcg_at_k — basic and edge cases
# ===========================================================================


def test_ndcg_perfect_ranking() -> None:
    runner = SearchTaskRunner(RunManager())
    score = runner._compute_ndcg_at_k(
        relevant_doc_ids=["a", "b", "c"],
        ranked_doc_ids=["a", "b", "c", "d", "e"],
        k=10,
    )
    assert score == 1.0


def test_ndcg_reversed_ranking() -> None:
    runner = SearchTaskRunner(RunManager())
    # Relevant docs at positions 3, 2, 1 (1-indexed)
    score = runner._compute_ndcg_at_k(
        relevant_doc_ids=["a", "b", "c"],
        ranked_doc_ids=["c", "b", "a"],
        k=10,
    )
    # Since all relevant are found, just in different order, nDCG = 1.0
    # (order within relevant set doesn't matter for binary relevance)
    assert score == 1.0


def test_ndcg_no_relevant_docs_in_ranking() -> None:
    runner = SearchTaskRunner(RunManager())
    score = runner._compute_ndcg_at_k(
        relevant_doc_ids=["a", "b"],
        ranked_doc_ids=["x", "y", "z"],
        k=10,
    )
    assert score == 0.0


def test_ndcg_empty_ranked_list() -> None:
    runner = SearchTaskRunner(RunManager())
    score = runner._compute_ndcg_at_k(
        relevant_doc_ids=["a", "b"],
        ranked_doc_ids=[],
        k=10,
    )
    assert score == 0.0


def test_ndcg_empty_relevant_list() -> None:
    runner = SearchTaskRunner(RunManager())
    score = runner._compute_ndcg_at_k(
        relevant_doc_ids=[],
        ranked_doc_ids=["a", "b", "c"],
        k=10,
    )
    assert score == 0.0


def test_ndcg_single_relevant_at_rank_1() -> None:
    runner = SearchTaskRunner(RunManager())
    score = runner._compute_ndcg_at_k(
        relevant_doc_ids=["a"],
        ranked_doc_ids=["a", "b", "c"],
        k=10,
    )
    assert score == 1.0


def test_ndcg_single_relevant_at_rank_5() -> None:
    runner = SearchTaskRunner(RunManager())
    score = runner._compute_ndcg_at_k(
        relevant_doc_ids=["a"],
        ranked_doc_ids=["x", "y", "z", "w", "a"],
        k=10,
    )
    # DCG = 1/log2(6), iDCG = 1/log2(2)
    expected = (1.0 / math.log2(6)) / (1.0 / math.log2(2))
    assert abs(score - expected) < 1e-9


def test_ndcg_k_truncates_ranking() -> None:
    runner = SearchTaskRunner(RunManager())
    # Relevant doc is at position 4, but k=3 so it should not be found
    score = runner._compute_ndcg_at_k(
        relevant_doc_ids=["a"],
        ranked_doc_ids=["x", "y", "z", "a"],
        k=3,
    )
    assert score == 0.0


def test_ndcg_both_empty() -> None:
    runner = SearchTaskRunner(RunManager())
    score = runner._compute_ndcg_at_k(
        relevant_doc_ids=[],
        ranked_doc_ids=[],
        k=10,
    )
    assert score == 0.0


def test_ndcg_duplicate_relevant_ids() -> None:
    """Duplicate relevant IDs should be treated as a set."""
    runner = SearchTaskRunner(RunManager())
    score = runner._compute_ndcg_at_k(
        relevant_doc_ids=["a", "a", "b"],
        ranked_doc_ids=["a", "b", "c"],
        k=10,
    )
    # Relevant set is {"a", "b"}, both at rank 1 and 2 → perfect
    assert score == 1.0


# ===========================================================================
# 5. _collect_query_result_previews — empty eval set
# ===========================================================================


def test_collect_previews_empty_eval_set() -> None:
    async def scenario() -> None:
        ctx = _make_run_context(eval_set=[])
        runner = SearchTaskRunner(RunManager())
        result = await runner._collect_query_result_previews(
            ctx, ctx.baseline_profile, es_svc=FakeESService({})
        )
        assert result == {}

    asyncio.run(scenario())


def test_collect_previews_returns_hits() -> None:
    async def scenario() -> None:
        ctx = _make_run_context(
            eval_set=[
                EvalCase(id="q1", query="shoes", relevantDocIds=["a"]),
            ],
        )
        runner = SearchTaskRunner(RunManager())
        fake_es = FakeESService({"shoes": ["doc_1", "doc_2", "doc_3"]})
        result = await runner._collect_query_result_previews(
            ctx, ctx.baseline_profile, es_svc=fake_es
        )

        assert "q1" in result
        assert len(result["q1"]) == 3
        assert result["q1"][0]["_id"] == "doc_1"

    asyncio.run(scenario())


def test_collect_previews_handles_es_failure() -> None:
    async def scenario() -> None:
        ctx = _make_run_context(
            eval_set=[
                EvalCase(id="q1", query="shoes", relevantDocIds=["a"]),
            ],
        )
        runner = SearchTaskRunner(RunManager())
        failing_es = FailingESService()
        result = await runner._collect_query_result_previews(
            ctx, ctx.baseline_profile, es_svc=failing_es
        )

        # Should return empty list for the query, not raise
        assert result["q1"] == []

    asyncio.run(scenario())


# ===========================================================================
# 6. compression_benchmark — skips when no vector field
# ===========================================================================


def test_compression_benchmark_skips_without_vector_field() -> None:
    async def scenario() -> None:
        manager = RunManager()
        ctx = _make_run_context(
            run_id="run_compress",
            vector_field=None,
            vector_dims=None,
        )
        manager.runs["run_compress"] = ctx
        runner = SearchTaskRunner(manager)

        await runner.compression_benchmark("run_compress")

        assert ctx.compression.status == "skipped"
        assert ctx.compression.methods == []

    asyncio.run(scenario())


def test_compression_benchmark_skips_with_missing_dims() -> None:
    async def scenario() -> None:
        manager = RunManager()
        ctx = _make_run_context(
            run_id="run_compress2",
            vector_field="embedding",
            vector_dims=None,
        )
        manager.runs["run_compress2"] = ctx
        runner = SearchTaskRunner(manager)

        await runner.compression_benchmark("run_compress2")

        assert ctx.compression.status == "skipped"

    asyncio.run(scenario())


def test_compression_benchmark_nonexistent_run() -> None:
    async def scenario() -> None:
        manager = RunManager()
        runner = SearchTaskRunner(manager)
        # Should return immediately without error
        await runner.compression_benchmark("nonexistent_run")

    asyncio.run(scenario())


# ===========================================================================
# 7. persona_simulator_loop — state transitions
# ===========================================================================


def _make_persona(pid: str, queries: Optional[List[str]] = None) -> PersonaViewModel:
    return PersonaViewModel(
        id=pid,
        name=f"Test User {pid}",
        role="Online Shopper",
        department="Retail",
        archetype="power_user",
        goal="Find products quickly",
        orbit=1,
        colorSeed=42,
        queries=queries or ["shoes", "hats", "jackets"],
    )


def test_persona_simulator_transitions_states() -> None:
    async def scenario() -> None:
        personas = [_make_persona("p1"), _make_persona("p2"), _make_persona("p3")]
        manager = RunManager()
        ctx = _make_run_context(run_id="run_persona", personas=personas)
        ctx.stage = "running"
        ctx.metrics.currentScore = 0.7
        manager.runs["run_persona"] = ctx

        # Collect published events
        published: List[Dict[str, Any]] = []
        original_publish = manager.publish

        async def capture_publish(run_id: str, event: Dict[str, Any]) -> None:
            published.append(event)

        manager.publish = capture_publish

        runner = SearchTaskRunner(manager)

        # Run the loop briefly then cancel
        async def run_briefly() -> None:
            task = asyncio.create_task(runner.persona_simulator_loop("run_persona"))
            await asyncio.sleep(0.1)
            ctx.cancel_flag.set()
            await task

        await run_briefly()

        # Personas should have been searched at least once
        total_searches = sum(p.totalSearches for p in personas)
        assert total_searches > 0

        # Each persona should be in a valid state
        valid_states = {"idle", "searching", "success", "partial", "failure", "reacting"}
        for persona in personas:
            assert persona.state in valid_states

        # At least one persona.batch event should have been published
        batch_events = [e for e in published if e["type"] == "persona.batch"]
        assert len(batch_events) > 0

    asyncio.run(scenario())


def test_persona_simulator_empty_personas() -> None:
    """With no personas, the loop should just sleep and exit on cancel."""

    async def scenario() -> None:
        manager = RunManager()
        ctx = _make_run_context(run_id="run_empty_persona", personas=[])
        ctx.stage = "running"
        manager.runs["run_empty_persona"] = ctx

        runner = SearchTaskRunner(manager)

        task = asyncio.create_task(runner.persona_simulator_loop("run_empty_persona"))
        await asyncio.sleep(0.05)
        ctx.cancel_flag.set()
        await task

        # No crash, no personas modified

    asyncio.run(scenario())


def test_persona_simulator_success_rate_updates() -> None:
    async def scenario() -> None:
        personas = [_make_persona("p1"), _make_persona("p2"), _make_persona("p3")]
        manager = RunManager()
        ctx = _make_run_context(run_id="run_rate", personas=personas)
        ctx.stage = "running"
        ctx.metrics.currentScore = 0.9  # High score → more successes
        manager.runs["run_rate"] = ctx

        async def noop_publish(run_id: str, event: Dict[str, Any]) -> None:
            pass

        manager.publish = noop_publish
        runner = SearchTaskRunner(manager)

        task = asyncio.create_task(runner.persona_simulator_loop("run_rate"))
        await asyncio.sleep(0.1)
        ctx.cancel_flag.set()
        await task

        # personaSuccessRate should have been set
        assert ctx.metrics.personaSuccessRate >= 0.0

    asyncio.run(scenario())


def test_persona_simulator_nonexistent_run() -> None:
    async def scenario() -> None:
        manager = RunManager()
        runner = SearchTaskRunner(manager)
        # Should return immediately without error
        await runner.persona_simulator_loop("nonexistent_run")

    asyncio.run(scenario())


# ===========================================================================
# 8. metrics_heartbeat — publishes metrics
# ===========================================================================


def test_metrics_heartbeat_publishes_ticks() -> None:
    async def scenario() -> None:
        manager = RunManager()
        ctx = _make_run_context(run_id="run_hb")
        ctx.stage = "running"
        manager.runs["run_hb"] = ctx

        published: List[Dict[str, Any]] = []

        async def capture_publish(run_id: str, event: Dict[str, Any]) -> None:
            published.append(event)

        manager.publish = capture_publish
        runner = SearchTaskRunner(manager)

        task = asyncio.create_task(runner.metrics_heartbeat("run_hb"))
        await asyncio.sleep(0.15)
        ctx.cancel_flag.set()
        await task

        tick_events = [e for e in published if e["type"] == "metrics.tick"]
        assert len(tick_events) >= 1
        # Payload should contain the metrics model
        payload = tick_events[0]["payload"]
        assert "currentScore" in payload
        assert "elapsedSeconds" in payload
        assert payload["elapsedSeconds"] >= 0

    asyncio.run(scenario())


def test_metrics_heartbeat_updates_elapsed_seconds() -> None:
    async def scenario() -> None:
        manager = RunManager()
        ctx = _make_run_context(run_id="run_hb2")
        ctx.stage = "running"
        manager.runs["run_hb2"] = ctx

        async def noop_publish(run_id: str, event: Dict[str, Any]) -> None:
            pass

        manager.publish = noop_publish
        runner = SearchTaskRunner(manager)

        task = asyncio.create_task(runner.metrics_heartbeat("run_hb2"))
        await asyncio.sleep(0.15)
        ctx.cancel_flag.set()
        await task

        # elapsedSeconds should have been updated
        assert ctx.metrics.elapsedSeconds > 0

    asyncio.run(scenario())


def test_metrics_heartbeat_nonexistent_run() -> None:
    async def scenario() -> None:
        manager = RunManager()
        runner = SearchTaskRunner(manager)
        # Should return immediately without error
        await runner.metrics_heartbeat("nonexistent_run")

    asyncio.run(scenario())


def test_metrics_heartbeat_stops_on_completed_stage() -> None:
    async def scenario() -> None:
        manager = RunManager()
        ctx = _make_run_context(run_id="run_hb3")
        ctx.stage = "completed"
        manager.runs["run_hb3"] = ctx

        published: List[Dict[str, Any]] = []

        async def capture_publish(run_id: str, event: Dict[str, Any]) -> None:
            published.append(event)

        manager.publish = capture_publish
        runner = SearchTaskRunner(manager)

        # Stage is "completed" so the while loop condition is False immediately
        await runner.metrics_heartbeat("run_hb3")

        assert len(published) == 0

    asyncio.run(scenario())
