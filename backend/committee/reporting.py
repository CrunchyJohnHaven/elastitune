from __future__ import annotations

import difflib
from datetime import datetime, timezone
from typing import Any, Dict, List

from ..services.llm_service import LLMService
from .models import (
    CommitteeChangeNarrative,
    CommitteeExportPayload,
    CommitteeImplementationGuide,
    CommitteeNarrativeSection,
    CommitteePersonaSummary,
    CommitteeReport,
    CommitteeReportSummary,
    CommitteeRewriteSnippet,
    CommitteeSectionExport,
    CommitteeSnippetLine,
    CommitteeValidationNote,
)
from .runtime import CommitteeRunContext


def build_report(ctx: CommitteeRunContext) -> CommitteeReport:
    kept_rewrites = [rewrite for rewrite in ctx.rewrites if rewrite.decision == "kept"]
    changed_section_ids = {rewrite.sectionId for rewrite in kept_rewrites}
    confidence_score = _compute_confidence_score(ctx, kept_rewrites)
    duration_seconds = _compute_duration_seconds(ctx)
    persona_summary = _build_persona_summary(ctx)
    change_narratives = _build_change_narratives(ctx, kept_rewrites)
    implementation_guide = _build_implementation_guide(ctx, kept_rewrites)
    validation_notes = _build_validation_notes(ctx, confidence_score, kept_rewrites)

    headline = (
        f"Committee review improved audience consensus by {ctx.metrics.improvementPct:+.1f}% "
        f"for `{ctx.summary.documentName}` after testing {ctx.metrics.rewritesTested} rewrite ideas."
    )
    overview = (
        f"ElastiTune evaluated the document against {ctx.summary.personasCount} committee personas, "
        f"accepted {ctx.metrics.acceptedRewrites} rewrites, and moved the consensus score from "
        f"{ctx.metrics.baselineScore:.3f} to {ctx.metrics.bestScore:.3f}. "
        f"{len(changed_section_ids)} sections changed in the final recommendation."
    )
    next_steps = [
        "Start with the accepted rewrites that affected the lowest-scoring sections and review them with the document owner.",
        "Re-test the revised document with a real reviewer or seller before rollout so you confirm the language still sounds natural.",
        "Use the persona objections in this report as a checklist for speaker notes, follow-up email copy, or slide annotations.",
    ]

    narrative = _build_narrative_sections(
        ctx=ctx,
        confidence_score=confidence_score,
        kept_rewrites=kept_rewrites,
        persona_summary=persona_summary,
    )

    return CommitteeReport(
        runId=ctx.run_id,
        generatedAt=datetime.now(timezone.utc).isoformat(),
        summary=CommitteeReportSummary(
            headline=headline,
            overview=overview,
            nextSteps=next_steps,
            baselineScore=ctx.metrics.baselineScore,
            bestScore=ctx.metrics.bestScore,
            improvementPct=ctx.metrics.improvementPct,
            rewritesTested=ctx.metrics.rewritesTested,
            acceptedRewrites=ctx.metrics.acceptedRewrites,
            durationSeconds=duration_seconds,
            confidenceScore=confidence_score,
            personasCount=ctx.summary.personasCount,
            sectionsChanged=len(changed_section_ids),
            aiEvaluations=ctx.metrics.aiEvaluations,
            heuristicEvaluations=ctx.metrics.heuristicEvaluations,
            llmCoveragePct=ctx.metrics.llmCoveragePct,
        ),
        document=ctx.best_document,
        personas=ctx.personas,
        rewrites=ctx.rewrites,
        narrative=narrative,
        personaSummary=persona_summary,
        changeNarratives=change_narratives,
        implementationGuide=implementation_guide,
        validationNotes=validation_notes,
        evaluationMode=ctx.evaluation_mode,
        warnings=ctx.warnings,
    )


