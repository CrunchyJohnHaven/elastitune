from __future__ import annotations

import logging
import re
from typing import Dict, Iterable, List, Optional

from ..services.llm_service import LLMService
from .industry_profiles import IndustryProfile, IndustryRiskRule
from .models import (
    CommitteeEmotion,
    CommitteeEvaluationMode,
    CommitteePersona,
    CommitteePersonaView,
    DocumentSection,
    PersonaSectionRollup,
    SectionEvaluation,
    SectionScoreBreakdown,
)

logger = logging.getLogger(__name__)

KEYWORD_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_/-]{2,}")


class CommitteeEvaluator:
    def __init__(
        self,
        profile: IndustryProfile,
        llm_service: Optional[LLMService] = None,
        warnings: Optional[List[str]] = None,
    ) -> None:
        self.profile = profile
        self.llm = llm_service
        self.warnings = warnings if warnings is not None else []

    async def evaluate_section(
        self,
        persona: CommitteePersona,
        section: DocumentSection,
    ) -> SectionEvaluation:
        if self.llm and self.llm.available:
            try:
                llm_result = await self.llm.evaluate_committee_section(persona, section)
                if llm_result:
                    return SectionEvaluation(
                        personaId=persona.id,
                        sectionId=section.id,
                        sectionTitle=section.title,
                        scores=SectionScoreBreakdown(
                            relevance=float(llm_result["relevance"]),
                            persuasiveness=float(llm_result["persuasiveness"]),
                            evidenceQuality=float(llm_result["evidence_quality"]),
                            riskScore=1.0 - min(len(llm_result.get("risk_flags", [])) * 0.12, 0.7),
                            completeness=max(
                                0.0,
                                1.0 - min(len(llm_result.get("missing", [])) * 0.15, 0.75),
                            ),
                        ),
                        riskFlags=list(llm_result.get("risk_flags", [])),
                        missing=list(llm_result.get("missing", [])),
                        emotionalResponse=_map_emotional_response(
                            str(llm_result.get("emotional_response", "neutral"))
                        ),
                        reactionQuote=str(llm_result.get("reaction_quote", "")).strip(),
                        compositeScore=_bounded(float(llm_result["composite_score"])),
                        source="llm",
                        confidence=0.92,
                    )
            except Exception as exc:
                logger.warning(
                    "LLM evaluation failed for persona=%s section=%s: %s",
                    persona.id,
                    section.id,
                    exc,
                )
                self._warn_once("AI evaluation failed for one or more sections; heuristic scoring was used instead.")

        return self._heuristic_evaluation(persona, section)

    async def evaluate_document(
        self,
        personas: List[CommitteePersona],
        sections: List[DocumentSection],
    ) -> Dict[tuple[int, str], SectionEvaluation]:
        results: Dict[tuple[int, str], SectionEvaluation] = {}
        for section in sections:
            for persona in personas:
                evaluation = await self.evaluate_section(persona, section)
                results[(section.id, persona.id)] = evaluation
        return results

    def rollup_persona_view(
        self,
        persona: CommitteePersona,
        sections: List[DocumentSection],
        evaluations: Dict[tuple[int, str], SectionEvaluation],
        latest_section_id: Optional[int] = None,
    ) -> CommitteePersonaView:
        per_section: List[PersonaSectionRollup] = []
        total_score = 0.0
        all_flags: List[str] = []
        all_missing: List[str] = []
        strongest_quote = ""
        top_objection = None
        sources: List[str] = []
        confidences: List[float] = []

        for section in sections:
            evaluation = evaluations[(section.id, persona.id)]
            per_section.append(
                PersonaSectionRollup(
                    sectionId=section.id,
                    sectionTitle=section.title,
                    compositeScore=round(evaluation.compositeScore, 4),
                    reactionQuote=evaluation.reactionQuote,
                    riskFlags=evaluation.riskFlags[:2],
                    missing=evaluation.missing[:2],
                    source=evaluation.source,
                    confidence=evaluation.confidence,
                )
            )
            total_score += evaluation.compositeScore
            all_flags.extend(evaluation.riskFlags)
            all_missing.extend(evaluation.missing)
            sources.append(evaluation.source)
            confidences.append(evaluation.confidence)
            if section.id == latest_section_id:
                strongest_quote = evaluation.reactionQuote
            if not top_objection and evaluation.riskFlags:
                top_objection = evaluation.riskFlags[0]

        average_score = total_score / max(len(sections), 1)
        if not strongest_quote:
            strongest_quote = max(
                (
                    evaluations[(section.id, persona.id)].reactionQuote
                    for section in sections
                ),
                key=len,
                default="",
            )

        sentiment = _score_to_sentiment(average_score)
        evaluation_source = "mixed" if len(set(sources)) > 1 else (sources[0] if sources else "heuristic")
        evaluation_confidence = round(sum(confidences) / max(len(confidences), 1), 2)
        return CommitteePersonaView(
            id=persona.id,
            name=persona.name,
            title=persona.title,
            roleInDecision=persona.roleInDecision,
            authorityWeight=persona.authorityWeight,
            skepticismLevel=persona.skepticismLevel,
            sentiment=sentiment,
            currentScore=round(average_score, 4),
            supportScore=round(max(0.0, min(1.0, average_score - persona.skepticismLevel * 0.02)), 4),
            reactionQuote=strongest_quote or "Needs stronger proof before moving forward.",
            topObjection=top_objection,
            riskFlags=list(dict.fromkeys(all_flags))[:4],
            missing=list(dict.fromkeys(all_missing))[:4],
            perSection=per_section,
            priorities=persona.priorities,
            concerns=persona.concerns,
            evaluationSource=evaluation_source,  # type: ignore[arg-type]
            evaluationConfidence=evaluation_confidence,
        )

    def consensus_score(
        self,
        personas: List[CommitteePersonaView],
        mode: CommitteeEvaluationMode = "full_committee",
    ) -> float:
        active = self.personas_for_mode(personas, mode)
        total_weight = sum(max(persona.authorityWeight, 0.0) for persona in active) or 1.0
        return round(
            sum(persona.currentScore * max(persona.authorityWeight, 0.0) for persona in active) / total_weight,
            4,
        )

    def personas_for_mode(
        self,
        personas: List[CommitteePersonaView],
        mode: CommitteeEvaluationMode,
    ) -> List[CommitteePersonaView]:
        if not personas:
            return personas
        if mode == "adversarial":
            return [min(personas, key=lambda persona: persona.currentScore)]
        if mode == "champion_only":
            champions = [
                persona for persona in personas
                if persona.sentiment in {"supportive", "cautiously_interested"}
            ]
            return champions or personas
        return personas

    def _heuristic_evaluation(
        self,
        persona: CommitteePersona,
        section: DocumentSection,
    ) -> SectionEvaluation:
        content = section.content
        content_keywords = _token_set(content)
        persona_keywords = _token_set(" ".join(
            persona.priorities
            + persona.concerns
            + persona.decisionCriteria
            + persona.likelyObjections
            + persona.whatWinsThemOver
        ))

        overlap = len(content_keywords & persona_keywords)
        relevance = _bounded(0.22 + overlap * 0.08)
        evidence_quality = _bounded(
            0.18
            + min(len(section.stats), 4) * 0.09
            + min(len(section.proofPoints), 3) * 0.11
        )
        persuasion_bonus = 0.08 if section.cta else 0.0
        persuasion_bonus += 0.08 if any(
            _contains_phrase(content, phrase) for phrase in persona.whatWinsThemOver
        ) else 0.0
        persuasiveness = _bounded(0.2 + overlap * 0.06 + persuasion_bonus)

        risk_flags = _risk_flags(self.profile, persona, section)
        missing = _missing_items(persona, section)
        risk_score = _bounded(1.0 - min(0.75, len(risk_flags) * 0.18))
        completeness = _bounded(1.0 - min(0.75, len(missing) * 0.17))

        composite = (
            relevance * 0.30
            + persuasiveness * 0.25
            + evidence_quality * 0.25
            + risk_score * 0.10
            + completeness * 0.10
        )
        quote = _reaction_quote(persona, risk_flags, missing, composite)
        emotional = "positive" if composite >= 0.65 else "negative" if composite < 0.42 else "neutral"

        return SectionEvaluation(
            personaId=persona.id,
            sectionId=section.id,
            sectionTitle=section.title,
            scores=SectionScoreBreakdown(
                relevance=round(relevance, 4),
                persuasiveness=round(persuasiveness, 4),
                evidenceQuality=round(evidence_quality, 4),
                riskScore=round(risk_score, 4),
                completeness=round(completeness, 4),
            ),
            riskFlags=risk_flags,
            missing=missing,
            emotionalResponse=emotional,
            reactionQuote=quote,
            compositeScore=round(composite, 4),
            source="heuristic",
            confidence=0.45,
        )

    def _warn_once(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)


