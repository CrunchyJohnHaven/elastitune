"""
Comprehensive unit tests for WebSocket handler support, routes service layer,
RunManager pub/sub, and search-profile experiment helpers.
"""
from __future__ import annotations

import asyncio
import copy
from typing import List

import pytest

from backend.models.contracts import (
    ExperimentRecord,
    LlmConfig,
    RunSnapshot,
    SearchProfile,
    SearchProfileChange,
    LexicalFieldEntry,
)
from backend.models.runtime import ConnectionContext, RunContext
from backend.services.demo_service import DemoService, _apply_profile_change as demo_apply
from backend.services.run_manager import (
    RunManager,
    _apply_profile_change,
    _heuristic_next_experiment,
    _hypothesis_text,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_connection(connection_id: str = "conn_test") -> ConnectionContext:
    return DemoService().create_connection(connection_id)


def _make_run_context(
    run_id: str = "run_test",
    connection_id: str = "conn_test",
) -> RunContext:
    conn = _make_connection(connection_id)
    return RunContext(
        run_id=run_id,
        connection=conn,
        personas=[],
        max_experiments=5,
        duration_minutes=1,
        auto_stop_on_plateau=False,
    )


def _make_snapshot(run_id: str = "run_snap") -> RunSnapshot:
    ctx = _make_run_context(run_id=run_id)
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
    )


# ===================================================================
# 1. RunManager pub/sub: publish / subscribe / unsubscribe
# ===================================================================

def test_pubsub_events_flow_through_queues() -> None:
    async def scenario() -> None:
        rm = RunManager()
        run_id = "run_ps"
        ctx = _make_run_context(run_id=run_id)
        await rm.create_run(run_id, ctx)

        q1 = await rm.subscribe(run_id)
        q2 = await rm.subscribe(run_id)

        event = {"type": "test.event", "payload": {"value": 42}}
        await rm.publish(run_id, event)

        e1 = q1.get_nowait()
        e2 = q2.get_nowait()
        assert e1 == event
        assert e2 == event

        # After unsubscribe, the queue should no longer receive events
        await rm.unsubscribe(run_id, q1)
        await rm.publish(run_id, {"type": "second"})

        assert q1.empty()
        assert not q2.empty()
        assert q2.get_nowait()["type"] == "second"

    asyncio.run(scenario())


def test_publish_to_nonexistent_run_does_not_error() -> None:
    async def scenario() -> None:
        rm = RunManager()
        # Publishing to a run with no subscribers should silently succeed
        await rm.publish("nonexistent_run", {"type": "noop"})

    asyncio.run(scenario())


def test_subscribe_creates_subscriber_set_if_missing() -> None:
    async def scenario() -> None:
        rm = RunManager()
        # subscribe without create_run first
        q = await rm.subscribe("orphan_run")
        assert q is not None
        assert "orphan_run" in rm.subscribers

    asyncio.run(scenario())


# ===================================================================
# 2. RunManager.create_run and get_snapshot
# ===================================================================

def test_create_run_and_get_snapshot() -> None:
    async def scenario() -> None:
        rm = RunManager()
        run_id = "run_snap_test"
        ctx = _make_run_context(run_id=run_id)
        await rm.create_run(run_id, ctx)

        snapshot = await rm.get_snapshot(run_id)
        assert snapshot is not None
        assert snapshot.runId == run_id
        assert snapshot.mode == "demo"
        assert snapshot.stage == "starting"
        assert snapshot.summary.indexName == ctx.summary.indexName

    asyncio.run(scenario())


def test_get_snapshot_returns_none_for_unknown_run() -> None:
    async def scenario() -> None:
        rm = RunManager()
        snapshot = await rm.get_snapshot("does_not_exist")
        assert snapshot is None

    asyncio.run(scenario())


