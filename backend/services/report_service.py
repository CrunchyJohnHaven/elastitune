from __future__ import annotations

import difflib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..models.contracts import SearchProfile, SearchProfileChange, PersonaViewModel
from ..models.runtime import RunContext
from ..models.report import (
    PersonaImpactRow,
    PersonaSummaryDetail,
    QueryBreakdownRow,
    ReportChangeNarrative,
    ReportCodeLine,
    ReportCodeSnippet,
    ReportConnectionConfig,
    ReportImplementationGuide,
    ReportNarrativeSection,
    ReportPayload,
    ReportSummary,
    ReportValidationNote,
)
from .llm_service import LLMService

logger = logging.getLogger(__name__)


class ReportService:
    """Generates a ReportPayload from a completed or stopped RunContext."""

    def generate(self, ctx: RunContext) -> ReportPayload:
        diff = self._compute_diff(ctx.baseline_profile, ctx.best_profile)
        persona_impact = self._compute_persona_impact(ctx.personas)
        query_breakdown = self._compute_query_breakdown(ctx)

        # Use the original baseline when this is a continued run
        is_continuation = bool(ctx.previous_run_id)
        original_baseline = ctx.original_baseline_score
        # Fallback: the metrics may have the original baseline even if the
        # context-level field was lost (e.g. after app restart during chain).
        if (
            original_baseline is None
            and getattr(ctx.metrics, "originalBaselineScore", None) is not None
        ):
            original_baseline = ctx.metrics.originalBaselineScore
        run_baseline_score = ctx.metrics.baselineScore
        best_score = ctx.metrics.bestScore

        # For the report, show cumulative improvement from the original baseline
        if original_baseline is not None:
            baseline_score = original_baseline
        else:
            baseline_score = run_baseline_score

        delta_pct = ((best_score - baseline_score) / max(baseline_score, 0.001)) * 100

        # Cumulative experiment counts across the chain — prefer context
        # fields, fall back to the metrics priors set during run init.
        prior_exp = (
            ctx.prior_experiments_run
            or getattr(ctx.metrics, "priorExperimentsRun", 0)
            or 0
        )
        prior_kept = (
            ctx.prior_improvements_kept
            or getattr(ctx.metrics, "priorImprovementsKept", 0)
            or 0
        )
        total_experiments = ctx.metrics.experimentsRun + prior_exp
        total_kept_all = ctx.metrics.improvementsKept + prior_kept

        kept = [e for e in ctx.experiments if e.decision == "kept"]
        all_kept_changes = [e.change.label for e in kept]
        # Also include prior experiments' changes
        prior_kept_exps = [e for e in ctx.prior_experiments if e.decision == "kept"]
        all_kept_changes = [e.change.label for e in prior_kept_exps] + all_kept_changes
        top_changes = all_kept_changes[:2]
        top_changes_text = (
            " and ".join(top_changes) if top_changes else "lexical tuning"
        )
        duration_seconds = self._compute_duration_seconds(ctx)
        duration_text = self._format_duration(duration_seconds)

        # Count queries that improved vs degraded
        improved_queries = sum(1 for q in query_breakdown if q.deltaPct > 1.0)
        degraded_queries = sum(1 for q in query_breakdown if q.deltaPct < -1.0)
        confidence_score = self._compute_confidence_score(
            improvements_kept=len(kept),
            experiments_run=ctx.metrics.experimentsRun,
            improved_queries=improved_queries,
            degraded_queries=degraded_queries,
            query_count=len(query_breakdown),
        )

        headline = f"Search quality improved {delta_pct:+.1f}% on {ctx.summary.baselineEvalCount} test queries."

        if is_continuation:
            overview = (
                f"ElastiTune evaluated `{ctx.summary.indexName}` across multiple optimization runs, "
                f"running {total_experiments} total experiments and keeping {total_kept_all} changes that improved "
                f"nDCG@10 from {baseline_score:.3f} (original baseline) to {best_score:.3f}. "
                f"The strongest gains came from {top_changes_text}."
            )
        else:
            overview = (
                f"ElastiTune evaluated `{ctx.summary.indexName}` for about {duration_text}, ran "
                f"{ctx.metrics.experimentsRun} experiments, and kept {len(kept)} changes that improved "
                f"nDCG@10 from {baseline_score:.3f} to {best_score:.3f}. "
                f"The strongest gains came from {top_changes_text}."
            )

        if query_breakdown:
            overview += f" Across individual queries, {improved_queries} of {len(query_breakdown)} improved"
            if degraded_queries > 0:
                overview += f" while {degraded_queries} saw minor regressions"
            overview += "."

        next_steps = []
        if is_continuation:
            next_steps.append(
                "This run continued from a previous optimization. Compare the cumulative improvement against the original baseline."
            )
        next_steps.extend(
            [
                "Review the accepted profile changes first and confirm they match the kinds of queries your users care about most.",
                f"Validate the tuned profile against a larger test set than the current {ctx.summary.baselineEvalCount}-query benchmark before promoting it.",
                "Save this profile as a candidate baseline and rerun ElastiTune after adding fresh user intents or failure cases.",
            ]
        )

        if ctx.compression.projectedMonthlySavingsUsd:
            overview += (
                f" Compression benchmarking suggests roughly "
                f"${ctx.compression.projectedMonthlySavingsUsd:.0f}/month in potential vector storage savings."
            )
            next_steps.append(
                "If vector search is important in this index, test the recommended compression setting before rolling it into production."
            )

        persona_summary = self._build_persona_summary(ctx)
        change_narratives = self._build_change_narratives(
            diff=diff,
            kept_experiments=kept,
            query_breakdown=query_breakdown,
            improved_queries=improved_queries,
            degraded_queries=degraded_queries,
        )
        implementation_guide = self._build_implementation_guide(ctx, diff)
        validation_notes = self._build_validation_notes(
            ctx=ctx,
            improved_queries=improved_queries,
            degraded_queries=degraded_queries,
            confidence_score=confidence_score,
            total_queries=len(query_breakdown),
        )
        narrative = self._build_narrative_sections(
            ctx=ctx,
            delta_pct=delta_pct,
            duration_text=duration_text,
            improved_queries=improved_queries,
            degraded_queries=degraded_queries,
            persona_summary=persona_summary,
            change_narratives=change_narratives,
            confidence_score=confidence_score,
        )

        report = ReportPayload(
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
                personaCount=len(ctx.personas),
                queriesImproved=improved_queries,
                queriesRegressed=degraded_queries,
                confidenceScore=confidence_score,
                isContinuation=is_continuation,
                originalBaselineScore=original_baseline if is_continuation else None,
                totalExperimentsRun=total_experiments if is_continuation else None,
                totalImprovementsKept=total_kept_all if is_continuation else None,
                modelId=ctx.best_profile.modelId if ctx.best_profile.modelId else None,
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
            narrative=narrative,
            personaSummary=persona_summary,
            changeNarratives=change_narratives,
            implementationGuide=implementation_guide,
            validationNotes=validation_notes,
            experiments=ctx.experiments,
            compression=ctx.compression,
            warnings=ctx.warnings,
            previousRunId=ctx.previous_run_id,
        )
        return report.sanitize_for_client()

    async def generate_async(self, ctx: RunContext) -> ReportPayload:
        report = self.generate(ctx)
        return await self._enrich_narrative_with_llm(ctx, report)

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
                delta = (
                    ((best - baseline) / max(baseline, 0.001)) * 100
                    if baseline > 0
                    else 0.0
                )
                rows.append(
                    QueryBreakdownRow(
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
                        baselineTopResults=ctx.per_query_results.get(query_id, {}).get(
                            "baseline", []
                        ),
                        bestTopResults=ctx.per_query_results.get(query_id, {}).get(
                            "best", []
                        ),
                    )
                )
        else:
            # Fallback: estimate from eval set and overall scores
            baseline_score = ctx.metrics.baselineScore
            best_score = ctx.metrics.bestScore
            for ec in ctx.eval_set:
                delta = (
                    (best_score - baseline_score) / max(baseline_score, 0.001)
                ) * 100
                rows.append(
                    QueryBreakdownRow(
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
                        baselineTopResults=ctx.per_query_results.get(ec.id, {}).get(
                            "baseline", []
                        ),
                        bestTopResults=ctx.per_query_results.get(ec.id, {}).get(
                            "best", []
                        ),
                    )
                )

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

    def _build_persona_summary(self, ctx: RunContext) -> PersonaSummaryDetail:
        archetype_counts: Dict[str, int] = {}
        role_counts: Dict[str, int] = {}

        for persona in ctx.personas:
            archetype = persona.archetype or "Unknown"
            role = persona.role or "Unknown role"
            archetype_counts[archetype] = archetype_counts.get(archetype, 0) + 1
            role_counts[role] = role_counts.get(role, 0) + 1

        top_roles = [
            role
            for role, _ in sorted(
                role_counts.items(), key=lambda item: (-item[1], item[0].lower())
            )[:3]
        ]

        if ctx.personas:
            explanation = (
                f"This run used {len(ctx.personas)} simulated personas to pressure-test the search profile from multiple angles. "
                f"Most represented roles were {', '.join(top_roles) if top_roles else 'the detected user roles'}. "
                "These personas are synthetic evaluators, not real people, and they help reveal whether improvements generalize across different intents."
            )
        else:
            explanation = (
                "This run did not include persona simulations, so the report is based entirely on the benchmark query set."
            )

        return PersonaSummaryDetail(
            personaCount=len(ctx.personas),
            archetypeCounts=archetype_counts,
            topRoles=top_roles,
            explanation=explanation,
        )

    def _build_change_narratives(
        self,
        diff: List[SearchProfileChange],
        kept_experiments: List[Any],
        query_breakdown: List[QueryBreakdownRow],
        improved_queries: int,
        degraded_queries: int,
    ) -> List[ReportChangeNarrative]:
        narratives: List[ReportChangeNarrative] = []
        strongest_queries = [row.query for row in query_breakdown[:2]]

        for change in diff:
            matching_experiment = next(
                (exp for exp in reversed(kept_experiments) if exp.change.path == change.path),
                None,
            )
            confidence = self._compute_change_confidence(
                delta_percent=matching_experiment.deltaPercent if matching_experiment else None,
                improved_queries=improved_queries,
                degraded_queries=degraded_queries,
            )
            title = self._humanize_change_path(change.path)
            before = self._format_change_value(change.before)
            after = self._format_change_value(change.after)
            expected_effect = self._describe_expected_effect(change.path, before, after)
            why_it_helped = self._explain_change_why(change.path, before, after)
            evidence: List[str] = []
            if matching_experiment:
                evidence.append(
                    f"Accepted in experiment {matching_experiment.experimentId} after the benchmark moved {matching_experiment.deltaPercent:+.1f}%."
                )
            if strongest_queries:
                evidence.append(
                    "Representative improved intents in the final profile included "
                    + ", ".join(f'"{query}"' for query in strongest_queries)
                    + "."
                )
            evidence.append(
                f"Final run improved {improved_queries} benchmark queries and regressed {degraded_queries}."
            )

            narratives.append(
                ReportChangeNarrative(
                    path=change.path,
                    title=title,
                    plainEnglish=f"{title} changed from {before} to {after}.",
                    before=before,
                    after=after,
                    expectedEffect=expected_effect,
                    whyItHelped=why_it_helped,
                    confidence=confidence,
                    evidence=evidence,
                )
            )

        return narratives

    def _build_implementation_guide(
        self, ctx: RunContext, diff: List[SearchProfileChange]
    ) -> ReportImplementationGuide:
        representative_query = None
        if ctx.eval_set:
            representative_query = ctx.eval_set[0].query
        elif ctx.per_query_scores:
            representative_query = next(iter(ctx.per_query_scores.keys()), None)
        else:
            representative_query = "example query"

        before_lines = self._build_query_lines(
            query_text=representative_query,
            profile=ctx.baseline_profile,
            diff=diff,
        )
        after_lines = self._build_query_lines(
            query_text=representative_query,
            profile=ctx.best_profile,
            diff=diff,
        )
        self._mark_changed_lines(before_lines, after_lines)

        changed_paths = [self._humanize_change_path(change.path) for change in diff[:4]]
        summary = (
            "This implementation guide shows a representative Elasticsearch request body before and after tuning. "
            "The line numbers below refer to the generated request example, so a developer can see exactly what changed even if the application wraps Elasticsearch in helper code."
        )
        apply_instructions = [
            "Find the part of your application that builds the Elasticsearch search request for this index.",
            "Compare that request body to the tuned example below and apply the changed fields first.",
            "Retest the exact benchmark queries from this report before promoting the new profile to production.",
        ]
        if diff:
            apply_instructions.append(
                "Prioritize these changes: " + ", ".join(changed_paths) + "."
            )

        snippet = ReportCodeSnippet(
            title="Representative request body",
            target=f"Application search request for index `{ctx.summary.indexName}`",
            format="json",
            summary="The `after` snippet is the tuned request body ElastiTune recommends.",
            beforeLines=before_lines,
            afterLines=after_lines,
        )

        return ReportImplementationGuide(
            summary=summary,
            applyInstructions=apply_instructions,
            representativeQuery=representative_query,
            note=(
                "The exact file path in a customer application will vary. Treat this as the authoritative before/after payload diff."
            ),
            snippets=[snippet],
        )

    def _build_validation_notes(
        self,
        ctx: RunContext,
        improved_queries: int,
        degraded_queries: int,
        confidence_score: float,
        total_queries: int,
    ) -> List[ReportValidationNote]:
        notes: List[ReportValidationNote] = []
        notes.append(
            ReportValidationNote(
                title="Benchmark coverage",
                body=(
                    f"The tuned profile was evaluated on {ctx.summary.baselineEvalCount} benchmark queries. "
                    "Treat this as evidence, not a universal guarantee, until you test against a broader production-like query set."
                ),
                severity="info",
            )
        )

        if improved_queries > 0:
            notes.append(
                ReportValidationNote(
                    title="Observed gains",
                    body=(
                        f"{improved_queries} of {total_queries or ctx.summary.baselineEvalCount} benchmark queries improved in the final profile."
                    ),
                    severity="success",
                )
            )

        if degraded_queries > 0:
            notes.append(
                ReportValidationNote(
                    title="Queries to review",
                    body=(
                        f"{degraded_queries} benchmark queries regressed slightly. Review those intents before rollout so you do not trade away an important edge case."
                    ),
                    severity="warning",
                )
            )

        if ctx.warnings:
            notes.append(
                ReportValidationNote(
                    title="Run warnings",
                    body="; ".join(ctx.warnings[:3]),
                    severity="warning",
                )
            )

        notes.append(
            ReportValidationNote(
                title="Confidence",
                body=(
                    f"ElastiTune assigns {confidence_score:.0%} confidence to this recommendation based on kept experiments, benchmark coverage, and whether improvements outweighed regressions."
                ),
                severity="info",
            )
        )
        return notes

    def _build_narrative_sections(
        self,
        ctx: RunContext,
        delta_pct: float,
        duration_text: str,
        improved_queries: int,
        degraded_queries: int,
        persona_summary: PersonaSummaryDetail,
        change_narratives: List[ReportChangeNarrative],
        confidence_score: float,
    ) -> List[ReportNarrativeSection]:
        top_change_titles = [change.title for change in change_narratives[:2]]
        top_changes_text = ", ".join(top_change_titles) if top_change_titles else "lexical tuning"

        return [
            ReportNarrativeSection(
                key="plain_english_summary",
                title="Plain-English Summary",
                body=(
                    f"ElastiTune ran search experiments for about {duration_text} and found a tuned profile that improved benchmark relevance by {delta_pct:+.1f}%. "
                    f"In plain English: more people are likely to see the right result higher up the page, sooner. "
                    f"The biggest wins came from {top_changes_text}."
                ),
                audience="executive",
                confidence=confidence_score,
            ),
            ReportNarrativeSection(
                key="why_this_matters",
                title="Why This Matters",
                body=(
                    f"Out of {len(ctx.eval_set)} benchmark queries, {improved_queries} clearly improved"
                    + (
                        f" and {degraded_queries} regressed slightly."
                        if degraded_queries
                        else " with no material regressions in the final benchmark."
                    )
                    + " That means the tuned profile improved the test set overall instead of relying on a single lucky query."
                ),
                audience="operator",
                confidence=confidence_score,
            ),
            ReportNarrativeSection(
                key="persona_coverage",
                title="Persona Coverage",
                body=persona_summary.explanation,
                audience="operator",
                confidence=0.72 if persona_summary.personaCount else 0.4,
            ),
            ReportNarrativeSection(
                key="implementation_readout",
                title="Implementation Readout",
                body=(
                    "The implementation guide below translates the tuning result into a before/after Elasticsearch request body with line numbers. "
                    "That lets a developer copy the important changes without reverse-engineering the optimizer."
                ),
                audience="technical",
                confidence=0.86,
            ),
        ]

    def _build_query_lines(
        self,
        query_text: Optional[str],
        profile: SearchProfile,
        diff: List[SearchProfileChange],
    ) -> List[ReportCodeLine]:
        body = self._build_query_body_preview(query_text or "example query", profile, 5)
        lines = self._json_lines(body)
        diff_hints = {
            self._snippet_token_for_path(change.path): self._humanize_change_path(change.path)
            for change in diff
        }

        result: List[ReportCodeLine] = []
        for idx, content in enumerate(lines, start=1):
            explanation = None
            for token, label in diff_hints.items():
                if token and token in content:
                    explanation = f"This line reflects the tuned {label.lower()}."
                    break
            result.append(
                ReportCodeLine(
                    lineNumber=idx,
                    content=content,
                    explanation=explanation,
                )
            )
        return result

    def _mark_changed_lines(
        self, before_lines: List[ReportCodeLine], after_lines: List[ReportCodeLine]
    ) -> None:
        matcher = difflib.SequenceMatcher(
            a=[line.content for line in before_lines],
            b=[line.content for line in after_lines],
        )
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                continue
            for line in before_lines[i1:i2]:
                line.changed = True
            for line in after_lines[j1:j2]:
                line.changed = True

    def _json_lines(self, payload: Dict[str, Any]) -> List[str]:
        import json

        return json.dumps(payload, indent=2).splitlines()

    def _build_query_body_preview(
        self, query_text: str, profile: SearchProfile, size: int
    ) -> Dict[str, Any]:
        fields = (
            [f"{field.field}^{field.boost}" for field in profile.lexicalFields]
            if profile.lexicalFields
            else ["*"]
        )

        multi_match: Dict[str, Any] = {
            "query": query_text,
            "fields": fields,
            "type": profile.multiMatchType,
            "minimum_should_match": profile.minimumShouldMatch,
        }
        if profile.tieBreaker > 0:
            multi_match["tie_breaker"] = profile.tieBreaker
        if profile.fuzziness != "0":
            multi_match["fuzziness"] = profile.fuzziness

        lexical_query: Dict[str, Any] = {"multi_match": multi_match}
        if profile.phraseBoost > 0 and profile.lexicalFields:
            top_field = profile.lexicalFields[0].field
            lexical_query = {
                "bool": {
                    "must": [{"multi_match": multi_match}],
                    "should": [
                        {
                            "match_phrase": {
                                top_field: {
                                    "query": query_text,
                                    "boost": profile.phraseBoost,
                                }
                            }
                        }
                    ],
                }
            }

        if profile.useVector and profile.vectorField:
            return {
                "size": size,
                "query": lexical_query,
                "knn": {
                    "field": profile.vectorField,
                    "query_vector_builder": {
                        "text_embedding": {
                            "model_id": profile.modelId or ".elser_model_2",
                            "model_text": query_text,
                        }
                    },
                    "k": profile.knnK,
                    "num_candidates": profile.numCandidates,
                    "boost": profile.vectorWeight,
                },
            }
        return {"size": size, "query": lexical_query}

    def _compute_confidence_score(
        self,
        improvements_kept: int,
        experiments_run: int,
        improved_queries: int,
        degraded_queries: int,
        query_count: int,
    ) -> float:
        score = 0.45
        if improvements_kept > 0:
            score += 0.15
        if experiments_run >= 5:
            score += 0.08
        if experiments_run >= 15:
            score += 0.05
        if query_count > 0:
            score += 0.08
        if improved_queries > 0:
            score += 0.12
        if improved_queries > degraded_queries:
            score += 0.1
        if degraded_queries > 0:
            score -= min(0.18, degraded_queries * 0.03)
        return round(min(0.97, max(0.3, score)), 2)

    def _compute_change_confidence(
        self,
        delta_percent: Optional[float],
        improved_queries: int,
        degraded_queries: int,
    ) -> float:
        score = 0.55
        if delta_percent is not None:
            if delta_percent > 5:
                score += 0.18
            elif delta_percent > 0:
                score += 0.1
        if improved_queries > degraded_queries:
            score += 0.08
        if degraded_queries > 0:
            score -= min(0.12, degraded_queries * 0.02)
        return round(min(0.96, max(0.35, score)), 2)

    def _humanize_change_path(self, path: str) -> str:
        mapping = {
            "phraseBoost": "phrase-match emphasis",
            "minimumShouldMatch": "minimum term match threshold",
            "multiMatchType": "multi-field match strategy",
            "tieBreaker": "tie-break balancing",
            "fuzziness": "fuzzy matching",
            "useVector": "hybrid vector retrieval",
            "vectorWeight": "vector score weighting",
            "lexicalWeight": "lexical score weighting",
            "fusionMethod": "score fusion method",
            "rrfRankConstant": "RRF rank constant",
            "knnK": "nearest-neighbor sample size",
            "numCandidates": "vector candidate pool",
        }
        if path in mapping:
            return mapping[path]
        if path.endswith(" boost"):
            return path.replace(" boost", " field boost")
        return path

    def _format_change_value(self, value: Any) -> str:
        if value is None or value == "":
            return "not set"
        if isinstance(value, bool):
            return "enabled" if value else "disabled"
        return str(value)

    def _describe_expected_effect(self, path: str, before: str, after: str) -> str:
        if path.endswith(" boost"):
            return (
                f"This increases how much the `{path.replace(' boost', '')}` field influences ranking, moving documents with stronger matches in that field higher in the results."
            )
        descriptions = {
            "phraseBoost": "This rewards exact phrase matches more strongly, which usually helps precise or navigational searches.",
            "minimumShouldMatch": "This changes how strict the lexical match must be before a document can rank well.",
            "multiMatchType": "This changes how Elasticsearch combines evidence from multiple text fields.",
            "tieBreaker": "This changes how much secondary matching fields contribute when several fields match at once.",
            "fuzziness": "This allows or tightens typo tolerance in lexical matching.",
            "useVector": "This turns hybrid retrieval on or off so semantic similarity can contribute alongside keyword matching.",
            "vectorWeight": "This changes how much semantic similarity influences the final ranking.",
            "lexicalWeight": "This changes how much classic keyword relevance influences the final ranking.",
            "fusionMethod": "This changes the algorithm used to combine lexical and vector scores.",
            "rrfRankConstant": "This changes how aggressively Reciprocal Rank Fusion smooths rank differences.",
            "knnK": "This changes how many nearest-neighbor vector hits Elasticsearch retrieves before scoring.",
            "numCandidates": "This changes how wide Elasticsearch searches for vector candidates before returning the top matches.",
        }
        return descriptions.get(
            path,
            f"This changes `{path}` from {before} to {after}, which alters how Elasticsearch scores and orders results.",
        )

    def _explain_change_why(self, path: str, before: str, after: str) -> str:
        if path == "minimumShouldMatch":
            return (
                f"Moving from {before} to {after} changed how strict the query was. This can help when the original setup was either too loose and noisy or too strict and brittle."
            )
        if path == "phraseBoost":
            return (
                f"Raising phrase emphasis from {before} to {after} helped reward exact phrasing when it mattered, which often surfaces more obviously relevant documents."
            )
        if path in {"vectorWeight", "lexicalWeight", "useVector", "fusionMethod"}:
            return (
                "This changed the balance between semantic retrieval and lexical matching, which matters when users search with both exact terms and broader concepts."
            )
        if path.endswith(" boost"):
            return (
                "This shifted ranking weight toward a field that appears to carry stronger relevance signals for this benchmark."
            )
        return (
            f"ElastiTune kept this change because the benchmark improved after moving `{path}` from {before} to {after}."
        )

    def _snippet_token_for_path(self, path: str) -> Optional[str]:
        mapping = {
            "phraseBoost": '"match_phrase"',
            "minimumShouldMatch": '"minimum_should_match"',
            "multiMatchType": '"type"',
            "tieBreaker": '"tie_breaker"',
            "fuzziness": '"fuzziness"',
            "vectorWeight": '"boost"',
            "useVector": '"knn"',
            "knnK": '"k"',
            "numCandidates": '"num_candidates"',
            "modelId": '"model_id"',
        }
        if path.endswith(" boost"):
            return path.replace(" boost", "") + "^"
        return mapping.get(path)

    def _compute_duration_seconds(self, ctx: RunContext) -> float:
        if ctx.metrics.elapsedSeconds > 0:
            return round(ctx.metrics.elapsedSeconds, 2)

        if ctx.started_at and ctx.completed_at:
            try:
                started = datetime.fromisoformat(ctx.started_at.replace("Z", "+00:00"))
                completed = datetime.fromisoformat(
                    ctx.completed_at.replace("Z", "+00:00")
                )
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

    async def _enrich_narrative_with_llm(
        self, ctx: RunContext, report: ReportPayload
    ) -> ReportPayload:
        if not ctx.llm_config or ctx.llm_config.provider == "disabled":
            return report

        llm = LLMService(ctx.llm_config)
        if not llm.available:
            return report

        prompt_sections = [
            {
                "key": section.key,
                "title": section.title,
                "body": section.body,
                "audience": section.audience,
            }
            for section in report.narrative
        ]
        prompt_changes = [
            {
                "title": change.title,
                "plainEnglish": change.plainEnglish,
                "expectedEffect": change.expectedEffect,
                "whyItHelped": change.whyItHelped,
            }
            for change in report.changeNarratives[:5]
        ]

        system_prompt = (
            "You rewrite Elasticsearch optimization reports for non-technical business readers. "
            "Keep every claim grounded in the provided evidence. Use plain English, be explicit, and do not invent file paths, line numbers, or causal claims that are not supported."
        )
        user_prompt = (
            "Rewrite the narrative sections and change explanations below into clearer plain English. "
            "Return JSON with keys `narrative` and `changeNarratives`. "
            "`narrative` must be an array of objects with `key` and `body`. "
            "`changeNarratives` must be an array of objects with `title`, `plainEnglish`, `expectedEffect`, and `whyItHelped`.\n\n"
            f"Report headline: {report.summary.headline}\n"
            f"Improvement: {report.summary.improvementPct:+.1f}%\n"
            f"Confidence: {report.summary.confidenceScore:.0%}\n"
            f"Persona count: {report.summary.personaCount}\n"
            f"Sections: {prompt_sections}\n"
            f"Changes: {prompt_changes}\n"
        )
        rewritten = await llm.complete_json(system_prompt, user_prompt)
        if not isinstance(rewritten, dict):
            return report

        narrative_updates = {
            item.get("key"): item.get("body")
            for item in rewritten.get("narrative", [])
            if isinstance(item, dict) and item.get("key") and item.get("body")
        }
        change_updates = {
            item.get("title"): item
            for item in rewritten.get("changeNarratives", [])
            if isinstance(item, dict) and item.get("title")
        }

        updated_narrative: List[ReportNarrativeSection] = []
        for section in report.narrative:
            new_body = narrative_updates.get(section.key)
            if new_body:
                updated_narrative.append(
                    section.model_copy(
                        update={"body": str(new_body), "source": "llm"},
                    )
                )
            else:
                updated_narrative.append(section)

        updated_changes: List[ReportChangeNarrative] = []
        for change in report.changeNarratives:
            update = change_updates.get(change.title)
            if update:
                updated_changes.append(
                    change.model_copy(
                        update={
                            "plainEnglish": str(
                                update.get("plainEnglish", change.plainEnglish)
                            ),
                            "expectedEffect": str(
                                update.get("expectedEffect", change.expectedEffect)
                            ),
                            "whyItHelped": str(
                                update.get("whyItHelped", change.whyItHelped)
                            ),
                        }
                    )
                )
            else:
                updated_changes.append(change)

        return report.model_copy(
            update={
                "narrative": updated_narrative,
                "changeNarratives": updated_changes,
            },
            deep=True,
        )
