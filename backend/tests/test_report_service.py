from __future__ import annotations


from backend.models.contracts import (
    ExperimentRecord,
    PersonaViewModel,
    SearchProfileChange,
)
from backend.models.runtime import RunContext
from backend.services.demo_service import DemoService
from backend.services.report_service import ReportService


def _make_change(label: str = "phrase boost 0.0 → 1.0") -> SearchProfileChange:
    return SearchProfileChange(
        path="phraseBoost",
        before=0.0,
        after=1.0,
        label=label,
    )


def _make_experiment(
    exp_id: int,
    baseline: float,
    candidate: float,
    decision: str = "kept",
    label: str = "phrase boost 0.0 → 1.0",
    duration_ms: int = 2300,
) -> ExperimentRecord:
    change = _make_change(label)
    return ExperimentRecord(
        experimentId=exp_id,
        timestamp="2026-03-25T21:00:00Z",
        hypothesis=change.label,
        change=change,
        baselineScore=baseline,
        candidateScore=candidate,
        deltaAbsolute=round(candidate - baseline, 4),
        deltaPercent=round(((candidate - baseline) / max(baseline, 0.001)) * 100, 1),
        decision=decision,
        durationMs=duration_ms,
        queryFailuresBefore=[],
        queryFailuresAfter=[],
    )


def _make_ctx(
    *,
    run_id: str = "run_test",
    baseline_score: float = 0.41,
    best_score: float = 0.49,
    experiments_run: int = 1,
    improvements_kept: int = 1,
    improvement_pct: float = 19.5,
    elapsed_seconds: float = 125,
    experiments: list[ExperimentRecord] | None = None,
    previous_run_id: str | None = None,
    original_baseline_score: float | None = None,
    prior_experiments_run: int = 0,
    prior_improvements_kept: int = 0,
    prior_experiments: list[ExperimentRecord] | None = None,
) -> RunContext:
    demo = DemoService()
    connection = demo.create_connection("conn_test")
    ctx = RunContext(
        run_id=run_id,
        connection=connection,
        personas=[],
        max_experiments=10,
        duration_minutes=5,
        auto_stop_on_plateau=True,
    )

    if experiments is None:
        experiments = [_make_experiment(1, baseline_score, best_score)]

    ctx.experiments = experiments
    ctx.metrics.baselineScore = baseline_score
    ctx.metrics.bestScore = best_score
    ctx.metrics.currentScore = best_score
    ctx.metrics.experimentsRun = experiments_run
    ctx.metrics.improvementsKept = improvements_kept
    ctx.metrics.improvementPct = improvement_pct
    ctx.metrics.elapsedSeconds = elapsed_seconds

    # Continuation fields
    ctx.previous_run_id = previous_run_id
    ctx.original_baseline_score = original_baseline_score
    ctx.prior_experiments_run = prior_experiments_run
    ctx.prior_improvements_kept = prior_improvements_kept
    ctx.prior_experiments = prior_experiments or []

    return ctx


# ------------------------------------------------------------------
# Original (non-continuation) tests
# ------------------------------------------------------------------