async def build_report_async(ctx: CommitteeRunContext) -> CommitteeReport:
    report = build_report(ctx)
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
        "You rewrite buying-committee optimization reports for non-technical business readers. "
        "Use plain English, stay faithful to the evidence, and do not invent claims."
    )
    user_prompt = (
        "Rewrite the committee report sections below into clearer plain English. "
        "Return JSON with keys `narrative` and `changeNarratives`. "
        "`narrative` must be an array of objects with `key` and `body`. "
        "`changeNarratives` must be an array of objects with `title`, `plainEnglish`, `expectedEffect`, and `whyItHelped`.\n\n"
        f"Headline: {report.summary.headline}\n"
        f"Confidence: {report.summary.confidenceScore:.0%}\n"
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

    updated_narrative = []
    for section in report.narrative:
        body = narrative_updates.get(section.key)
        updated_narrative.append(
            section.model_copy(
                update={"body": str(body), "source": "llm"} if body else {}
            )
        )

    updated_changes = []
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
        update={"narrative": updated_narrative, "changeNarratives": updated_changes},
        deep=True,
    )


def build_export_payload(ctx: CommitteeRunContext) -> CommitteeExportPayload:
    current_sections = {section.id: section for section in ctx.best_document.sections}
    exported_sections = []
    for section in ctx.baseline_document.sections:
        optimized = current_sections.get(section.id, section)
        exported_sections.append(
            CommitteeSectionExport(
                sectionId=section.id,
                title=section.title,
                originalContent=section.content,
                optimizedContent=optimized.content,
            )
        )
    sorted_personas = sorted(
        ctx.personas, key=lambda persona: persona.authorityWeight, reverse=True
    )
    excluded_titles = ("thank you", "appendix", "agenda")
    weak_sections = []
    for persona in sorted_personas:
        selected_for_persona = 0
        for section in sorted(persona.perSection, key=lambda item: item.compositeScore):
            lowered_title = section.sectionTitle.lower()
            if any(token in lowered_title for token in excluded_titles):
                continue
            weak_sections.append(
                {
                    "persona": persona.name,
                    "sectionId": section.sectionId,
                    "sectionTitle": section.sectionTitle,
                    "score": section.compositeScore,
                    "quote": section.reactionQuote,
                    "riskFlags": section.riskFlags,
                    "missing": section.missing,
                }
            )
            selected_for_persona += 1
            if selected_for_persona >= 2:
                break
    weak_sections = weak_sections[:10]

    actionable_feedback = []
    seen_section_ids = set()
    for item in weak_sections:
        if item["sectionId"] in seen_section_ids:
            continue
        seen_section_ids.add(item["sectionId"])
        actionable_feedback.append(
            {
                "sectionId": item["sectionId"],
                "sectionTitle": item["sectionTitle"],
                "whyItUnderperforms": item["quote"],
                "riskFlags": item["riskFlags"],
                "missing": item["missing"],
            }
        )

    return CommitteeExportPayload(
        runId=ctx.run_id,
        documentName=ctx.summary.documentName,
        exportedAt=datetime.now(timezone.utc).isoformat(),
        committeeSummary={
            "evaluationMode": ctx.evaluation_mode,
            "industryProfileId": ctx.summary.industryProfileId,
            "industryLabel": ctx.summary.industryLabel,
            "baselineScore": ctx.metrics.baselineScore,
            "bestScore": ctx.metrics.bestScore,
            "improvementPct": ctx.metrics.improvementPct,
            "acceptedRewrites": ctx.metrics.acceptedRewrites,
            "rewritesTested": ctx.metrics.rewritesTested,
            "aiEvaluations": ctx.metrics.aiEvaluations,
            "heuristicEvaluations": ctx.metrics.heuristicEvaluations,
            "llmCoveragePct": ctx.metrics.llmCoveragePct,
            "personas": [
                {
                    "name": persona.name,
                    "title": persona.title,
                    "authorityWeight": persona.authorityWeight,
                    "currentScore": persona.currentScore,
                    "topObjection": persona.topObjection,
                    "evaluationSource": persona.evaluationSource,
                }
                for persona in sorted_personas
            ],
        },
        sections=exported_sections,
        rewriteLog=ctx.rewrites,
        llmHandoff={
            "task": "Review this committee feedback and rewrite the document for the identified audience while preserving factual integrity.",
            "documentName": ctx.summary.documentName,
            "industryProfile": {
                "id": ctx.summary.industryProfileId,
                "label": ctx.summary.industryLabel,
            },
            "evaluationCoverage": {
                "aiEvaluations": ctx.metrics.aiEvaluations,
                "heuristicEvaluations": ctx.metrics.heuristicEvaluations,
                "llmCoveragePct": ctx.metrics.llmCoveragePct,
            },
            "targetAudience": [
                {
                    "name": persona.name,
                    "title": persona.title,
                    "priorities": persona.priorities,
                    "concerns": persona.concerns,
                    "topObjection": persona.topObjection,
                    "score": persona.currentScore,
                    "evaluationSource": persona.evaluationSource,
                }
                for persona in sorted_personas
            ],
            "documentSummary": {
                "sectionsCount": len(ctx.best_document.sections),
                "currentConsensusScore": ctx.metrics.bestScore,
                "keyWeakSpots": weak_sections,
            },
            "rewriteGoals": [
                "Improve scores for low-confidence personas without hurting supportive personas.",
                "Tighten unsupported claims and add caveats where needed.",
                "Increase audience specificity and objection preemption.",
            ],
            "actionableSectionFeedback": actionable_feedback,
            "materials": {
                "optimizedSections": [
                    {
                        "sectionId": section.sectionId,
                        "title": section.title,
                        "originalContent": section.originalContent,
                        "optimizedContent": section.optimizedContent,
                    }
                    for section in exported_sections
                ],
                "rewriteLog": [rewrite.model_dump() for rewrite in ctx.rewrites],
            },
            "suggestedPrompt": (
                "You are rewriting this document for the attached buying committee. "
                "Use the audience model, weak-spot list, and optimized sections to produce a cleaner, more persuasive version."
            ),
        },
    )


