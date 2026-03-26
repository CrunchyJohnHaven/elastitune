from __future__ import annotations

from dataclasses import dataclass, field
import uuid
from typing import List, Optional

from .industry_profiles import IndustryProfile, detect_industry_profile
from .models import CommitteeDocument, CommitteePersona


_SEED_PERSONA_DETAILS = [
    {
        "roleInDecision": "economic_buyer",
        "authorityWeight": 0.24,
        "priorities": ["Clear business value", "Risk-adjusted return", "Practical rollout"],
        "concerns": ["Budget exposure", "Time to value", "Change management burden"],
        "decisionCriteria": ["ROI clarity", "Executive fit", "Delivery confidence"],
        "likelyObjections": ["The financial case is not concrete enough."],
        "whatWinsThemOver": ["Measured outcomes", "Short path to production value"],
        "skepticismLevel": 6,
        "domainExpertise": "business",
        "politicalMotivations": ["Avoid a visible failed initiative"],
    },
    {
        "roleInDecision": "technical_buyer",
        "authorityWeight": 0.22,
        "priorities": ["Architecture fit", "Operational simplicity", "Security posture"],
        "concerns": ["Integration complexity", "Operational overhead", "Migration risk"],
        "decisionCriteria": ["Implementation feasibility", "Platform alignment", "Supportability"],
        "likelyObjections": ["The technical rollout path is underspecified."],
        "whatWinsThemOver": ["Concrete implementation plan", "Evidence of low operational burden"],
        "skepticismLevel": 7,
        "domainExpertise": "technical",
        "politicalMotivations": ["Protect team capacity"],
    },
    {
        "roleInDecision": "risk_reviewer",
        "authorityWeight": 0.18,
        "priorities": ["Control coverage", "Compliance posture", "Auditability"],
        "concerns": ["Security gaps", "Missing caveats", "Approval risk"],
        "decisionCriteria": ["Control detail", "Evidence strength", "Governance fit"],
        "likelyObjections": ["Risk and compliance mitigations are too vague."],
        "whatWinsThemOver": ["Explicit controls", "Documented safeguards", "Clear caveats"],
        "skepticismLevel": 8,
        "domainExpertise": "risk",
        "politicalMotivations": ["Avoid signing off on unclear exposure"],
    },
    {
        "roleInDecision": "business_sponsor",
        "authorityWeight": 0.20,
        "priorities": ["Stakeholder buy-in", "Customer impact", "Execution confidence"],
        "concerns": ["Operational disruption", "Unclear ownership", "Weak narrative"],
        "decisionCriteria": ["Business relevance", "Stakeholder resonance", "Execution plan"],
        "likelyObjections": ["The story does not connect clearly to the business problem."],
        "whatWinsThemOver": ["Strong business framing", "Role-specific proof points"],
        "skepticismLevel": 5,
        "domainExpertise": "operations",
        "politicalMotivations": ["Champion a safe, credible win"],
    },
    {
        "roleInDecision": "financial_reviewer",
        "authorityWeight": 0.16,
        "priorities": ["Budget alignment", "Defensible assumptions", "Procurement readiness"],
        "concerns": ["Soft savings claims", "Missing baseline", "Procurement friction"],
        "decisionCriteria": ["Cost clarity", "Procurement path", "Payback confidence"],
        "likelyObjections": ["The economic case needs firmer assumptions."],
        "whatWinsThemOver": ["Baseline numbers", "Payback framing", "Procurement path clarity"],
        "skepticismLevel": 7,
        "domainExpertise": "finance",
        "politicalMotivations": ["Avoid surprise spend and approval churn"],
    },
]


@dataclass
class CommitteePersonaBuild:
    personas: List[CommitteePersona]
    profile: IndustryProfile
    warnings: List[str] = field(default_factory=list)


async def build_committee_personas(
    document: CommitteeDocument,
    committee_description: Optional[str] = None,
    provided_personas: Optional[List[CommitteePersona]] = None,
    use_seed_personas: bool = True,
    llm_service=None,
) -> CommitteePersonaBuild:
    profile = detect_industry_profile(
        [document.documentName, document.rawText] + [section.title for section in document.sections[:8]]
    )

    if provided_personas:
        return CommitteePersonaBuild(personas=provided_personas, profile=profile)

    if llm_service and llm_service.available:
        prompt = committee_description or _summarize_document(document)
        generated = await llm_service.generate_committee_personas(prompt)
        personas = _coerce_generated_personas(generated)
        if personas:
            return CommitteePersonaBuild(personas=personas, profile=profile)

    return CommitteePersonaBuild(personas=_build_seed_personas(profile), profile=profile)


def _build_seed_personas(profile: IndustryProfile) -> List[CommitteePersona]:
    roles = list(profile.default_roles)[: len(_SEED_PERSONA_DETAILS)]
    personas: List[CommitteePersona] = []
    for index, role in enumerate(roles):
        seed = _SEED_PERSONA_DETAILS[index]
        personas.append(
            CommitteePersona(
                id=f"committee_{index + 1}",
                name=role.split("/")[0].strip(),
                title=role,
                organization="Prospective Buyer",
                roleInDecision=seed["roleInDecision"],
                authorityWeight=seed["authorityWeight"],
                priorities=list(seed["priorities"]),
                concerns=list(seed["concerns"]),
                decisionCriteria=list(seed["decisionCriteria"]),
                likelyObjections=list(seed["likelyObjections"]),
                whatWinsThemOver=list(seed["whatWinsThemOver"]),
                skepticismLevel=seed["skepticismLevel"],
                domainExpertise=seed["domainExpertise"],
                politicalMotivations=list(seed["politicalMotivations"]),
            )
        )
    return personas


def _coerce_generated_personas(generated: list) -> List[CommitteePersona]:
    personas: List[CommitteePersona] = []
    for index, item in enumerate(generated):
        if not isinstance(item, dict):
            continue
        try:
            persona = CommitteePersona(
                id=str(item.get("id") or f"committee_{index + 1}_{uuid.uuid4().hex[:6]}"),
                name=str(item.get("name", f"Persona {index + 1}")),
                title=str(item.get("title", "Stakeholder")),
                organization=str(item.get("organization", "Prospective Buyer")),
                roleInDecision=str(item.get("roleInDecision", "reviewer")),
                authorityWeight=float(item.get("authorityWeight", 0.2)),
                priorities=[str(value) for value in item.get("priorities", [])],
                concerns=[str(value) for value in item.get("concerns", [])],
                decisionCriteria=[str(value) for value in item.get("decisionCriteria", [])],
                likelyObjections=[str(value) for value in item.get("likelyObjections", [])],
                whatWinsThemOver=[str(value) for value in item.get("whatWinsThemOver", [])],
                skepticismLevel=int(item.get("skepticismLevel", 5)),
                domainExpertise=item.get("domainExpertise"),
                politicalMotivations=[str(value) for value in item.get("politicalMotivations", [])],
            )
        except Exception:
            continue
        personas.append(persona)
    return personas


def _summarize_document(document: CommitteeDocument) -> str:
    sections = "\n".join(
        f"- {section.title}: {section.content[:180]}"
        for section in document.sections[:6]
    )
    return f"Document: {document.documentName}\n{sections}"