class TestReportServiceBasic:
    """Tests for single-run (non-continuation) reports."""

    def test_generates_structured_summary_with_real_duration(self) -> None:
        ctx = _make_ctx()
        report = ReportService().generate(ctx)

        assert report.summary.headline == (
            f"Search quality improved +19.5% on {ctx.summary.baselineEvalCount} test queries."
        )
        assert report.summary.durationSeconds == 125
        assert "about 2 minutes" in report.summary.overview
        assert "phrase boost 0.0 → 1.0" in report.summary.overview
        assert len(report.summary.nextSteps) == 3
        assert report.summary.nextSteps[0].startswith(
            "Review the accepted profile changes"
        )
        assert report.summary.confidenceScore > 0.5
        assert report.summary.personaCount == 0

    def test_non_continuation_flags_are_false(self) -> None:
        ctx = _make_ctx()
        report = ReportService().generate(ctx)

        assert report.summary.isContinuation is False
        assert report.summary.originalBaselineScore is None
        assert report.summary.totalExperimentsRun is None
        assert report.summary.totalImprovementsKept is None

    def test_baseline_score_matches_metrics(self) -> None:
        ctx = _make_ctx(baseline_score=0.35, best_score=0.50)
        report = ReportService().generate(ctx)

        assert report.summary.baselineScore == 0.35
        assert report.summary.bestScore == 0.50

    def test_improvement_pct_calculated_correctly(self) -> None:
        ctx = _make_ctx(baseline_score=0.40, best_score=0.50)
        report = ReportService().generate(ctx)

        expected_pct = ((0.50 - 0.40) / 0.40) * 100  # 25.0%
        assert abs(report.summary.improvementPct - expected_pct) < 0.1

    def test_experiments_count_is_current_run_only(self) -> None:
        experiments = [
            _make_experiment(1, 0.41, 0.45, "kept", "change A"),
            _make_experiment(2, 0.45, 0.44, "reverted", "change B"),
            _make_experiment(3, 0.45, 0.49, "kept", "change C"),
        ]
        ctx = _make_ctx(
            experiments=experiments,
            experiments_run=3,
            improvements_kept=2,
        )
        report = ReportService().generate(ctx)

        assert report.summary.experimentsRun == 3
        assert report.summary.improvementsKept == 2

    def test_no_previous_run_id_means_not_continuation(self) -> None:
        ctx = _make_ctx()
        report = ReportService().generate(ctx)

        assert report.previousRunId is None
        assert "multiple optimization runs" not in report.summary.overview

    def test_overview_mentions_single_run_format(self) -> None:
        ctx = _make_ctx()
        report = ReportService().generate(ctx)

        assert "for about" in report.summary.overview
        assert "ran 1 experiments" in report.summary.overview

    def test_report_includes_plain_english_narrative_sections(self) -> None:
        ctx = _make_ctx()
        report = ReportService().generate(ctx)

        section_keys = [section.key for section in report.narrative]
        assert "plain_english_summary" in section_keys
        assert "implementation_readout" in section_keys

    def test_report_includes_implementation_guide_with_line_numbers(self) -> None:
        ctx = _make_ctx()
        ctx.baseline_profile.phraseBoost = 0.0
        ctx.best_profile.phraseBoost = 1.0
        report = ReportService().generate(ctx)

        assert report.implementationGuide is not None
        assert report.implementationGuide.snippets
        snippet = report.implementationGuide.snippets[0]
        assert snippet.beforeLines[0].lineNumber == 1
        assert snippet.afterLines[0].lineNumber == 1
        assert any(line.changed for line in snippet.afterLines)

    def test_report_includes_change_narratives(self) -> None:
        ctx = _make_ctx()
        ctx.baseline_profile.phraseBoost = 0.0
        ctx.best_profile.phraseBoost = 1.0
        report = ReportService().generate(ctx)

        assert report.changeNarratives
        assert "phrase" in report.changeNarratives[0].plainEnglish.lower()
        assert report.changeNarratives[0].confidence > 0.5


# ------------------------------------------------------------------
# Continuation (multi-run chain) tests
# ------------------------------------------------------------------


