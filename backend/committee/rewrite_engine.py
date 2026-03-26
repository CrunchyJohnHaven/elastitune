from __future__ import annotations

import logging
import random
import re
from dataclasses import dataclass
from typing import Dict, Optional

from ..services.llm_service import LLMService
from .industry_profiles import IndustryProfile
from .models import DocumentSection

logger = logging.getLogger(__name__)


BASE_PARAMETER_VALUES: Dict[str, list[str]] = {
    "stat_framing": ["conservative", "moderate", "aggressive"],
    "proof_point_density": ["low", "medium", "high"],
    "cta_urgency": ["soft", "firm", "direct"],
    "objection_preemption": ["none", "light", "heavy"],
    "technical_depth": ["executive", "practitioner", "mixed"],
    "risk_narrative": ["opportunity", "threat", "balanced"],
}


@dataclass
class RewriteProposal:
    section_id: int
    parameter_name: str
    old_value: str
    new_value: str
    description: str
    rewritten_text: str


class CommitteeRewriteEngine:
    def __init__(
        self,
        profile: IndustryProfile,
        llm_service: Optional[LLMService] = None,
        warnings: Optional[list[str]] = None,
    ) -> None:
        self.profile = profile
        self.llm = llm_service
        self.warnings = warnings if warnings is not None else []

    async def propose(
        self,
        section: DocumentSection,
        state: Dict[int, Dict[str, str]],
        rng: random.Random,
        parameter_name: Optional[str] = None,
    ) -> RewriteProposal:
        parameter_space = {**BASE_PARAMETER_VALUES, **self.profile.parameter_values}
        chosen_parameter = parameter_name or rng.choice(list(parameter_space.keys()))
        current_value = state.get(section.id, {}).get(chosen_parameter, parameter_space[chosen_parameter][0])
        candidates = [value for value in parameter_space[chosen_parameter] if value != current_value]
        new_value = rng.choice(candidates)

        if self.llm and self.llm.available:
            try:
                rewritten = await self.llm.rewrite_committee_section(
                    section=section,
                    parameter_name=chosen_parameter,
                    old_value=current_value,
                    new_value=new_value,
                    industry_label=self.profile.label,
                    parameter_options=parameter_space,
                )
                if rewritten:
                    return RewriteProposal(
                        section_id=section.id,
                        parameter_name=chosen_parameter,
                        old_value=current_value,
                        new_value=new_value,
                        description=_description(chosen_parameter, new_value),
                        rewritten_text=rewritten.strip(),
                    )
            except Exception as exc:
                logger.warning(
                    "LLM rewrite failed for section=%s parameter=%s: %s",
                    section.id,
                    chosen_parameter,
                    exc,
                )
                self._warn_once("AI rewrite generation failed for one or more sections; rule-based rewriting was used instead.")

        return RewriteProposal(
            section_id=section.id,
            parameter_name=chosen_parameter,
            old_value=current_value,
            new_value=new_value,
            description=_description(chosen_parameter, new_value),
            rewritten_text=_heuristic_rewrite(self.profile, section, chosen_parameter, new_value),
        )

    def _warn_once(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)