def test_get_run_returns_context() -> None:
    async def scenario() -> None:
        rm = RunManager()
        run_id = "run_ctx_test"
        ctx = _make_run_context(run_id=run_id)
        await rm.create_run(run_id, ctx)

        result = await rm.get_run(run_id)
        assert result is ctx

    asyncio.run(scenario())


# ===================================================================
# 3. RunManager.stop_run
# ===================================================================

def test_stop_run_sets_cancel_flag_and_stage() -> None:
    async def scenario() -> None:
        rm = RunManager()
        run_id = "run_stop"
        ctx = _make_run_context(run_id=run_id)
        await rm.create_run(run_id, ctx)

        q = await rm.subscribe(run_id)

        assert not ctx.cancel_flag.is_set()
        assert ctx.stage == "starting"

        await rm.stop_run(run_id)

        assert ctx.cancel_flag.is_set()
        assert ctx.stage == "stopping"

        # A stage event should have been published
        event = q.get_nowait()
        assert event["type"] == "run.stage"
        assert event["payload"]["stage"] == "stopping"

    asyncio.run(scenario())


def test_stop_run_on_nonexistent_run_is_noop() -> None:
    async def scenario() -> None:
        rm = RunManager()
        # Should not raise
        await rm.stop_run("ghost_run")

    asyncio.run(scenario())


# ===================================================================
# 4. RunManager.get_connection: cache hit and miss
# ===================================================================

def test_get_connection_cache_hit() -> None:
    async def scenario() -> None:
        rm = RunManager()
        conn = _make_connection("conn_hit")
        await rm.create_connection("conn_hit", conn)

        result = await rm.get_connection("conn_hit")
        assert result is conn

    asyncio.run(scenario())


def test_get_connection_cache_miss_no_persistence() -> None:
    async def scenario() -> None:
        rm = RunManager()
        result = await rm.get_connection("conn_miss")
        assert result is None

    asyncio.run(scenario())


# ===================================================================
# 5. RunSnapshot.sanitize_for_client: deep copy
# ===================================================================

def test_sanitize_for_client_returns_deep_copy() -> None:
    snapshot = _make_snapshot("run_sanitize")
    sanitized = snapshot.sanitize_for_client()

    assert sanitized is not snapshot
    assert sanitized.runId == snapshot.runId
    assert sanitized.metrics is not snapshot.metrics
    assert sanitized.summary is not snapshot.summary

    # Mutating the sanitized copy should not affect the original
    sanitized.warnings.append("injected")
    assert "injected" not in snapshot.warnings


def test_sanitize_preserves_all_fields() -> None:
    snapshot = _make_snapshot("run_fields")
    snapshot.warnings = ["w1"]
    sanitized = snapshot.sanitize_for_client()

    assert sanitized.warnings == ["w1"]
    assert sanitized.stage == snapshot.stage
    assert sanitized.mode == snapshot.mode


# ===================================================================
# 6. LlmConfig.sanitize_for_client: apiKey stripped
# ===================================================================

def test_llm_config_sanitize_strips_api_key() -> None:
    config = LlmConfig(
        provider="openai",
        baseUrl="https://api.openai.com",
        model="gpt-4",
        apiKey="sk-supersecret",
    )
    sanitized = config.sanitize_for_client()

    assert sanitized.apiKey is None
    assert sanitized.provider == "openai"
    assert sanitized.baseUrl == "https://api.openai.com"
    assert sanitized.model == "gpt-4"

    # Original should still have the key
    assert config.apiKey == "sk-supersecret"


def test_llm_config_sanitize_when_no_key() -> None:
    config = LlmConfig(provider="disabled")
    sanitized = config.sanitize_for_client()
    assert sanitized.apiKey is None
    assert sanitized.provider == "disabled"


# ===================================================================
# 7. RunManager.list_search_runs with no persistence
# ===================================================================

def test_list_search_runs_no_persistence_returns_empty() -> None:
    async def scenario() -> None:
        rm = RunManager()
        result = await rm.list_search_runs()
        assert result == []

    asyncio.run(scenario())


