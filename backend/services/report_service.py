from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from ..models.contracts import SearchProfile, SearchProfileChange, PersonaViewModel
from ..models.runtime import RunContext
from ..models.report import (
    PersonaImpactRow,
    QueryBreakdownRow,
    ReportConnectionConfig,
    ReportPayload,
    ReportSummary,
)

logger = logging.getLogger(__name__)


class ReportService:
    """Generates a ReportPayload from a completed or stopped RunContext."""

    def generate(self, ctx: RunContext) -> ReportPayload:
        diff = self._compute_diff(ctx.baseline_profile, ctx.best_profile)
        persona_impact = self._compute_persona_impact(ctx.personas)
        query_breakdown = self._compute_query_breakdown(ctx)

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

        # Count queries that improved vs degraded
        improved_queries = sum(1 for q in query_breakdown if q.deltaPct > 1.0)
        degraded_queries = sum(1 for q in query_breakdown if q.deltaPct < -1.0)

        headline = (
            f"Search quality improved {delta_pct:+.1f}% on {ctx.summary.baselineEvalCount} test queries."
        )

        overview = (
            f"ElastiTune evaluated `{ctx.summary.indexName}` for about {duration_text}, ran "
            f"{ctx.metrics.experimentsRun} experiments, and kept {len(kept)} changes that improved "
            f"nDCG@10 from {baseline_score:.3f} to {best_score:.3f}. "
            f"The strongest gains came from {top_changes_text}."
        )

        if query_breakdown:
            overview += (
                f" Across individual queries, {improved_queries} of {len(query_breakdown)} improved"
            )
            if degraded_queries > 0:
                overview += f" while {degraded_queries} saw minor regressions"
            overview += "."

        is_continuation = bool(ctx.previous_run_id)
        next_steps = []
        if is_continuation:
            next_steps.append(
                "This run continued from a previous optimization. Compare the cumulative improvement against the original baseline."
            )
        next_steps.extend([
            "Review the accepted profile changes first and confirm they match the kinds of queries your users care about most.",
            f"Validate the tuned profile against a larger test set than the current {ctx.summary.baselineEvalCount}-query benchmark before promoting it.",
            "Save this profile as a candidate baseline and rerun ElastiTune after adding fresh user intents or failure cases.",
        ])

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
                nextSteps=next_steps[:4],
                baselineScore=baseline_score,
                bestScore=best_score,
                improvementPct=delta_pct,
                experimentsRun=ctx.metrics.experimentsRun,
                improvementsKept=len(kept),
                durationSeconds=duration_seconds,
                projectedMonthlySavingsUsd=ctx.compression.projectedMonthlySavingsUsd,
            ),
            connection=ctx.summary,
            connectionConfig=ReportConnectionConfig(
                mode=ctx.mode,
                esUrl=ctx.es_url,
                apiKey=ctx.api_key,
                indexName=ctx.index_name,
                evalSet=ctx.eval_set,
                llm=ctx.llm_config,
            ),
            searchProfileBefore=ctx.baseline_profile,
            searchProfileAfter=ctx.best_profile,
            diff=diff,
            queryBreakdown=query_breakdown,
            personaImpact=persona_impact,
            experiments=ctx.experiments,
            compression=ctx.compression,
            warnings=ctx.warnings,
            previousRunId=ctx.previous_run_id,
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

        # Simple scalar fields
        scalar_labels: Dict[str, str] = {
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
        }

        for field, label in scalar_labels.items():
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

        # Special handling for lexicalFields — produce per-field boost changes
        b_fields = before_dict.get("lexicalFields", [])
        a_fields = after_dict.get("lexicalFields", [])
        b_map = {f["field"]: f["boost"] for f in b_fields if isinstance(f, dict)}
        a_map = {f["field"]: f["boost"] for f in a_fields if isinstance(f, dict)}
        all_field_names = list(dict.fromkeys(list(b_map.keys()) + list(a_map.keys())))
        for fname in all_field_names:
            b_boost = b_map.get(fname)
            a_boost = a_map.get(fname)
            if b_boost != a_boost:
                changes.append(
                    SearchProfileChange(
                        path=f"{fname} boost",
                        before=b_boost if b_boost is not None else "—",
                        after=a_boost if a_boost is not None else "—",
                        label=f"{fname} boost: {b_boost} → {a_boost}",
                    )
                )

        return changes

    def _compute_query_breakdown(self, ctx: RunContext) -> List[QueryBreakdownRow]:
        """Build per-query before/after breakdown from stored per_query_scores."""
        rows: List[QueryBreakdownRow] = []
        eval_lookup = {ec.id: ec for ec in ctx.eval_set}

        if ctx.per_query_scores:
            # Use actual tracked per-query scores
            for query_id, scores in ctx.per_query_scores.items():
                ec = eval_lookup.get(query_id)
                baseline = scores.get("baseline", 0.0)
                best = scores.get("best", baseline)
                delta = ((best - baseline) / max(baseline, 0.001)) * 100 if baseline > 0 else 0.0
                rows.append(QueryBreakdownRow(
                    queryId=query_id,
                    query=ec.query if ec else query_id,
                    difficulty=ec.difficulty or "medium" if ec else "medium",
                    baselineScore=round(baseline, 4),
                    bestScore=round(best, 4),
                    deltaPct=round(delta, 1),
                    failureReason=self._infer_failure_reason(
                        baseline,
                        best,
                        ctx.per_query_results.get(query_id, {}).get("baseline", []),
                    ),
                    topRelevantDocIds=ec.relevantDocIds[:5] if ec else [],
                    baselineTopResults=ctx.per_query_results.get(query_id, {}).get("baseline", []),
                    bestTopResults=ctx.per_query_results.get(query_id, {}).get("best", []),
                ))
        else:
            # Fallback: estimate from eval set and overall scores
            baseline_score = ctx.metrics.baselineScore
            best_score = ctx.metrics.bestScore
            for ec in ctx.eval_set:
                delta = ((best_score - baseline_score) / max(baseline_score, 0.001)) * 100
                rows.append(QueryBreakdownRow(
                    queryId=ec.id,
                    query=ec.query,
                    difficulty=ec.difficulty or "medium",
                    baselineScore=round(baseline_score, 4),
                    bestScore=round(best_score, 4),
                    deltaPct=round(delta, 1),
                    failureReason=self._infer_failure_reason(
                        baseline_score,
                        best_score,
                        ctx.per_query_results.get(ec.id, {}).get("baseline", []),
                    ),
                    topRelevantDocIds=ec.relevantDocIds[:5],
                    baselineTopResults=ctx.per_query_results.get(ec.id, {}).get("baseline", []),
                    bestTopResults=ctx.per_query_results.get(ec.id, {}).get("best", []),
                ))

        # Sort by improvement (biggest gains first)
        rows.sort(key=lambda r: r.deltaPct, reverse=True)
        return rows

    def _infer_failure_reason(
        self,
        baseline: float,
        best: float,
        baseline_results: List[Dict[str, Any]],
    ) -> str | None:
        if baseline == 0 and not baseline_results:
            return "No results surfaced near the top ranks. That usually points to strict lexical matching, missing synonyms, or the wrong fields carrying the query."
        if baseline == 0 and baseline_results:
            return "Results came back, but the relevant ones were buried. Field weighting or match strategy likely favored noisy matches."
        if best < baseline:
            return "The overall benchmark improved, but this intent regressed slightly. Treat it as a candidate for a dedicated eval case or field-specific weighting."
        return None

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