def _risk_flags(profile: IndustryProfile, persona: CommitteePersona, section: DocumentSection) -> List[str]:
    flags: List[str] = []
    lowered = section.content.lower()
    persona_context = " ".join(
        [persona.title, persona.roleInDecision] + persona.concerns + persona.decisionCriteria
    ).lower()

    if section.stats and len(section.proofPoints) == 0:
        flags.append("Claims need source attribution.")
    if any(token in lowered for token in ("ai", "autonomous", "automate")) and any(
        marker in persona_context for marker in ("liability", "control", "trust", "skeptic", "risk")
    ):
        flags.append("AI framing may trigger skepticism.")
    if persona.skepticismLevel >= 8 and len(section.stats) >= 3 and "sample" not in lowered and "caveat" not in lowered:
        flags.append("Bold statistics may not survive scrutiny.")

    for rule in profile.risk_rules:
        if _matches_rule(rule, lowered, persona_context):
            flags.append(rule.flag_text)

    return list(dict.fromkeys(flags))[:3]


def _matches_rule(rule: IndustryRiskRule, lowered_content: str, persona_context: str) -> bool:
    if rule.present_terms and not any(term in lowered_content for term in rule.present_terms):
        return False
    if rule.persona_keywords and not any(keyword in persona_context for keyword in rule.persona_keywords):
        return False
    if rule.absent_terms and any(term in lowered_content for term in rule.absent_terms):
        return False
    return True