class TestReportServiceContinuation:
    """Tests for continued runs showing cumulative improvement."""

    def test_continuation_uses_original_baseline_score(self) -> None:
        """The critical fix: report should show original baseline, not this run's baseline."""
        ctx = _make_ctx(
            baseline_score=0.565,  # This run's baseline (inherited best from run 1)
            best_score=0.595,
            previous_run_id="run_prev_001",
            original_baseline_score=0.459,  # The ORIGINAL baseline from run 1
        )
        report = ReportService().generate(ctx)

        # Report baseline should be the original, not this run's
        assert report.summary.baselineScore == 0.459
        assert report.summary.bestScore == 0.595

    def test_continuation_improvement_pct_is_cumulative(self) -> None:
        """Improvement % should be computed from original baseline, not current run's baseline."""
        ctx = _make_ctx(
            baseline_score=0.565,
            best_score=0.595,
            previous_run_id="run_prev_001",
            original_baseline_score=0.459,
        )
        report = ReportService().generate(ctx)

        # Expected: (0.595 - 0.459) / 0.459 * 100 ≈ 29.6%
        expected_pct = ((0.595 - 0.459) / 0.459) * 100
        assert abs(report.summary.improvementPct - expected_pct) < 0.1
        assert (
            report.summary.improvementPct > 25
        )  # Definitely not ~5.3% (run-only delta)

    def test_continuation_headline_shows_cumulative_improvement(self) -> None:
        ctx = _make_ctx(
            baseline_score=0.565,
            best_score=0.595,
            previous_run_id="run_prev_001",
            original_baseline_score=0.459,
        )
        report = ReportService().generate(ctx)

        # Headline should reflect cumulative improvement (~29.6%), not run-only (~5.3%)
        assert "+29." in report.summary.headline or "+30." in report.summary.headline

    def test_continuation_flags_are_set(self) -> None:
        ctx = _make_ctx(
            previous_run_id="run_prev_001",
            original_baseline_score=0.459,
            prior_experiments_run=50,
            prior_improvements_kept=8,
            experiments_run=15,
            improvements_kept=3,
        )
        report = ReportService().generate(ctx)

        assert report.summary.isContinuation is True
        assert report.summary.originalBaselineScore == 0.459

    def test_continuation_total_experiments_are_cumulative(self) -> None:
        ctx = _make_ctx(
            previous_run_id="run_prev_001",
            original_baseline_score=0.459,
            prior_experiments_run=50,
            prior_improvements_kept=8,
            experiments_run=15,
            improvements_kept=3,
        )
        report = ReportService().generate(ctx)

        assert report.summary.totalExperimentsRun == 65  # 50 + 15
        assert report.summary.totalImprovementsKept == 11  # 8 + 3

    def test_continuation_overview_mentions_multiple_runs(self) -> None:
        ctx = _make_ctx(
            previous_run_id="run_prev_001",
            original_baseline_score=0.459,
            prior_experiments_run=50,
            prior_improvements_kept=8,
            experiments_run=15,
            improvements_kept=3,
        )
        report = ReportService().generate(ctx)

        assert "multiple optimization runs" in report.summary.overview
        assert "65 total experiments" in report.summary.overview
        assert "11 changes" in report.summary.overview
        assert "(original baseline)" in report.summary.overview

    def test_continuation_next_steps_include_continuation_note(self) -> None:
        ctx = _make_ctx(
            previous_run_id="run_prev_001",
            original_baseline_score=0.459,
        )
        report = ReportService().generate(ctx)

        assert any(
            "continued from a previous" in step for step in report.summary.nextSteps
        )

    def test_continuation_previous_run_id_in_payload(self) -> None:
        ctx = _make_ctx(previous_run_id="run_prev_001", original_baseline_score=0.459)
        report = ReportService().generate(ctx)

        assert report.previousRunId == "run_prev_001"

    def test_continuation_with_prior_experiments_in_changes_list(self) -> None:
        """Prior experiments' kept changes should appear in overview."""
        prior_exp = _make_experiment(1, 0.41, 0.50, "kept", "title boost increase")
        current_exp = _make_experiment(2, 0.50, 0.56, "kept", "phrase boost tweak")
        ctx = _make_ctx(
            baseline_score=0.50,
            best_score=0.56,
            experiments=[current_exp],
            experiments_run=1,
            improvements_kept=1,
            previous_run_id="run_prev_001",
            original_baseline_score=0.41,
            prior_experiments_run=1,
            prior_improvements_kept=1,
            prior_experiments=[prior_exp],
        )
        report = ReportService().generate(ctx)

        # Both changes should be referenced in overview
        assert "title boost increase" in report.summary.overview


# ------------------------------------------------------------------
# Edge cases
# ------------------------------------------------------------------


