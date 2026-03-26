from __future__ import annotations

import asyncio

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
        assert restored_report.connectionConfig.indexName == connection.summary.indexName
        assert restored_connection is not None
        assert restored_connection.index_name == connection.summary.indexName
        assert len(completed_runs) == 1
        assert completed_runs[0]["run_id"] == "run_persist"

    asyncio.run(scenario())
