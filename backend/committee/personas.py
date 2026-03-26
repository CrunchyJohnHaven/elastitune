from __future__ import annotations

from dataclasses import dataclass, field
import logging
import uuid
from typing import List, Optional

from .industry_profiles import IndustryProfile, detect_industry_profile, get_industry_profile
from .models import CommitteeDocument, CommitteePersona

logger = logging.getLogger(__name__)


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

_SBA_PERSONAS = [
    CommitteePersona(
        id="committee_sba_cio",
        name="Hartley Caldwell",
        title="Chief Information Officer, SBA",
        organization="Small Business Administration",
        roleInDecision="Final technical authority",
        authorityWeight=0.25,
        priorities=[
            "Cybersecurity and data sovereignty",
            "FedRAMP compliance",
            "Integration with existing SBA systems",
            "Cost justification for OMB",
        ],
        concerns=[
            "Another AI vendor overpromising",
            "Maintenance burden on thin IT staff",
            "Data leaving SBA control",
            "Audit exposure if the system fails",
        ],
        decisionCriteria=[
            "Proven federal deployments",
            "Air-gap capability",
            "FedRAMP Moderate readiness",
            "Five-year total cost of ownership",
        ],
        likelyObjections=[
            "How does this integrate with our current document management?",
            "What is the maintenance burden?",
            "Show me the FedRAMP package.",
        ],
        whatWinsThemOver=[
            "Search.gov scale proof",
            "CISA deployment proof",
            "Carahsoft procurement path",
        ],
        skepticismLevel=7,
        domainExpertise="technology",
        politicalMotivations=["Protect security posture without adding operational burden"],
    ),
    CommitteePersona(
        id="committee_sba_gc",
        name="General Counsel",
        title="General Counsel, SBA",
        organization="Small Business Administration",
        roleInDecision="Domain owner and internal champion",
        authorityWeight=0.30,
        priorities=[
            "Reducing litigation risk from inconsistent opinions",
            "Attorney adoption",
            "Institutional knowledge retention",
            "Defensibility of AI-assisted opinions",
        ],
        concerns=[
            "AI making legal determinations",
            "Liability if the system surfaces the wrong precedent",
            "Attorney resistance to new tools",
            "Political optics of AI replacing lawyers",
        ],
        decisionCriteria=[
            "Citation trail transparency",
            "Human in the loop",
            "High attorney adoption",
            "OIG audit alignment",
        ],
        likelyObjections=[
            "Attorneys will not trust AI for legal research.",
            "What happens when it is wrong?",
        ],
        whatWinsThemOver=[
            "Full citation trails",
            "Explainability",
            "Search framing instead of AI lawyer framing",
        ],
        skepticismLevel=8,
        domainExpertise="legal",
        politicalMotivations=["Protect professional trust and defensibility"],
    ),
    CommitteePersona(
        id="committee_sba_budget",
        name="Budget Director",
        title="Chief Financial Officer / Budget Director, SBA",
        organization="Small Business Administration",
        roleInDecision="Economic approver",
        authorityWeight=0.25,
        priorities=[
            "Quantified ROI with defensible math",
            "Fit within existing budget lines",
            "No surprise implementation costs",
            "OMB justification narrative",
        ],
        concerns=[
            "Inflated vendor ROI projections",
            "Hidden implementation costs",
            "Multi-year commitment with unclear exit",
            "Hiring alternatives may be cheaper",
        ],
        decisionCriteria=[
            "Payback under 18 months",
            "Five-year TCO",
            "Comparison to hiring alternative",
            "Existing procurement vehicle",
        ],
        likelyObjections=[
            "The ROI math feels stretched.",
            "What is the actual license cost?",
        ],
        whatWinsThemOver=[
            "Hard math with defensible baselines",
            "Carahsoft pricing path",
            "Comparison to labor alternatives",
        ],
        skepticismLevel=9,
        domainExpertise="finance",
        politicalMotivations=["Avoid defendable spend without solid proof"],
    ),
    CommitteePersona(
        id="committee_sba_field",
        name="District Office Attorney",
        title="Senior Attorney, SBA District Office",
        organization="Small Business Administration",
        roleInDecision="End user and adoption signal",
        authorityWeight=0.10,
        priorities=[
            "Save time on daily work",
            "Find relevant precedents faster",
            "Avoid extra bureaucracy",
            "Work reliably on existing hardware",
        ],
        concerns=[
            "Another IT system that breaks",
            "Replacing professional judgment with algorithms",
            "Training time versus value",
        ],
        decisionCriteria=[
            "Minutes instead of hours to find precedent",
            "Natural language queries",
            "Minimal training",
        ],
        likelyObjections=[
            "My current method works fine.",
            "I do not want AI telling me what the law says.",
        ],
        whatWinsThemOver=[
            "Live search demo",
            "Search-not-lawyer framing",
            "Hours-to-minutes proof",
        ],
        skepticismLevel=6,
        domainExpertise="field legal operations",
        politicalMotivations=["Protect autonomy and avoid friction"],
    ),
    CommitteePersona(
        id="committee_sba_oig",
        name="OIG Auditor",
        title="Assistant Inspector General for Auditing, SBA OIG",
        organization="Small Business Administration",
        roleInDecision="Shadow stress-test persona",
        authorityWeight=0.10,
        priorities=[
            "Accuracy of OIG finding representation",
            "Root-cause alignment",
            "Auditability of the system itself",
        ],
        concerns=[
            "Vendor cherry-picking OIG data",
            "Correlation presented as causation",
            "Technology over-claiming against process recommendations",
        ],
        decisionCriteria=[
            "Faithful representation of audit findings",
            "Clear mapping from finding to capability",
            "System output auditability",
        ],
        likelyObjections=[
            "The audit language is overstated.",
            "This recommendation was about controls, not a product.",
        ],
        whatWinsThemOver=[
            "Tighter caveats",
            "Careful mapping from findings to controls",
        ],
        skepticismLevel=10,
        domainExpertise="audit",
        politicalMotivations=["Prevent overclaiming against official findings"],
    ),
]