class TestReportServiceEdgeCases:
    """Edge cases and boundary conditions."""

    def test_zero_baseline_does_not_divide_by_zero(self) -> None:
        ctx = _make_ctx(baseline_score=0.0, best_score=0.10)
        report = ReportService().generate(ctx)

        # Should not crash; uses max(baseline, 0.001) guard
        assert report.summary.improvementPct > 0

    def test_no_experiments_still_generates_report(self) -> None:
        ctx = _make_ctx(
            experiments=[],
            experiments_run=0,
            improvements_kept=0,
            baseline_score=0.41,
            best_score=0.41,
        )
        report = ReportService().generate(ctx)

        assert report.summary.experimentsRun == 0
        assert report.summary.improvementsKept == 0

    def test_continuation_with_no_original_baseline_falls_back(self) -> None:
        """If original_baseline_score is None even with previous_run_id, use run baseline."""
        ctx = _make_ctx(
            baseline_score=0.50,
            best_score=0.55,
            previous_run_id="run_prev_001",
            original_baseline_score=None,  # Not set for some reason
        )
        report = ReportService().generate(ctx)

        # Should fall back to run baseline
        assert report.summary.baselineScore == 0.50

    def test_duration_from_elapsed_seconds(self) -> None:
        ctx = _make_ctx(elapsed_seconds=3723)  # 1h 2m 3s
        report = ReportService().generate(ctx)

        assert report.summary.durationSeconds == 3723

    def test_duration_from_experiment_ms_when_no_elapsed(self) -> None:
        experiments = [
            _make_experiment(1, 0.41, 0.45, duration_ms=5000),
            _make_experiment(2, 0.45, 0.49, duration_ms=3000),
        ]
        ctx = _make_ctx(
            experiments=experiments,
            experiments_run=2,
            elapsed_seconds=0,
        )
        report = ReportService().generate(ctx)

        assert report.summary.durationSeconds == 8.0  # (5000 + 3000) / 1000

    def test_format_duration_seconds(self) -> None:
        svc = ReportService()
        assert svc._format_duration(30) == "30 seconds"
        assert svc._format_duration(0.5) == "1 seconds"

    def test_format_duration_minutes(self) -> None:
        svc = ReportService()
        assert svc._format_duration(120) == "2 minutes"
        assert svc._format_duration(300) == "5 minutes"

    def test_format_duration_hours(self) -> None:
        svc = ReportService()
        assert svc._format_duration(3600) == "1 hours"
        assert svc._format_duration(5400) == "1h 30m"

    def test_diff_detects_scalar_changes(self) -> None:
        ctx = _make_ctx()
        ctx.baseline_profile.phraseBoost = 0.0
        ctx.best_profile.phraseBoost = 1.5
        report = ReportService().generate(ctx)

        phrase_diff = [d for d in report.diff if d.path == "phraseBoost"]
        assert len(phrase_diff) == 1
        assert phrase_diff[0].before == 0.0
        assert phrase_diff[0].after == 1.5

    def test_infer_failure_reason_no_results(self) -> None:
        svc = ReportService()
        reason = svc._infer_failure_reason(0, 0, [])
        assert "No results surfaced" in reason

    def test_infer_failure_reason_buried(self) -> None:
        svc = ReportService()
        reason = svc._infer_failure_reason(
            0, 0.5, [{"docId": "1", "title": "t", "excerpt": "e", "score": 0.1}]
        )
        assert "buried" in reason

    def test_infer_failure_reason_regression(self) -> None:
        svc = ReportService()
        reason = svc._infer_failure_reason(0.5, 0.3, [])
        assert "regressed" in reason

    def test_infer_failure_reason_none_when_improved(self) -> None:
        svc = ReportService()
        reason = svc._infer_failure_reason(0.3, 0.5, [])
        assert reason is None

    def test_persona_summary_counts_roles(self) -> None:
        ctx = _make_ctx()
        persona_a = PersonaViewModel(
            id="p1",
            name="Analyst",
            role="Security Analyst",
            department="Security",
            archetype="Expert",
            goal="Find high-risk issues",
            orbit=1,
            colorSeed=1,
            queries=["critical cve", "urgent patch"],
        )
        persona_b = PersonaViewModel(
            id="p2",
            name="Architect",
            role="Security Architect",
            department="Security",
            archetype="Expert",
            goal="Design safe systems",
            orbit=2,
            colorSeed=2,
            queries=["identity architecture", "network segmentation"],
        )
        ctx.personas = [persona_a, persona_b]

        report = ReportService().generate(ctx)

        assert report.personaSummary is not None
        assert report.personaSummary.personaCount == 2
        assert "Security Analyst" in report.personaSummary.topRoles


# ------------------------------------------------------------------
# Serialization roundtrip tests
# ------------------------------------------------------------------


class TestReportSerialization:
    """Ensure report payloads serialize correctly for the frontend."""

    def test_continuation_fields_in_json(self) -> None:
        ctx = _make_ctx(
            previous_run_id="run_prev_001",
            original_baseline_score=0.459,
            prior_experiments_run=50,
            prior_improvements_kept=8,
            experiments_run=15,
            improvements_kept=3,
        )
        report = ReportService().generate(ctx)
        data = report.model_dump()

        assert data["summary"]["isContinuation"] is True
        assert data["summary"]["originalBaselineScore"] == 0.459
        assert data["summary"]["totalExperimentsRun"] == 65
        assert data["summary"]["totalImprovementsKept"] == 11

    def test_non_continuation_fields_in_json(self) -> None:
        ctx = _make_ctx()
        report = ReportService().generate(ctx)
        data = report.model_dump()

        assert data["summary"]["isContinuation"] is False
        assert data["summary"]["originalBaselineScore"] is None
        assert data["summary"]["totalExperimentsRun"] is None
        assert data["summary"]["totalImprovementsKept"] is None

    def test_previous_run_id_in_json(self) -> None:
        ctx = _make_ctx(previous_run_id="run_abc")
        report = ReportService().generate(ctx)
        data = report.model_dump()

        assert data["previousRunId"] == "run_abc"

    def test_baseline_score_reflects_original_in_json(self) -> None:
        """The frontend reads summary.baselineScore — it must be the original baseline."""
        ctx = _make_ctx(
            baseline_score=0.565,
            best_score=0.595,
            previous_run_id="run_prev",
            original_baseline_score=0.459,
        )
        report = ReportService().generate(ctx)
        data = report.model_dump()

        # Frontend reads this directly for metric cards
        assert data["summary"]["baselineScore"] == 0.459
        assert data["summary"]["bestScore"] == 0.595
        assert data["summary"]["improvementPct"] > 25  # Cumulative ~29.6%
        assert "narrative" in data
        assert "implementationGuide" in data