def _build_persona_summary(ctx: CommitteeRunContext) -> CommitteePersonaSummary:
    supportive_count = sum(
        1 for persona in ctx.personas if persona.sentiment == "supportive"
    )
    cautious_count = sum(
        1
        for persona in ctx.personas
        if persona.sentiment in {"cautiously_interested", "neutral"}
    )
    skeptical_count = sum(
        1 for persona in ctx.personas if persona.sentiment in {"skeptical", "opposed"}
    )
    sorted_personas = sorted(ctx.personas, key=lambda persona: persona.currentScore)
    top_blocker = sorted_personas[0].name if sorted_personas else None
    top_supporter = sorted_personas[-1].name if sorted_personas else None

    explanation = (
        f"This run simulated {ctx.summary.personasCount} buying-committee perspectives. "
        f"{supportive_count} ended supportive, {cautious_count} remained mixed or neutral, and {skeptical_count} still had meaningful objections. "
        "Use the blocker feedback to tighten the final message before sharing the revised document."
    )
    return CommitteePersonaSummary(
        supportiveCount=supportive_count,
        cautiousCount=cautious_count,
        skepticalCount=skeptical_count,
        topSupporter=top_supporter,
        topBlocker=top_blocker,
        explanation=explanation,
    )


def _build_change_narratives(
    ctx: CommitteeRunContext, kept_rewrites: List[Any]
) -> List[CommitteeChangeNarrative]:
    narratives: List[CommitteeChangeNarrative] = []
    for rewrite in sorted(kept_rewrites, key=lambda item: item.deltaPercent, reverse=True)[
        :6
    ]:
        evidence = [
            f"Accepted in rewrite {rewrite.experimentId} with a committee score change of {rewrite.deltaPercent:+.1f}%.",
            f"Worst persona drop was {rewrite.worstPersonaDrop:+.3f} and do-no-harm was {'satisfied' if rewrite.doNoHarmSatisfied else 'violated'}.",
        ]
        if rewrite.personaDeltas:
            best_persona = max(rewrite.personaDeltas.items(), key=lambda item: item[1])
            evidence.append(
                f"Biggest visible lift came from persona `{best_persona[0]}` at {best_persona[1]:+.3f}."
            )
        narratives.append(
            CommitteeChangeNarrative(
                experimentId=rewrite.experimentId,
                sectionId=rewrite.sectionId,
                sectionTitle=rewrite.sectionTitle,
                title=f"Section {rewrite.sectionId}: {rewrite.sectionTitle}",
                plainEnglish=(
                    f"ElastiTune rewrote the `{rewrite.sectionTitle}` section by changing `{rewrite.parameterName}`. "
                    f"In practice, this means the section text was revised from the earlier wording to a stronger version that the committee scored higher."
                ),
                expectedEffect=(
                    "The goal of this rewrite was to make the section clearer, more persuasive, or more evidence-backed for skeptical reviewers."
                ),
                whyItHelped=(
                    rewrite.description
                    or "The updated language better addressed committee concerns than the original wording."
                ),
                confidence=round(
                    min(
                        0.96,
                        max(
                            0.4,
                            0.58
                            + (0.16 if rewrite.deltaPercent > 5 else 0.08)
                            + (0.08 if rewrite.doNoHarmSatisfied else -0.12),
                        ),
                    ),
                    2,
                ),
                evidence=evidence,
            )
        )
    return narratives