@dataclass
class CommitteePersonaBuild:
    personas: List[CommitteePersona]
    profile: IndustryProfile
    warnings: List[str] = field(default_factory=list)


def seeded_sba_personas() -> List[CommitteePersona]:
    return [persona.model_copy(deep=True) for persona in _SBA_PERSONAS]


async def build_committee_personas(
    document: CommitteeDocument,
    committee_description: Optional[str] = None,
    provided_personas: Optional[List[CommitteePersona]] = None,
    use_seed_personas: bool = True,
    llm_service=None,
    industry_profile_id: Optional[str] = None,
) -> CommitteePersonaBuild:
    warnings: List[str] = []
    profile = (
        get_industry_profile(industry_profile_id)
        if industry_profile_id
        else detect_industry_profile(
            [document.documentName, document.rawText] + [section.title for section in document.sections[:8]]
        )
    )

    if provided_personas:
        return CommitteePersonaBuild(
            personas=_normalize_weights(provided_personas, warnings),
            profile=profile,
            warnings=warnings,
        )

    if use_seed_personas:
        government_profile = get_industry_profile("government")
        return CommitteePersonaBuild(
            personas=seeded_sba_personas(),
            profile=government_profile,
            warnings=warnings,
        )

    if llm_service and llm_service.available:
        prompt = committee_description or _summarize_document(document, profile.label)
        generated = await llm_service.generate_committee_personas(prompt)
        personas = _normalize_weights(_coerce_generated_personas(generated), warnings)
        if personas:
            return CommitteePersonaBuild(personas=personas, profile=profile, warnings=warnings)
        warnings.append("AI persona generation returned no valid personas; profile-based committee defaults were used.")

    return CommitteePersonaBuild(
        personas=_normalize_weights(_build_seed_personas(profile), warnings),
        profile=profile,
        warnings=warnings,
    )


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


def _normalize_weights(personas: List[CommitteePersona], warnings: List[str]) -> List[CommitteePersona]:
    if not personas:
        return personas
    total = sum(max(persona.authorityWeight, 0.0) for persona in personas)
    if 0.99 <= total <= 1.01:
        return personas
    if total <= 0:
        even_weight = round(1 / len(personas), 4)
        warnings.append("Persona authority weights were invalid and were reset evenly.")
        logger.warning("Committee persona weights were non-positive; reset evenly.")
        return [
            persona.model_copy(update={"authorityWeight": even_weight})
            for persona in personas
        ]
    warnings.append("Persona authority weights were normalized to sum to 1.0.")
    logger.warning("Committee persona weights normalized from total=%s", total)
    return [
        persona.model_copy(update={"authorityWeight": round(max(persona.authorityWeight, 0.0) / total, 4)})
        for persona in personas
    ]


def _summarize_document(document: CommitteeDocument, profile_label: str) -> str:
    sections = "\n".join(
        f"- {section.title}: {section.content[:180]}"
        for section in document.sections[:6]
    )
    return f"Industry context: {profile_label}\nDocument: {document.documentName}\n{sections}"