def _missing_items(persona: CommitteePersona, section: DocumentSection) -> List[str]:
    missing: List[str] = []
    lowered = section.content.lower()
    for criterion in persona.decisionCriteria[:4]:
        keywords = _token_set(criterion)
        if keywords and not keywords.intersection(_token_set(lowered)):
            missing.append(criterion)
    return list(dict.fromkeys(missing))[:3]


def _reaction_quote(
    persona: CommitteePersona,
    risk_flags: List[str],
    missing: List[str],
    composite: float,
) -> str:
    if risk_flags:
        return risk_flags[0]
    if missing:
        return f"I still need to see {missing[0].lower()} before I can support this."
    if composite >= 0.72:
        return f"This section speaks directly to my priorities around {persona.priorities[0].lower()}."
    if composite >= 0.55:
        return "This is moving in the right direction, but I need one more concrete proof point."
    return "I'm not convinced yet; this still feels too generic for our buying committee."


def _contains_phrase(content: str, phrase: str) -> bool:
    return any(token in content.lower() for token in _token_set(phrase))


def _token_set(text: str) -> set[str]:
    return {match.group(0).lower() for match in KEYWORD_RE.finditer(text.lower())}


def _bounded(value: float) -> float:
    return max(0.0, min(1.0, value))


def _score_to_sentiment(score: float) -> str:
    if score >= 0.72:
        return "supportive"
    if score >= 0.58:
        return "cautiously_interested"
    if score >= 0.45:
        return "neutral"
    if score >= 0.32:
        return "skeptical"
    return "opposed"


def _map_emotional_response(value: str) -> CommitteeEmotion:
    lowered = value.replace(" ", "_").lower()
    if lowered in {"supportive", "cautiously_interested"}:
        return "positive"
    if lowered in {"skeptical", "opposed", "negative"}:
        return "negative"
    return "neutral"
