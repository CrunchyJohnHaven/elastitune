from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from backend.models.contracts import (
    ExperimentRecord,
    HeroMetrics,
    SearchProfile,
    SearchProfileChange,
)
from backend.models.report import ReportPayload
from backend.services.demo_service import DemoService
from backend.services.report_service import ReportService


# ---------------------------------------------------------------------------
# SearchProfile defaults
# ---------------------------------------------------------------------------


class TestSearchProfileDefaults:
    def test_default_multi_match_type(self) -> None:
        profile = SearchProfile()
        assert profile.multiMatchType == "best_fields"

    def test_default_minimum_should_match(self) -> None:
        profile = SearchProfile()
        assert profile.minimumShouldMatch == "75%"

    def test_default_tie_breaker(self) -> None:
        profile = SearchProfile()
        assert profile.tieBreaker == 0.0

    def test_default_phrase_boost(self) -> None:
        profile = SearchProfile()
        assert profile.phraseBoost == 0.0

    def test_default_fuzziness(self) -> None:
        profile = SearchProfile()
        assert profile.fuzziness == "0"

    def test_default_use_vector_is_false(self) -> None:
        profile = SearchProfile()
        assert profile.useVector is False

    def test_default_vector_weight(self) -> None:
        profile = SearchProfile()
        assert profile.vectorWeight == 0.35

    def test_default_lexical_weight(self) -> None:
        profile = SearchProfile()
        assert profile.lexicalWeight == 0.65

    def test_default_fusion_method(self) -> None:
        profile = SearchProfile()
        assert profile.fusionMethod == "weighted_sum"

    def test_default_lexical_fields_empty(self) -> None:
        profile = SearchProfile()
        assert profile.lexicalFields == []

    def test_defaults_produce_valid_model(self) -> None:
        # Should not raise
        profile = SearchProfile()
        assert profile is not None


# ---------------------------------------------------------------------------
# HeroMetrics serialization
# ---------------------------------------------------------------------------


class TestHeroMetricsSerialization:
    def test_model_dump_includes_continuation_fields(self) -> None:
        m = HeroMetrics()
        data = m.model_dump()
        assert "originalBaselineScore" in data
        assert "priorExperimentsRun" in data
        assert "priorImprovementsKept" in data

    def test_continuation_fields_default_values(self) -> None:
        m = HeroMetrics()
        assert m.originalBaselineScore is None
        assert m.priorExperimentsRun == 0
        assert m.priorImprovementsKept == 0

    def test_continuation_fields_can_be_set(self) -> None:
        m = HeroMetrics(
            originalBaselineScore=0.41,
            priorExperimentsRun=12,
            priorImprovementsKept=5,
        )
        data = m.model_dump()
        assert data["originalBaselineScore"] == 0.41
        assert data["priorExperimentsRun"] == 12
        assert data["priorImprovementsKept"] == 5

    def test_score_fields_serialise(self) -> None:
        m = HeroMetrics(
            currentScore=0.5,
            baselineScore=0.4,
            bestScore=0.55,
            improvementPct=37.5,
        )
        data = m.model_dump()
        assert data["currentScore"] == 0.5
        assert data["baselineScore"] == 0.4
        assert data["bestScore"] == 0.55

    def test_score_timeline_defaults_empty(self) -> None:
        m = HeroMetrics()
        assert m.scoreTimeline == []


# ---------------------------------------------------------------------------
# ReportPayload round-trip through JSON
# ---------------------------------------------------------------------------