def test_list_search_runs_with_filters_no_persistence() -> None:
    async def scenario() -> None:
        rm = RunManager()
        result = await rm.list_search_runs(
            limit=10,
            index_name="test-index",
            completed_only=True,
        )
        assert result == []

    asyncio.run(scenario())


# ===================================================================
# 8. _apply_profile_change: field boost and scalar properties
# ===================================================================

def test_apply_profile_change_field_boost() -> None:
    profile = SearchProfile(
        lexicalFields=[
            LexicalFieldEntry(field="title", boost=2.0),
            LexicalFieldEntry(field="description", boost=1.0),
        ]
    )
    change = SearchProfileChange(
        path="lexicalFields[0].boost",
        before=2.0,
        after=3.5,
        label="title boost 2.0 -> 3.5",
    )
    _apply_profile_change(profile, change)
    assert profile.lexicalFields[0].boost == 3.5
    assert profile.lexicalFields[1].boost == 1.0  # unchanged


def test_apply_profile_change_second_field() -> None:
    profile = SearchProfile(
        lexicalFields=[
            LexicalFieldEntry(field="title", boost=2.0),
            LexicalFieldEntry(field="body", boost=1.0),
        ]
    )
    change = SearchProfileChange(
        path="lexicalFields[1].boost",
        before=1.0,
        after=4.0,
        label="body boost 1.0 -> 4.0",
    )
    _apply_profile_change(profile, change)
    assert profile.lexicalFields[1].boost == 4.0


def test_apply_profile_change_scalar_property() -> None:
    profile = SearchProfile()
    assert profile.minimumShouldMatch == "75%"

    change = SearchProfileChange(
        path="minimumShouldMatch",
        before="75%",
        after="85%",
        label="minimumShouldMatch 75% -> 85%",
    )
    _apply_profile_change(profile, change)
    assert profile.minimumShouldMatch == "85%"


def test_apply_profile_change_tie_breaker() -> None:
    profile = SearchProfile(tieBreaker=0.0)
    change = SearchProfileChange(
        path="tieBreaker",
        before=0.0,
        after=0.3,
        label="Tie breaker 0.0 -> 0.3",
    )
    _apply_profile_change(profile, change)
    assert profile.tieBreaker == 0.3


def test_apply_profile_change_fuzziness() -> None:
    profile = SearchProfile(fuzziness="0")
    change = SearchProfileChange(
        path="fuzziness", before="0", after="AUTO", label="fuzziness 0 -> AUTO"
    )
    _apply_profile_change(profile, change)
    assert profile.fuzziness == "AUTO"


def test_apply_profile_change_use_vector() -> None:
    profile = SearchProfile(useVector=False)
    change = SearchProfileChange(
        path="useVector", before=False, after=True, label="Hybrid search enabled"
    )
    _apply_profile_change(profile, change)
    assert profile.useVector is True


def test_apply_profile_change_out_of_bounds_index_does_not_crash() -> None:
    profile = SearchProfile(
        lexicalFields=[LexicalFieldEntry(field="title", boost=1.0)]
    )
    change = SearchProfileChange(
        path="lexicalFields[99].boost",
        before=1.0,
        after=5.0,
        label="out of bounds",
    )
    # Should not raise — just silently skip
    _apply_profile_change(profile, change)
    assert profile.lexicalFields[0].boost == 1.0


def test_apply_profile_change_nonexistent_attr_does_not_crash() -> None:
    profile = SearchProfile()
    change = SearchProfileChange(
        path="nonExistentField",
        before=None,
        after="value",
        label="noop",
    )
    _apply_profile_change(profile, change)


# ===================================================================
# 9. _heuristic_next_experiment: grid sweep generates valid changes
# ===================================================================

