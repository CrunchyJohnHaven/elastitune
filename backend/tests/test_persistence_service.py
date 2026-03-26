from __future__ import annotations

import asyncio

from backend.models.contracts import LlmConfig
from backend.models.runtime import RunContext
from backend.services.demo_service import DemoService
from backend.services.persistence_service import PersistenceService
from backend.services.report_service import ReportService
from backend.services.run_manager import RunManager


def test_persisted_snapshot_and_report_survive_new_run_manager(tmp_path) -> None:
    async def scenario() -> None:
        persistence = PersistenceService(db_path=str(tmp_path / "elastitune-test.db"))
        await persistence.init()

        connection = DemoService().create_connection("conn_persist")
        connection.api_key = "es-secret"
        connection.llm_config = LlmConfig(
            provider="openai_compatible",
            baseUrl="https://example.com/v1",
            model="gpt-test",
            apiKey="llm-secret",
        )
        ctx = RunContext(
            run_id="run_persist",
            connection=connection,
            personas=[],
            max_experiments=3,
            duration_minutes=1,
            auto_stop_on_plateau=True,
        )
        ctx.stage = "completed"
        ctx.metrics.baselineScore = 0.41
        ctx.metrics.currentScore = 0.47
        ctx.metrics.bestScore = 0.47
        ctx.metrics.improvementPct = 14.63
        ctx.metrics.experimentsRun = 3
        ctx.metrics.elapsedSeconds = 42
        ctx.report = ReportService().generate(ctx)

        manager = RunManager(persistence=persistence)
        await manager.create_connection("conn_persist", connection)
        await manager.create_run("run_persist", ctx)
        await persistence.save_snapshot(await manager.get_snapshot("run_persist"))
        await persistence.save_report(ctx.report)

        restored_manager = RunManager(persistence=persistence)
        restored_snapshot = await restored_manager.get_snapshot("run_persist")
        restored_report = await restored_manager.get_report("run_persist")
        restored_connection = await restored_manager.get_connection("conn_persist")
        completed_runs = await restored_manager.list_search_runs(
            limit=10,
            index_name=connection.summary.indexName,
            completed_only=True,
        )

        assert restored_snapshot is not None
        assert restored_snapshot.stage == "completed"
        assert restored_snapshot.metrics.bestScore == 0.47
        assert restored_report is not None
        assert restored_report.runId == "run_persist"
        assert restored_report.summary.durationSeconds == 42
        assert restored_report.connectionConfig is not None
        assert (
            restored_report.connectionConfig.indexName == connection.summary.indexName
        )
        assert restored_report.connectionConfig.apiKey is None
        assert restored_report.connectionConfig.hasApiKey is True
        assert restored_report.connectionConfig.llm is not None
        assert restored_report.connectionConfig.llm.apiKey is None
        assert restored_connection is not None
        assert restored_connection.index_name == connection.summary.indexName
        assert restored_connection.api_key is None
        assert restored_connection.llm_config is not None
        assert restored_connection.llm_config.apiKey is None
        assert len(completed_runs) == 1
        assert completed_runs[0]["run_id"] == "run_persist"

    asyncio.run(scenario())


def test_loading_nonexistent_run_returns_none(tmp_path) -> None:
    """Loading a run that was never persisted should return None gracefully."""

    async def scenario() -> None:
        persistence = PersistenceService(db_path=str(tmp_path / "test-missing.db"))
        await persistence.init()

        snapshot = await persistence.load_snapshot("run_does_not_exist")
        report = await persistence.load_report("run_does_not_exist")
        connection = await persistence.load_connection("conn_does_not_exist")

        assert snapshot is None
        assert report is None
        assert connection is None

    asyncio.run(scenario())


def test_persist_and_load_report_with_continuation_fields(tmp_path) -> None:
    """Persisting a continuation report and reloading it should preserve continuation fields."""

    async def scenario() -> None:
        persistence = PersistenceService(db_path=str(tmp_path / "cont-test.db"))
        await persistence.init()

        connection = DemoService().create_connection("conn_cont")
        ctx = RunContext(
            run_id="run_cont",
            connection=connection,
            personas=[],
            max_experiments=3,
            duration_minutes=1,
            auto_stop_on_plateau=True,
        )
        ctx.stage = "completed"
        ctx.metrics.baselineScore = 0.565
        ctx.metrics.currentScore = 0.595
        ctx.metrics.bestScore = 0.595
        ctx.metrics.improvementPct = 29.6
        ctx.metrics.experimentsRun = 5
        ctx.metrics.elapsedSeconds = 30
        ctx.metrics.originalBaselineScore = 0.459
        ctx.metrics.priorExperimentsRun = 50
        ctx.metrics.priorImprovementsKept = 8

        # Set continuation context on the RunContext itself
        ctx.previous_run_id = "run_prev_001"
        ctx.original_baseline_score = 0.459
        ctx.prior_experiments_run = 50
        ctx.prior_improvements_kept = 8

        ctx.report = ReportService().generate(ctx)

        manager = RunManager(persistence=persistence)
        await manager.create_connection("conn_cont", connection)
        await manager.create_run("run_cont", ctx)
        await persistence.save_snapshot(await manager.get_snapshot("run_cont"))
        await persistence.save_report(ctx.report)

        restored_report = await persistence.load_report("run_cont")
        assert restored_report is not None
        assert restored_report.runId == "run_cont"
        assert restored_report.previousRunId == "run_prev_001"
        assert restored_report.summary.isContinuation is True
        assert restored_report.summary.originalBaselineScore == 0.459

    asyncio.run(scenario())