def _description(parameter_name: str, new_value: str) -> str:
    descriptions = {
        "stat_framing": {
            "conservative": "Softened the statistical framing and added caveat language.",
            "moderate": "Balanced the headline numbers with steadier proof language.",
            "aggressive": "Led with the strongest measurable outcome to sharpen urgency.",
        },
        "proof_point_density": {
            "low": "Reduced supporting proof to keep the story tighter and faster.",
            "medium": "Added a second proof anchor so the claim feels better supported.",
            "high": "Layered in multiple proof anchors to make the case feel more defensible.",
        },
        "cta_urgency": {
            "soft": "Softened the next step so the ask feels easier to accept.",
            "firm": "Made the next step more concrete with a specific working session ask.",
            "direct": "Turned the close into a direct scheduling ask with near-term urgency.",
        },
        "objection_preemption": {
            "none": "Removed up-front objection handling to keep the section leaner.",
            "light": "Added one objection-preemption line to reduce likely pushback.",
            "heavy": "Front-loaded multiple objection-handling cues before the room can raise them.",
        },
        "technical_depth": {
            "executive": "Shifted the section toward business outcomes and governance language.",
            "practitioner": "Added implementation detail around architecture, rollout, and ownership.",
            "mixed": "Balanced executive framing with a short technical proof layer.",
        },
        "risk_narrative": {
            "opportunity": "Reframed the section around upside and forward momentum.",
            "threat": "Led with downside risk to make inaction feel more costly.",
            "balanced": "Balanced the downside of waiting with the upside of moving now.",
        },
        "social_proof_type": {
            "internal": "Anchored the proof around Elastic's own operating outcomes.",
            "external": "Swapped in customer-facing proof to increase credibility.",
            "peer_company": "Shifted proof toward a peer-company example closer to this buyer.",
            "analyst_report": "Added third-party market validation to reduce vendor-only bias.",
            "federal": "Shifted proof toward federal deployment familiarity and procurement comfort.",
        },
        "specificity": {
            "general": "Pulled the language back toward a broader buyer-ready narrative.",
            "role_tailored": "Tailored the language to the specific stakeholder role.",
            "vertical_tailored": "Tailored the section to this industry's buying dynamics.",
            "agency_tailored": "Tailored the section more directly to the target agency context.",
            "hyper_specific": "Made the language feel prepared for this exact room and workflow.",
        },
    }
    return descriptions.get(parameter_name, {}).get(
        new_value,
        f"Adjusted {parameter_name.replace('_', ' ')} to {new_value}.",
    )


def _heuristic_rewrite(
    profile: IndustryProfile,
    section: DocumentSection,
    parameter_name: str,
    new_value: str,
) -> str:
    text = re.sub(r"\s+", " ", section.content.strip())
    if not text:
        return text

    sentences = _split_sentences(text)

    if parameter_name == "stat_framing":
        return _rewrite_stat_framing(text, sentences, section, new_value)
    if parameter_name == "proof_point_density":
        return _rewrite_proof_density(profile, text, section, new_value)
    if parameter_name == "cta_urgency":
        return _replace_or_append_cta(text, _cta_text(profile, new_value))
    if parameter_name == "objection_preemption":
        return _prepend_objection_preemption(text, profile, new_value)
    if parameter_name == "technical_depth":
        return _rewrite_technical_depth(text, new_value)
    if parameter_name == "risk_narrative":
        return _rewrite_risk_narrative(text, section, new_value)
    if parameter_name == "social_proof_type":
        return _rewrite_social_proof(profile, text, new_value)
    if parameter_name == "specificity":
        return _rewrite_specificity(profile, section, text, new_value)

    return text


def _rewrite_stat_framing(text: str, sentences: list[str], section: DocumentSection, new_value: str) -> str:
    if not sentences:
        return text
    lead = sentences[0]
    remainder = " ".join(sentences[1:]).strip()
    stat = section.stats[0] if section.stats else "the measurable impact"

    if new_value == "conservative":
        prefix = f"Based on the available evidence, {lead[0].lower() + lead[1:]}" if lead else text
        suffix = "These figures should be interpreted as directional and validated against the buyer's operating context."
        return " ".join(part for part in [prefix, remainder, suffix] if part).strip()
    if new_value == "aggressive":
        prefix = f"{stat} is the headline outcome here."
        return " ".join(part for part in [prefix, lead, remainder] if part).strip()
    suffix = "The figures are presented as material, but grounded in the cited evidence and assumptions."
    return " ".join(part for part in [lead, remainder, suffix] if part).strip()


def _rewrite_proof_density(profile: IndustryProfile, text: str, section: DocumentSection, new_value: str) -> str:
    existing = list(dict.fromkeys(section.proofPoints))[:3]
    fallback = {
        "government": "public-sector deployment proof",
        "enterprise_tech": "peer technology migration proof",
        "financial_services": "regulated-industry control evidence",
        "healthcare": "provider or health-system proof point",
        "general_enterprise": "peer customer outcome evidence",
    }.get(profile.id, "peer customer outcome evidence")

    desired_count = {"low": 1, "medium": 2, "high": 3}[new_value]
    proof_points = existing[:desired_count]
    while len(proof_points) < desired_count:
        proof_points.append(fallback)

    proof_clause = " Proof anchors: " + "; ".join(proof_points) + "."
    return f"{text.rstrip('.')}." + proof_clause


