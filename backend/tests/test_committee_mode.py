from __future__ import annotations

import asyncio

from backend.committee.document_parser import parse_document_bytes
from backend.committee.evaluator import CommitteeEvaluator
from backend.committee.industry_profiles import get_industry_profile
from backend.committee.models import CommitteePersonaView
from backend.committee.personas import build_committee_personas


def test_broken_pdf_falls_back_with_warning() -> None:
    document = parse_document_bytes(
        "broken.pdf",
        b"this is not a real pdf but it mentions observability, migration, and elastic cloud",
    )

    assert document.parseMode == "fallback"
    assert document.parseWarnings
    assert len(document.sections) >= 1


def test_enterprise_document_uses_enterprise_profile_not_sba() -> None:
    document = parse_document_bytes(
        "csc.txt",
        (
            b"Accelerating observability modernization on Elastic Cloud.\n\n"
            b"Reduce patching, simplify migration, improve FinOps visibility, and lower operational toil."
        ),
    )

    result = asyncio.run(
        build_committee_personas(
            document=document,
            committee_description="",
            provided_personas=None,
            use_seed_personas=False,
            llm_service=None,
        )
    )

    assert result.profile.id == "enterprise_tech"
    titles = [persona.title for persona in result.personas]
    assert "Chief Information Officer / CTO" in titles
    assert "General Counsel" not in titles


def test_evaluation_modes_are_real() -> None:
    evaluator = CommitteeEvaluator(get_industry_profile("general_enterprise"))
    personas = [
        CommitteePersonaView(
            id="supporter",
            name="Supporter",
            title="Champion",
            roleInDecision="Champion",
            authorityWeight=0.5,
            skepticismLevel=3,
            sentiment="supportive",
            currentScore=0.82,
            supportScore=0.8,
            reactionQuote="Looks strong.",
            topObjection=None,
            riskFlags=[],
            missing=[],
            perSection=[],
            priorities=[],
            concerns=[],
            evaluationSource="heuristic",
            evaluationConfidence=0.5,
        ),
        CommitteePersonaView(
            id="skeptic",
            name="Skeptic",
            title="Skeptic",
            roleInDecision="Blocker",
            authorityWeight=0.5,
            skepticismLevel=9,
            sentiment="skeptical",
            currentScore=0.28,
            supportScore=0.1,
            reactionQuote="Needs work.",
            topObjection="Missing proof",
            riskFlags=["Missing proof"],
            missing=["ROI support"],
            perSection=[],
            priorities=[],
            concerns=[],
            evaluationSource="heuristic",
            evaluationConfidence=0.5,
        ),
    ]

    full_committee = evaluator.consensus_score(personas, "full_committee")
    adversarial = evaluator.consensus_score(personas, "adversarial")
    champion_only = evaluator.consensus_score(personas, "champion_only")

    assert full_committee == 0.55
    assert adversarial == 0.28
    assert champion_only == 0.82