def test_heuristic_next_experiment_first_call_returns_change() -> None:
    profile = SearchProfile(
        lexicalFields=[
            LexicalFieldEntry(field="title", boost=2.0),
            LexicalFieldEntry(field="description", boost=1.0),
        ]
    )
    change = _heuristic_next_experiment(profile, [])
    assert change is not None
    assert isinstance(change, SearchProfileChange)
    assert change.path is not None
    assert change.after is not None
    assert change.before is not None


def test_heuristic_next_experiment_avoids_already_tried() -> None:
    profile = SearchProfile(
        lexicalFields=[
            LexicalFieldEntry(field="title", boost=2.0),
        ]
    )
    first = _heuristic_next_experiment(profile, [])
    assert first is not None

    # Build a fake history with that experiment
    record = ExperimentRecord(
        experimentId=1,
        timestamp="2024-01-01T00:00:00Z",
        hypothesis="test",
        change=first,
        beforeScore=0.5,
        candidateScore=0.55,
        deltaAbsolute=0.05,
        deltaPercent=10.0,
        decision="kept",
        durationMs=100,
    )
    second = _heuristic_next_experiment(profile, [record])
    assert second is not None
    # Should not be the exact same (path, after) pair
    assert not (second.path == first.path and second.after == first.after)


def test_heuristic_next_experiment_always_returns_something() -> None:
    """Even with a large history, the heuristic should never return None."""
    profile = SearchProfile(
        lexicalFields=[
            LexicalFieldEntry(field="title", boost=2.0),
            LexicalFieldEntry(field="description", boost=1.0),
        ]
    )
    history: List[ExperimentRecord] = []
    for i in range(50):
        change = _heuristic_next_experiment(profile, history)
        assert change is not None
        history.append(
            ExperimentRecord(
                experimentId=i + 1,
                timestamp="2024-01-01T00:00:00Z",
                hypothesis="test",
                change=change,
                beforeScore=0.5,
                candidateScore=0.52,
                deltaAbsolute=0.02,
                deltaPercent=4.0,
                decision="kept" if i % 2 == 0 else "reverted",
                durationMs=100,
            )
        )


def test_heuristic_returns_valid_search_profile_paths() -> None:
    """Each generated change should reference a real SearchProfile attribute
    or a lexicalFields[N].boost path."""
    import re

    profile = SearchProfile(
        lexicalFields=[
            LexicalFieldEntry(field="title", boost=2.0),
            LexicalFieldEntry(field="description", boost=1.0),
        ]
    )
    valid_attrs = set(SearchProfile.model_fields.keys())

    for _ in range(20):
        change = _heuristic_next_experiment(profile, [])
        if change is None:
            break
        if re.match(r"lexicalFields\[\d+\]\.boost", change.path):
            continue
        assert change.path in valid_attrs, f"Unexpected path: {change.path}"


# ===================================================================
# 10. _hypothesis_text: test hypothesis generation for various changes
# ===================================================================

def test_hypothesis_text_field_boost_increase() -> None:
    change = SearchProfileChange(
        path="lexicalFields[0].boost",
        before=1.0,
        after=3.0,
        label="title boost 1.0 -> 3.0",
    )
    text = _hypothesis_text(change)
    assert "title" in text.lower() or "increase" in text.lower()
    assert len(text) > 10


def test_hypothesis_text_field_boost_decrease() -> None:
    change = SearchProfileChange(
        path="lexicalFields[0].boost",
        before=3.0,
        after=1.0,
        label="title boost 3.0 -> 1.0",
    )
    text = _hypothesis_text(change)
    assert "title" in text.lower() or "reduce" in text.lower()
    assert len(text) > 10


def test_hypothesis_text_multi_match_type() -> None:
    change = SearchProfileChange(
        path="multiMatchType",
        before="best_fields",
        after="cross_fields",
        label="multiMatchType best_fields -> cross_fields",
    )
    text = _hypothesis_text(change)
    assert "cross" in text.lower() or "field" in text.lower()