def _cta_text(profile: IndustryProfile, new_value: str) -> str:
    noun = {
        "government": "working session",
        "enterprise_tech": "migration planning session",
        "financial_services": "decision workshop",
        "healthcare": "operating-model review",
        "general_enterprise": "working session",
    }.get(profile.id, "working session")
    if new_value == "soft":
        return f"If useful, we would welcome a short {noun} to validate fit."
    if new_value == "firm":
        return f"The next step is a 60-minute {noun} this month to validate scope and fit."
    return f"Schedule the 60-minute {noun} now so the team can pressure-test the plan this month."


def _prepend_objection_preemption(text: str, profile: IndustryProfile, new_value: str) -> str:
    if new_value == "none":
        return text
    preface_map = {
        "government": "This is positioned to support human decision-making, preserve traceability, and fit existing control expectations.",
        "enterprise_tech": "This is positioned to lower operational drag, support phased migration, and preserve control clarity.",
        "financial_services": "This is positioned to strengthen defensibility, governance, and audit readiness without overstating automation.",
        "healthcare": "This is positioned to improve workflow outcomes while preserving oversight, privacy, and auditability.",
        "general_enterprise": "This is positioned to improve outcomes while keeping the rollout practical, governable, and low risk.",
    }
    preface = preface_map.get(profile.id, preface_map["general_enterprise"])
    if new_value == "heavy":
        preface += " It addresses likely buyer concerns up front instead of forcing the room to infer them."
    return f"{preface} {text}".strip()


def _rewrite_technical_depth(text: str, new_value: str) -> str:
    if new_value == "executive":
        trimmed = re.sub(r"\b(architecture|kubernetes|api|certificate|ingest|replication|cluster|deployment)\b", "", text, flags=re.I)
        trimmed = re.sub(r"\s{2,}", " ", trimmed).strip()
        return f"{trimmed} The emphasis stays on outcomes, adoption, and governance."
    if new_value == "practitioner":
        return f"{text} Implementation detail: call out architecture fit, integration surfaces, rollout sequencing, and operating ownership."
    return f"{text} Add one short technical note after the business outcome so both executives and practitioners can follow the argument."


def _rewrite_risk_narrative(text: str, section: DocumentSection, new_value: str) -> str:
    headline = section.stats[0] if section.stats else "the current operating risk"
    if new_value == "opportunity":
        return f"The upside is the lead story: {headline} can be recovered, accelerated, or made more defensible. {text}"
    if new_value == "threat":
        return f"The downside is the lead story: today's operating model leaves {headline} exposed. {text}"
    return f"{text} This frames both the downside of staying put and the upside of moving now."


def _rewrite_social_proof(profile: IndustryProfile, text: str, new_value: str) -> str:
    proof = {
        "internal": "Reference Elastic's own operating improvements as a proof anchor.",
        "external": "Reference a named customer outcome with measurable before/after change.",
        "peer_company": "Reference a peer-company deployment that feels close to this buyer's world.",
        "analyst_report": "Reference a third-party analyst or market-validation proof point.",
        "federal": "Reference public-sector scale proof and procurement familiarity.",
    }.get(new_value, "Reference a relevant proof point.")
    return f"{text} {proof}"


def _rewrite_specificity(profile: IndustryProfile, section: DocumentSection, text: str, new_value: str) -> str:
    if new_value == "general":
        return text
    if new_value == "role_tailored":
        return f"{text} Tailor the language to the specific decision-maker concerns this section is meant to answer."
    if new_value == "vertical_tailored":
        return f"{text} Tailor the language to {profile.label.lower()} buying dynamics and operating constraints."
    return f"{text} Make the section feel prepared for this exact room by naming the workflow, objections, and decision criteria directly."


def _replace_or_append_cta(text: str, new_cta: str) -> str:
    sentences = _split_sentences(text)
    cta_tokens = ("schedule", "next step", "demo", "discovery", "call", "session")
    updated: list[str] = []
    replaced = False
    for sentence in sentences:
        if any(token in sentence.lower() for token in cta_tokens):
            if not replaced:
                updated.append(new_cta)
                replaced = True
            continue
        updated.append(sentence)
    if not replaced:
        updated.append(new_cta)
    return " ".join(part.strip() for part in updated if part.strip())


def _split_sentences(text: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    return parts or [text]
