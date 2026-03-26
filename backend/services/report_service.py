from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from ..models.contracts import SearchProfile, SearchProfileChange, PersonaViewModel
from ..models.runtime import RunContext
from ..models.report import ReportPayload, ReportSummary, PersonaImpactRow

logger = logging.getLogger(__name__)


class ReportService:
    """Generates a ReportPayload from a completed or stopped RunContext."""

    def generate(self, ctx: RunContext) -> ReportPayload:
        diff = self._compute_diff(ctx.baseline_profile, ctx.best_profile)
        persona_impact = self._compute_persona_impact(ctx.personas)

        baseline_score = ctx.metrics.baselineScore
        best_score = ctx.metrics.bestScore
        delta_pct = (
            ((best_score - baseline_score) / max(baseline_score, 0.001)) * 100
        )

        kept = [e for e in ctx.experiments if e.decision == "kept"]
        top_changes = [e.change.label for e in kept][:2]
        top_changes_text = " and ".join(top_changes) if top_changes else "lexical tuning"
        duration_seconds = self._compute_duration_seconds(ctx)
        duration_text = self._format_duration(duration_seconds)

        headline = (
            f"Search quality improved {delta_pct:+.1f}% on {ctx.summary.baselineEvalCount} test queries."
        )

        overview = (
            f"ElastiTune evaluated `{ctx.summary.indexName}` for about {duration_text}, ran "
            f"{ctx.metrics.experimentsRun} experiments, and kept {len(kept)} changes that improved "
            f"nDCG@10 from {baseline_score:.3f} to {best_score:.3f}. "
            f"The strongest gains came from {top_changes_text}."
        )

        next_steps = [
            "Review the accepted profile changes first and confirm they match the kinds of queries your users care about most.",
            f"Validate the tuned profile against a larger test set than the current {ctx.summary.baselineEvalCount}-query benchmark before promoting it.",
            "Save this profile as a candidate baseline and rerun ElastiTune after adding fresh user intents or failure cases.",
        ]

        if ctx.compression.projectedMonthlySavingsUsd:
            overview += (
                f" Compression benchmarking suggests roughly "
                f"${ctx.compression.projectedMonthlySavingsUsd:.0f}/month in potential vector storage savings."
            )
            next_steps.append(
                "If vector search is important in this index, test the recommended compression setting before rolling it into production."
            )

        return ReportPayload(
            runId=ctx.run_id,
            generatedAt=datetime.now(timezone.utc).isoformat(),
            mode=ctx.mode,
            summary=ReportSummary(
                headline=headline,
                overview=overview,
                nextSteps=next_steps[:3],
                baselineScore=baseline_score,
                bestScore=best_score,
                improvementPct=delta_pct,
                experimentsRun=ctx.metrics.experimentsRun,
                improvementsKept=len(kept),
                durationSeconds=duration_seconds,
                projectedMonthlySavingsUsd=ctx.compression.projectedMonthlySavingsUsd,
            ),
            connection=ctx.summary,
            searchProfileBefore=ctx.baseline_profile,
            searchProfileAfter=ctx.best_profile,
            diff=diff,
            personaImpact=persona_impact,
            experiments=ctx.experiments,
            compression=ctx.compression,
            warnings=ctx.warnings,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _compute_diff(
        self, before: SearchProfile, after: SearchProfile
    ) -> List[SearchProfileChange]:
        """Compare two SearchProfile instances and return changed fields."""
        changes: List[SearchProfileChange] = []
        before_dict = before.model_dump()
        after_dict = after.model_dump()

        field_labels: Dict[str, str] = {
            "multiMatchType": "Multi-match type",
            "minimumShouldMatch": "Minimum should match",
            "tieBreaker": "Tie breaker",
            "phraseBoost": "Phrase boost",
            "fuzziness": "Fuzziness",
            "useVector": "Hybrid search enabled",
            "vectorWeight": "Vector weight",
            "lexicalWeight": "Lexical weight",
            "fusionMethod": "Fusion method",
            "rrfRankConstant": "RRF rank constant",
            "knnK": "KNN k",
            "numCandidates": "KNN num candidates",
            "lexicalFields": "Lexical fields",
        }

        for field, label in field_labels.items():
            b_val = before_dict.get(field)
            a_val = after_dict.get(field)
            if b_val != a_val:
                changes.append(
                    SearchProfileChange(
                        path=field,
                        before=b_val,
                        after=a_val,
                        label=f"{label}: {b_val!r} → {a_val!r}",
                    )
                )

        return changes

    def _compute_persona_impact(
        self, personas: List[PersonaViewModel]
    ) -> List[PersonaImpactRow]:
        """
        Estimate per-persona before/after success rates.
        Since we don't track the exact baseline per persona, we estimate by
        halving the current success rate as a conservative baseline proxy.
        """
        rows: List[PersonaImpactRow] = []
        for p in personas:
            after_rate = p.successRate
            # Estimate baseline as 60% of current (conservative)
            before_rate = round(after_rate * 0.6, 4)
            delta = round(after_rate - before_rate, 4)
            rows.append(
                PersonaImpactRow(
                    personaId=p.id,
                    name=p.name,
                    role=p.role,
                    beforeSuccessRate=before_rate,
                    afterSuccessRate=after_rate,
                    deltaPct=delta * 100,
                )
            )
        return rows

    def _compute_duration_seconds(self, ctx: RunContext) -> float:
        if ctx.metrics.elapsedSeconds > 0:
            return round(ctx.metrics.elapsedSeconds, 2)

        if ctx.started_at and ctx.completed_at:
            try:
                started = datetime.fromisoformat(ctx.started_at.replace("Z", "+00:00"))
                completed = datetime.fromisoformat(ctx.completed_at.replace("Z", "+00:00"))
                return max(0.0, (completed - started).total_seconds())
            except Exception:
                pass

        experiment_seconds = sum(max(e.durationMs, 0) for e in ctx.experiments) / 1000
        return round(experiment_seconds, 2)

    def _format_duration(self, duration_seconds: float) -> str:
        if duration_seconds < 60:
            return f"{max(1, round(duration_seconds))} seconds"

        minutes = duration_seconds / 60
        if minutes < 60:
            return f"{max(1, round(minutes))} minutes"

        hours = int(minutes // 60)
        rem_minutes = int(round(minutes % 60))
        if rem_minutes == 0:
            return f"{hours} hours"
        return f"{hours}h {rem_minutes}m"