def test_hypothesis_text_minimum_should_match_increase() -> None:
    change = SearchProfileChange(
        path="minimumShouldMatch",
        before="75%",
        after="85%",
        label="minimumShouldMatch 75% -> 85%",
    )
    text = _hypothesis_text(change)
    assert "tighten" in text.lower() or "match" in text.lower()


def test_hypothesis_text_minimum_should_match_decrease() -> None:
    change = SearchProfileChange(
        path="minimumShouldMatch",
        before="85%",
        after="60%",
        label="minimumShouldMatch 85% -> 60%",
    )
    text = _hypothesis_text(change)
    assert "relax" in text.lower() or "match" in text.lower()


def test_hypothesis_text_fuzziness_to_auto() -> None:
    change = SearchProfileChange(
        path="fuzziness", before="0", after="AUTO", label="fuzziness 0 -> AUTO"
    )
    text = _hypothesis_text(change)
    assert "fuzzy" in text.lower() or "typo" in text.lower() or "tolerant" in text.lower()


def test_hypothesis_text_fuzziness_to_zero() -> None:
    change = SearchProfileChange(
        path="fuzziness", before="AUTO", after="0", label="fuzziness AUTO -> 0"
    )
    text = _hypothesis_text(change)
    assert "fuzzy" in text.lower() or "precision" in text.lower()


def test_hypothesis_text_phrase_boost() -> None:
    change = SearchProfileChange(
        path="phraseBoost", before=0.0, after=2.0, label="phraseBoost 0.0 -> 2.0"
    )
    text = _hypothesis_text(change)
    assert "phrase" in text.lower()


def test_hypothesis_text_tie_breaker() -> None:
    change = SearchProfileChange(
        path="tieBreaker", before=0.0, after=0.3, label="tieBreaker 0.0 -> 0.3"
    )
    text = _hypothesis_text(change)
    assert "field" in text.lower() or "rebalance" in text.lower()


def test_hypothesis_text_vector_weight_increase() -> None:
    change = SearchProfileChange(
        path="vectorWeight", before=0.3, after=0.5, label="vectorWeight 0.3 -> 0.5"
    )
    text = _hypothesis_text(change)
    assert "semantic" in text.lower() or "vector" in text.lower()


def test_hypothesis_text_vector_weight_decrease() -> None:
    change = SearchProfileChange(
        path="vectorWeight", before=0.5, after=0.2, label="vectorWeight 0.5 -> 0.2"
    )
    text = _hypothesis_text(change)
    assert "lexical" in text.lower() or "ranking" in text.lower()


def test_hypothesis_text_fusion_method_rrf() -> None:
    change = SearchProfileChange(
        path="fusionMethod",
        before="weighted_sum",
        after="rrf",
        label="fusionMethod weighted_sum -> rrf",
    )
    text = _hypothesis_text(change)
    assert "rrf" in text.lower() or "reciprocal" in text.lower() or "fusion" in text.lower()


def test_hypothesis_text_fusion_method_weighted_sum() -> None:
    change = SearchProfileChange(
        path="fusionMethod",
        before="rrf",
        after="weighted_sum",
        label="fusionMethod rrf -> weighted_sum",
    )
    text = _hypothesis_text(change)
    assert "weighted" in text.lower() or "fusion" in text.lower()


def test_hypothesis_text_rrf_rank_constant() -> None:
    change = SearchProfileChange(
        path="rrfRankConstant",
        before=60,
        after=80,
        label="rrfRankConstant 60 -> 80",
    )
    text = _hypothesis_text(change)
    assert "rank" in text.lower() or "reciprocal" in text.lower()


def test_hypothesis_text_knn_k() -> None:
    change = SearchProfileChange(
        path="knnK", before=20, after=50, label="knnK 20 -> 50"
    )
    text = _hypothesis_text(change)
    assert "semantic" in text.lower() or "vector" in text.lower() or "candidate" in text.lower()


