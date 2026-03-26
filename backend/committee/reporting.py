from __future__ import annotations

from datetime import datetime, timezone

from .models import (
    CommitteeExportPayload,
    CommitteeReport,
    CommitteeReportSummary,
    CommitteeSectionExport,
)
from .runtime import CommitteeRunContext


def build_report(ctx: CommitteeRunContext) -> CommitteeReport:
    headline = (
        f"Committee mode evaluated `{ctx.summary.documentName}` across "
        f"{ctx.summary.personasCount} buying committee personas and tested "
        f"{ctx.metrics.rewritesTested} rewrites. Consensus improved from "
        f"{ctx.metrics.baselineScore:.4f} to {ctx.metrics.bestScore:.4f} "
        f"({ctx.metrics.improvementPct:+.1f}%)."
    )
    return CommitteeReport(
        runId=ctx.run_id,
        generatedAt=datetime.now(timezone.utc).isoformat(),
        summary=CommitteeReportSummary(
            headline=headline,
            baselineScore=ctx.metrics.baselineScore,
            bestScore=ctx.metrics.bestScore,
            improvementPct=ctx.metrics.improvementPct,
            rewritesTested=ctx.metrics.rewritesTested,
            acceptedRewrites=ctx.metrics.acceptedRewrites,
        ),
        document=ctx.best_document,
        personas=ctx.personas,
        rewrites=ctx.rewrites,
        evaluationMode=ctx.evaluation_mode,
        warnings=ctx.warnings,
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
