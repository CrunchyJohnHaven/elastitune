from __future__ import annotations

from backend.models.contracts import ExperimentRecord, SearchProfileChange
from backend.models.runtime import RunContext
from backend.services.demo_service import DemoService
from backend.services.report_service import ReportService


def test_report_service_generates_structured_summary_with_real_duration() -> None:
    demo = DemoService()
    connection = demo.create_connection("conn_test")
    ctx = RunContext(
        run_id="run_test",
        connection=connection,
        personas=[],
        max_experiments=10,
        duration_minutes=5,
        auto_stop_on_plateau=True,
    )

    change = SearchProfileChange(
        path="phraseBoost",
        before=0.0,
        after=1.0,
        label="phrase boost 0.0 → 1.0",
    )
    ctx.experiments = [
        ExperimentRecord(
            experimentId=1,
            timestamp="2026-03-25T21:00:00Z",
            hypothesis=change.label,
            change=change,
            baselineScore=0.41,
            candidateScore=0.49,
            deltaAbsolute=0.08,
            deltaPercent=19.5,
            decision="kept",
            durationMs=2300,
            queryFailuresBefore=[],
            queryFailuresAfter=[],
        )
    ]
    ctx.metrics.baselineScore = 0.41
    ctx.metrics.bestScore = 0.49
    ctx.metrics.currentScore = 0.49
    ctx.metrics.experimentsRun = 1
    ctx.metrics.improvementsKept = 1
    ctx.metrics.improvementPct = 19.5
    ctx.metrics.elapsedSeconds = 125

    report = ReportService().generate(ctx)

    assert report.summary.headline == (
        f"Search quality improved +19.5% on {ctx.summary.baselineEvalCount} test queries."
    )
    assert report.summary.durationSeconds == 125
    assert "about 2 minutes" in report.summary.overview
    assert "phrase boost 0.0 → 1.0" in report.summary.overview
    assert len(report.summary.nextSteps) == 3
    assert report.summary.nextSteps[0].startswith("Review the accepted profile changes")