def _build_implementation_guide(
    ctx: CommitteeRunContext, kept_rewrites: List[Any]
) -> CommitteeImplementationGuide:
    snippets = [
        _build_rewrite_snippet(rewrite)
        for rewrite in sorted(kept_rewrites, key=lambda item: item.deltaPercent, reverse=True)[
            :4
        ]
    ]
    return CommitteeImplementationGuide(
        summary=(
            "This rewrite guide shows the exact text changes ElastiTune recommends for the document sections that improved committee consensus the most."
        ),
        applyInstructions=[
            "Update the original document section with the revised wording shown below.",
            "Review each accepted rewrite with the document owner so the message still matches the real deal context.",
            "Pay extra attention to sections tied to blockers or skeptical personas before finalizing the deck or brief.",
        ],
        note=(
            "Line numbers refer to the excerpt shown in this report so a reviewer can see exactly which sentences changed."
        ),
        snippets=snippets,
    )


def _build_rewrite_snippet(rewrite: Any) -> CommitteeRewriteSnippet:
    before_lines = _text_to_lines(rewrite.beforeText)
    after_lines = _text_to_lines(rewrite.afterText)
    _mark_changed_lines(before_lines, after_lines)

    return CommitteeRewriteSnippet(
        title=f"Section {rewrite.sectionId}: {rewrite.sectionTitle}",
        target=f"Document section {rewrite.sectionId}",
        summary=(
            f"Accepted rewrite {rewrite.experimentId} changed `{rewrite.parameterName}` and moved the committee score {rewrite.deltaPercent:+.1f}%."
        ),
        beforeLines=before_lines,
        afterLines=after_lines,
    )


def _build_validation_notes(
    ctx: CommitteeRunContext, confidence_score: float, kept_rewrites: List[Any]
) -> List[CommitteeValidationNote]:
    notes = [
        CommitteeValidationNote(
            title="Committee coverage",
            body=(
                f"The report reflects {ctx.summary.personasCount} committee personas across `{ctx.summary.industryLabel}` in `{ctx.evaluation_mode}` mode."
            ),
            severity="info",
        ),
        CommitteeValidationNote(
            title="AI evaluation coverage",
            body=(
                f"{ctx.metrics.aiEvaluations} persona evaluations used an LLM and {ctx.metrics.heuristicEvaluations} used heuristics, for {ctx.metrics.llmCoveragePct:.0f}% LLM coverage."
            ),
            severity="success" if ctx.metrics.llmCoveragePct >= 50 else "info",
        ),
        CommitteeValidationNote(
            title="Do-no-harm guardrail",
            body=(
                f"The configured do-no-harm floor was {ctx.metrics.doNoHarmFloor:+.2f}. "
                f"{sum(1 for rewrite in kept_rewrites if rewrite.doNoHarmSatisfied)} accepted rewrites satisfied that guardrail."
            ),
            severity="success",
        ),
    ]
    if ctx.warnings:
        notes.append(
            CommitteeValidationNote(
                title="Run warnings",
                body="; ".join(ctx.warnings[:3]),
                severity="warning",
            )
        )
    notes.append(
        CommitteeValidationNote(
            title="Confidence",
            body=(
                f"ElastiTune assigns {confidence_score:.0%} confidence to this recommendation based on accepted rewrites, persona coverage, and whether the do-no-harm guardrail held."
            ),
            severity="info",
        )
    )
    return notes