class TestReportPayloadRoundtrip:
    def _make_report(self) -> ReportPayload:
        connection = DemoService().create_connection("conn_roundtrip")
        from backend.models.runtime import RunContext

        ctx = RunContext(
            run_id="run_roundtrip",
            connection=connection,
            personas=[],
            max_experiments=5,
            duration_minutes=1,
            auto_stop_on_plateau=True,
        )
        ctx.metrics.baselineScore = 0.40
        ctx.metrics.bestScore = 0.50
        ctx.metrics.currentScore = 0.50
        ctx.metrics.experimentsRun = 1
        ctx.metrics.improvementsKept = 1
        ctx.metrics.improvementPct = 25.0
        ctx.metrics.elapsedSeconds = 60

        change = SearchProfileChange(
            path="phraseBoost", before=0.0, after=1.0, label="phraseBoost 0.0 → 1.0"
        )
        ctx.experiments = [
            ExperimentRecord(
                experimentId=1,
                timestamp="2026-03-26T00:00:00Z",
                hypothesis="test",
                change=change,
                baselineScore=0.40,
                candidateScore=0.50,
                deltaAbsolute=0.10,
                deltaPercent=25.0,
                decision="kept",
                durationMs=500,
                queryFailuresBefore=[],
                queryFailuresAfter=[],
            )
        ]
        return ReportService().generate(ctx)

    def test_round_trip_via_json(self) -> None:
        report = self._make_report()
        json_str = report.model_dump_json()
        restored = ReportPayload.model_validate_json(json_str)
        assert restored.runId == report.runId
        assert restored.summary.baselineScore == report.summary.baselineScore
        assert restored.summary.bestScore == report.summary.bestScore

    def test_model_dump_is_json_serialisable(self) -> None:
        report = self._make_report()
        data = report.model_dump()
        # Should not raise
        serialised = json.dumps(data, default=str)
        assert isinstance(serialised, str)

    def test_run_id_preserved_in_round_trip(self) -> None:
        report = self._make_report()
        restored = ReportPayload.model_validate(report.model_dump())
        assert restored.runId == "run_roundtrip"

    def test_summary_fields_preserved(self) -> None:
        report = self._make_report()
        data = report.model_dump()
        summary = data["summary"]
        assert "headline" in summary
        assert "overview" in summary
        assert "nextSteps" in summary
        assert "baselineScore" in summary
        assert "bestScore" in summary
        assert "improvementPct" in summary


# ---------------------------------------------------------------------------
# ExperimentRecord validation
# ---------------------------------------------------------------------------


class TestExperimentRecordValidation:
    def _make_valid_change(self) -> SearchProfileChange:
        return SearchProfileChange(
            path="phraseBoost",
            before=0.0,
            after=1.0,
            label="phraseBoost 0.0 → 1.0",
        )

    def test_valid_record_constructs_without_error(self) -> None:
        change = self._make_valid_change()
        record = ExperimentRecord(
            experimentId=1,
            timestamp="2026-03-26T00:00:00Z",
            hypothesis="Test hypothesis",
            change=change,
            baselineScore=0.40,
            candidateScore=0.50,
            deltaAbsolute=0.10,
            deltaPercent=25.0,
            decision="kept",
            durationMs=1000,
        )
        assert record.experimentId == 1

    def test_baseline_score_alias_works(self) -> None:
        """ExperimentRecord accepts 'baselineScore' as an alias for 'beforeScore'."""
        change = self._make_valid_change()
        record = ExperimentRecord(
            experimentId=1,
            timestamp="2026-03-26T00:00:00Z",
            hypothesis="alias test",
            change=change,
            baselineScore=0.42,
            candidateScore=0.48,
            deltaAbsolute=0.06,
            deltaPercent=14.3,
            decision="kept",
            durationMs=800,
        )
        assert record.beforeScore == 0.42
        assert record.baselineScore == 0.42

    def test_decision_must_be_valid_literal(self) -> None:
        change = self._make_valid_change()
        with pytest.raises(ValidationError):
            ExperimentRecord(
                experimentId=1,
                timestamp="2026-03-26T00:00:00Z",
                hypothesis="bad decision",
                change=change,
                baselineScore=0.40,
                candidateScore=0.50,
                deltaAbsolute=0.10,
                deltaPercent=25.0,
                decision="invalid_decision",  # type: ignore[arg-type]
                durationMs=1000,
            )

    def test_query_failures_default_to_empty_lists(self) -> None:
        change = self._make_valid_change()
        record = ExperimentRecord(
            experimentId=2,
            timestamp="2026-03-26T00:00:00Z",
            hypothesis="defaults test",
            change=change,
            baselineScore=0.4,
            candidateScore=0.5,
            deltaAbsolute=0.1,
            deltaPercent=25.0,
            decision="reverted",
            durationMs=500,
        )
        assert record.queryFailuresBefore == []
        assert record.queryFailuresAfter == []

    def test_missing_required_field_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            ExperimentRecord(  # type: ignore[call-arg]
                # experimentId is missing
                timestamp="2026-03-26T00:00:00Z",
                hypothesis="missing field",
                change=self._make_valid_change(),
                baselineScore=0.4,
                candidateScore=0.5,
                deltaAbsolute=0.1,
                deltaPercent=25.0,
                decision="kept",
                durationMs=500,
            )
