from __future__ import annotations

import asyncio

from backend.committee.industry_profiles import get_industry_profile
from backend.committee.models import (
    CommitteeDocument,
    CommitteePersona,
    CommitteePersonaView,
    DocumentSection,
    RewriteAttempt,
)
from backend.committee.reporting import build_report, build_report_async
from backend.committee.runtime import CommitteeConnectionContext, CommitteeRunContext


def _make_ctx() -> CommitteeRunContext:
    document = CommitteeDocument(
        documentId="doc_1",
        documentName="Executive plan.md",
        sourceType="md",
        sections=[
            DocumentSection(
                id=1,
                title="Why change now",
                content="Our current platform creates delays and unclear outcomes.",
            ),
            DocumentSection(
                id=2,
                title="Business impact",
                content="Elastic can reduce risk and improve visibility.",
            ),
        ],
    )
    personas = [
        CommitteePersona(
            id="cio",
            name="Alex",
            title="CIO",
            organization="Buyer",
            roleInDecision="Executive sponsor",
            authorityWeight=0.5,
        ),
        CommitteePersona(
            id="cfo",
            name="Jamie",
            title="CFO",
            organization="Buyer",
            roleInDecision="Financial approver",
            authorityWeight=0.5,
        ),
    ]
    persona_views = [
        CommitteePersonaView(
            id="cio",
            name="Alex",
            title="CIO",
            roleInDecision="Executive sponsor",
            authorityWeight=0.5,
            skepticismLevel=3,
            sentiment="supportive",
            currentScore=0.81,
            supportScore=0.78,
            reactionQuote="This now reads like a credible modernization plan.",
            topObjection=None,
            riskFlags=[],
            missing=[],
            perSection=[],
            priorities=["speed", "risk reduction"],
            concerns=["migration risk"],
            evaluationSource="mixed",
            evaluationConfidence=0.75,
        ),
        CommitteePersonaView(
            id="cfo",
            name="Jamie",
            title="CFO",
            roleInDecision="Financial approver",
            authorityWeight=0.5,
            skepticismLevel=8,
            sentiment="skeptical",
            currentScore=0.39,
            supportScore=0.32,
            reactionQuote="Better, but I still want firmer financial proof.",
            topObjection="Needs clearer ROI evidence.",
            riskFlags=["ROI clarity"],
            missing=["Cost avoidance detail"],
            perSection=[],
            priorities=["ROI", "risk control"],
            concerns=["budget risk"],
            evaluationSource="mixed",
            evaluationConfidence=0.72,
        ),
    ]
    connection = CommitteeConnectionContext(
        connection_id="committee_conn",
        document=document,
        personas=personas,
        profile=get_industry_profile("general_enterprise"),
        evaluation_mode="full_committee",
    )
    ctx = CommitteeRunContext(
        run_id="committee_run",
        connection=connection,
        persona_views=persona_views,
        max_rewrites=6,
        duration_minutes=2,
        auto_stop_on_plateau=True,
    )
    ctx.metrics.baselineScore = 0.46
    ctx.metrics.bestScore = 0.61
    ctx.metrics.improvementPct = 32.6
    ctx.metrics.rewritesTested = 4
    ctx.metrics.acceptedRewrites = 2
    ctx.metrics.elapsedSeconds = 94
    ctx.metrics.aiEvaluations = 6
    ctx.metrics.heuristicEvaluations = 4
    ctx.metrics.llmCoveragePct = 60
    ctx.warnings = ["One section still lacks quantified ROI proof."]
    ctx.rewrites = [
        RewriteAttempt(
            experimentId=1,
            timestamp="2026-03-26T12:00:00Z",
            sectionId=1,
            sectionTitle="Why change now",
            parameterName="opening",
            oldValue="Our current platform creates delays and unclear outcomes.",
            newValue="Teams lose time because the current platform hides operational risk.",
            description="The revised opening made the urgency clearer and more executive-friendly.",
            baselineScore=0.46,
            candidateScore=0.55,
            deltaAbsolute=0.09,
            deltaPercent=19.6,
            decision="kept",
            doNoHarmSatisfied=True,
            worstPersonaDrop=-0.01,
            beforeText="Our current platform creates delays and unclear outcomes.",
            afterText="Teams lose time because the current platform hides operational risk.",
            personaDeltas={"cio": 0.09, "cfo": 0.04},
            durationMs=1200,
        ),
        RewriteAttempt(
            experimentId=2,
            timestamp="2026-03-26T12:01:00Z",
            sectionId=2,
            sectionTitle="Business impact",
            parameterName="proof",
            oldValue="Elastic can reduce risk and improve visibility.",
            newValue="Elastic can reduce incident response risk, improve visibility, and create a clearer path to measurable ROI.",
            description="The new version tied product value to risk and ROI in language a financial approver can follow.",
            baselineScore=0.55,
            candidateScore=0.61,
            deltaAbsolute=0.06,
            deltaPercent=10.9,
            decision="kept",
            doNoHarmSatisfied=True,
            worstPersonaDrop=0.0,
            beforeText="Elastic can reduce risk and improve visibility.",
            afterText="Elastic can reduce incident response risk, improve visibility, and create a clearer path to measurable ROI.",
            personaDeltas={"cio": 0.03, "cfo": 0.08},
            durationMs=1100,
        ),
    ]
    return ctx


def test_committee_report_includes_narrative_and_summary() -> None:
    report = build_report(_make_ctx())

    assert report.summary.durationSeconds == 94
    assert report.summary.confidenceScore > 0.5
    assert report.summary.personasCount == 2
    assert report.summary.sectionsChanged == 2
    assert "consensus score" in report.summary.overview
    assert len(report.summary.nextSteps) == 3
    assert report.narrative
    assert report.narrative[0].key == "plain_english_summary"


def test_committee_report_includes_persona_and_change_details() -> None:
    report = build_report(_make_ctx())

    assert report.personaSummary is not None
    assert report.personaSummary.supportiveCount == 1
    assert report.personaSummary.skepticalCount == 1
    assert report.personaSummary.topBlocker == "Jamie"
    assert report.changeNarratives
    assert "Why change now" in report.changeNarratives[0].title
    assert report.changeNarratives[0].confidence > 0.5


def test_committee_report_includes_implementation_guide() -> None:
    report = build_report(_make_ctx())

    assert report.implementationGuide is not None
    assert report.implementationGuide.snippets
    snippet = report.implementationGuide.snippets[0]
    assert snippet.beforeLines[0].lineNumber == 1
    assert any(line.changed for line in snippet.afterLines)


def test_committee_report_serializes_new_fields() -> None:
    report = build_report(_make_ctx())
    data = report.model_dump()

    assert "narrative" in data
    assert "personaSummary" in data
    assert "implementationGuide" in data
    assert data["summary"]["confidenceScore"] > 0


def test_committee_async_report_without_llm_matches_sync_shape() -> None:
    ctx = _make_ctx()
    report = asyncio.run(build_report_async(ctx))

    assert report.narrative
    assert report.changeNarratives
    assert report.implementationGuide is not None