def _build_narrative_sections(
    ctx: CommitteeRunContext,
    confidence_score: float,
    kept_rewrites: List[Any],
    persona_summary: CommitteePersonaSummary,
) -> List[CommitteeNarrativeSection]:
    strongest_rewrite = (
        max(kept_rewrites, key=lambda rewrite: rewrite.deltaPercent)
        if kept_rewrites
        else None
    )
    strongest_text = (
        f"The strongest accepted rewrite was in section {strongest_rewrite.sectionId}, `{strongest_rewrite.sectionTitle}`, which moved the score {strongest_rewrite.deltaPercent:+.1f}%."
        if strongest_rewrite
        else "No rewrite was accepted, so the report mostly explains the committee objections rather than final text changes."
    )
    return [
        CommitteeNarrativeSection(
            key="plain_english_summary",
            title="Plain-English Summary",
            body=(
                f"ElastiTune tested different wording changes against a simulated buying committee and found a version of the document that improved consensus by {ctx.metrics.improvementPct:+.1f}%. "
                f"In plain English: the revised document should land better with the target audience than the original version."
            ),
            audience="executive",
            confidence=confidence_score,
        ),
        CommitteeNarrativeSection(
            key="what_changed",
            title="What Changed",
            body=strongest_text,
            audience="operator",
            confidence=confidence_score,
        ),
        CommitteeNarrativeSection(
            key="persona_reaction",
            title="Persona Reaction",
            body=persona_summary.explanation,
            audience="operator",
            confidence=0.75,
        ),
        CommitteeNarrativeSection(
            key="implementation_readout",
            title="Implementation Readout",
            body=(
                "The implementation guide below shows the exact lines of document text that changed in the accepted rewrites so a human reviewer can approve or adapt them quickly."
            ),
            audience="technical",
            confidence=0.86,
        ),
    ]


def _compute_confidence_score(
    ctx: CommitteeRunContext, kept_rewrites: List[Any]
) -> float:
    score = 0.45
    if kept_rewrites:
        score += 0.15
    if ctx.summary.personasCount >= 4:
        score += 0.08
    if ctx.metrics.rewritesTested >= 8:
        score += 0.08
    if ctx.metrics.llmCoveragePct >= 40:
        score += 0.08
    if ctx.metrics.improvementPct > 0:
        score += 0.08
    if any(not rewrite.doNoHarmSatisfied for rewrite in kept_rewrites):
        score -= 0.12
    return round(min(0.97, max(0.35, score)), 2)


def _compute_duration_seconds(ctx: CommitteeRunContext) -> float:
    if ctx.metrics.elapsedSeconds > 0:
        return round(ctx.metrics.elapsedSeconds, 2)
    return 0.0


def _text_to_lines(text: str) -> List[CommitteeSnippetLine]:
    return [
        CommitteeSnippetLine(lineNumber=index + 1, content=line)
        for index, line in enumerate((text or "").splitlines() or [""])
    ]


def _mark_changed_lines(
    before_lines: List[CommitteeSnippetLine], after_lines: List[CommitteeSnippetLine]
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
            line.explanation = "This line was replaced or removed in the accepted rewrite."
        for line in after_lines[j1:j2]:
            line.changed = True
            line.explanation = "This line appears in the accepted rewrite."