def test_hypothesis_text_unknown_path_fallback() -> None:
    change = SearchProfileChange(
        path="somethingNew", before="a", after="b", label="somethingNew a -> b"
    )
    text = _hypothesis_text(change)
    assert "somethingNew" in text
    assert len(text) > 10


# ===================================================================
# Extra: _apply_profile_change from demo_service (simpler version)
# ===================================================================

def test_demo_apply_profile_change_scalar() -> None:
    profile = SearchProfile(phraseBoost=0.0)
    change = SearchProfileChange(
        path="phraseBoost", before=0.0, after=2.0, label="phraseBoost 0.0 -> 2.0"
    )
    demo_apply(profile, change)
    assert profile.phraseBoost == 2.0


# ===================================================================
# Extra: get_any_snapshot and get_any_run
# ===================================================================

def test_get_any_snapshot_returns_search_snapshot() -> None:
    async def scenario() -> None:
        rm = RunManager()
        run_id = "run_any"
        ctx = _make_run_context(run_id=run_id)
        await rm.create_run(run_id, ctx)

        snapshot = await rm.get_any_snapshot(run_id)
        assert snapshot is not None
        assert snapshot.runId == run_id

    asyncio.run(scenario())


def test_get_any_snapshot_returns_none_for_unknown() -> None:
    async def scenario() -> None:
        rm = RunManager()
        result = await rm.get_any_snapshot("unknown")
        assert result is None

    asyncio.run(scenario())


def test_get_any_run_returns_search_context() -> None:
    async def scenario() -> None:
        rm = RunManager()
        run_id = "run_any_ctx"
        ctx = _make_run_context(run_id=run_id)
        await rm.create_run(run_id, ctx)

        result = await rm.get_any_run(run_id)
        assert result is ctx

    asyncio.run(scenario())


def test_get_any_run_returns_none_for_unknown() -> None:
    async def scenario() -> None:
        rm = RunManager()
        result = await rm.get_any_run("unknown")
        assert result is None

    asyncio.run(scenario())


# ===================================================================
# Extra: Multiple subscribers and full-queue handling
# ===================================================================

def test_publish_drops_events_when_queue_is_full() -> None:
    async def scenario() -> None:
        rm = RunManager()
        run_id = "run_full_q"
        ctx = _make_run_context(run_id=run_id)
        await rm.create_run(run_id, ctx)

        q = await rm.subscribe(run_id)
        # Queue maxsize is 512; fill it up
        for i in range(512):
            await rm.publish(run_id, {"type": "fill", "i": i})

        assert q.full()

        # Next publish should not raise, but the full queue gets discarded
        await rm.publish(run_id, {"type": "overflow"})
        # The queue should have been removed from subscribers
        assert q not in rm.subscribers[run_id]

    asyncio.run(scenario())


def test_multiple_unsubscribe_is_safe() -> None:
    async def scenario() -> None:
        rm = RunManager()
        run_id = "run_double_unsub"
        ctx = _make_run_context(run_id=run_id)
        await rm.create_run(run_id, ctx)

        q = await rm.subscribe(run_id)
        await rm.unsubscribe(run_id, q)
        # Second unsubscribe should not raise
        await rm.unsubscribe(run_id, q)

    asyncio.run(scenario())


# ===================================================================
# Extra: _build_search_snapshot captures run config correctly
# ===================================================================

def test_build_search_snapshot_includes_run_config() -> None:
    async def scenario() -> None:
        rm = RunManager()
        run_id = "run_config"
        ctx = _make_run_context(run_id=run_id)
        ctx.max_experiments = 42
        ctx.duration_minutes = 15
        ctx.auto_stop_on_plateau = False
        await rm.create_run(run_id, ctx)

        snapshot = await rm.get_snapshot(run_id)
        assert snapshot is not None
        assert snapshot.runConfig.maxExperiments == 42
        assert snapshot.runConfig.durationMinutes == 15
        assert snapshot.runConfig.autoStopOnPlateau is False

    asyncio.run(scenario())
