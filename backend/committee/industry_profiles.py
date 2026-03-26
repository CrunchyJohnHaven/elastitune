from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class IndustryRiskRule:
    flag_text: str
    absent_terms: tuple[str, ...] = ()
    present_terms: tuple[str, ...] = ()
    persona_keywords: tuple[str, ...] = ()


@dataclass(frozen=True)
class IndustryProfile:
    id: str
    label: str
    detection_terms: tuple[str, ...]
    social_proof_types: tuple[str, ...]
    specificity_values: tuple[str, ...]
    risk_rules: tuple[IndustryRiskRule, ...]
    default_roles: tuple[str, ...]

    @property
    def parameter_values(self) -> Dict[str, List[str]]:
        return {
            "stat_framing": ["conservative", "moderate", "aggressive"],
            "proof_point_density": ["low", "medium", "high"],
            "cta_urgency": ["soft", "firm", "direct"],
            "objection_preemption": ["none", "light", "heavy"],
            "technical_depth": ["executive", "practitioner", "mixed"],
            "risk_narrative": ["opportunity", "threat", "balanced"],
            "social_proof_type": list(self.social_proof_types),
            "specificity": list(self.specificity_values),
        }


INDUSTRY_PROFILES: Dict[str, IndustryProfile] = {
    "government": IndustryProfile(
        id="government",
        label="Government / Public Sector",
        detection_terms=(
            "fedramp",
            "carahsoft",
            "oig",
            "omb",
            "solicitation",
            "agency",
            "procurement",
            "general counsel",
            "district office",
            "search.gov",
            "cisa",
        ),
        social_proof_types=("internal", "external", "federal"),
        specificity_values=("general", "agency_tailored", "hyper_specific"),
        risk_rules=(
            IndustryRiskRule(
                flag_text="Compliance posture is underspecified.",
                absent_terms=("fedramp", "fisma", "state ramp", "cjis"),
                persona_keywords=("compliance", "cio", "security", "audit"),
            ),
            IndustryRiskRule(
                flag_text="Procurement path is unclear.",
                absent_terms=(
                    "carahsoft",
                    "naspo",
                    "procurement",
                    "vehicle",
                    "solicitation",
                ),
                persona_keywords=("budget", "procurement", "finance", "omb"),
            ),
            IndustryRiskRule(
                flag_text="Document needs tighter audit caveats.",
                absent_terms=("sample", "caveat", "finding", "audit"),
                present_terms=("oig", "inspector general", "recoverable"),
                persona_keywords=("audit", "oig", "legal"),
            ),
        ),
        default_roles=(
            "Chief Information Officer",
            "General Counsel",
            "Budget Director",
            "Program Owner",
            "Audit Stakeholder",
        ),
    ),
    "enterprise_tech": IndustryProfile(
        id="enterprise_tech",
        label="Enterprise Technology",
        detection_terms=(
            "observability",
            "elastic cloud",
            "platform engineering",
            "migration",
            "finops",
            "tco",
            "opex",
            "capex",
            "developer productivity",
            "sre",
            "self-managed",
        ),
        social_proof_types=("internal", "external", "peer_company", "analyst_report"),
        specificity_values=(
            "general",
            "role_tailored",
            "vertical_tailored",
            "hyper_specific",
        ),
        risk_rules=(
            IndustryRiskRule(
                flag_text="Integration and transition plan are underspecified.",
                absent_terms=(
                    "migration",
                    "phased",
                    "integration",
                    "cutover",
                    "transition",
                ),
                persona_keywords=("technology", "platform", "cto", "cio"),
            ),
            IndustryRiskRule(
                flag_text="Operational burden reduction is not concrete enough.",
                absent_terms=("patch", "certificate", "operations", "admin", "toil"),
                persona_keywords=("platform", "operations", "observability"),
            ),
            IndustryRiskRule(
                flag_text="Financial case needs tighter baseline and breakeven support.",
                absent_terms=("baseline", "tco", "payback", "breakeven", "savings"),
                persona_keywords=("finance", "budget", "finops", "cfo"),
            ),
            IndustryRiskRule(
                flag_text="Security and compliance responsibilities remain unclear.",
                absent_terms=(
                    "security",
                    "compliance",
                    "shared responsibility",
                    "audit",
                ),
                persona_keywords=("security", "risk", "compliance", "ciso"),
            ),
        ),
        default_roles=(
            "Chief Information Officer / CTO",
            "VP Platform Engineering / Head of Observability",
            "CFO / Finance Director / FinOps",
            "CISO / Security & Compliance Lead",
            "VP Operations / Product / Customer Experience",
        ),
    ),
    "financial_services": IndustryProfile(
        id="financial_services",
        label="Financial Services",
        detection_terms=(
            "bank",
            "trading",
            "aml",
            "fraud",
            "basel",
            "sox",
            "regulatory reporting",
            "portfolio",
            "wealth",
        ),
        social_proof_types=("internal", "external", "peer_company", "analyst_report"),
        specificity_values=(
            "general",
            "role_tailored",
            "vertical_tailored",
            "hyper_specific",
        ),
        risk_rules=(
            IndustryRiskRule(
                flag_text="Control framework and audit trail need stronger detail.",
                absent_terms=("audit trail", "control", "governance", "approval"),
                persona_keywords=("risk", "compliance", "audit", "legal"),
            ),
            IndustryRiskRule(
                flag_text="Business case does not address regulatory downside clearly enough.",
                absent_terms=("regulatory", "penalty", "risk", "exposure"),
                persona_keywords=("finance", "legal", "risk"),
            ),
        ),
        default_roles=(
            "Chief Information Officer",
            "Chief Risk Officer",
            "Chief Financial Officer",
            "Business Line Leader",
            "Compliance Counsel",
        ),
    ),
    "healthcare": IndustryProfile(
        id="healthcare",
        label="Healthcare",
        detection_terms=(
            "patient",
            "clinical",
            "hipaa",
            "ehr",
            "provider",
            "health system",
            "care team",
            "clinical operations",
        ),
        social_proof_types=("internal", "external", "peer_company", "analyst_report"),
        specificity_values=(
            "general",
            "role_tailored",
            "vertical_tailored",
            "hyper_specific",
        ),
        risk_rules=(
            IndustryRiskRule(
                flag_text="Clinical workflow impact is not concrete enough.",
                absent_terms=("workflow", "care team", "turnaround", "clinical"),
                persona_keywords=("operations", "clinical", "medical"),
            ),
            IndustryRiskRule(
                flag_text="Privacy and compliance safeguards need explicit treatment.",
                absent_terms=("hipaa", "privacy", "access control", "audit"),
                persona_keywords=("privacy", "compliance", "security", "legal"),
            ),
        ),
        default_roles=(
            "Chief Information Officer",
            "Clinical Operations Leader",
            "Chief Financial Officer",
            "Security / Privacy Officer",
            "Physician or Service Line Sponsor",
        ),
    ),
    "general_enterprise": IndustryProfile(
        id="general_enterprise",
        label="General Enterprise",
        detection_terms=(),
        social_proof_types=("internal", "external", "peer_company", "analyst_report"),
        specificity_values=(
            "general",
            "role_tailored",
            "vertical_tailored",
            "hyper_specific",
        ),
        risk_rules=(
            IndustryRiskRule(
                flag_text="Implementation path is too vague.",
                absent_terms=("timeline", "phase", "implementation", "rollout"),
                persona_keywords=("operations", "technology", "platform", "it"),
            ),
            IndustryRiskRule(
                flag_text="ROI narrative needs more concrete proof.",
                absent_terms=("roi", "payback", "savings", "tco"),
                persona_keywords=("finance", "budget", "cfo"),
            ),
            IndustryRiskRule(
                flag_text="Risk mitigation needs to be made more explicit.",
                absent_terms=("risk", "control", "governance", "security"),
                persona_keywords=("security", "legal", "risk", "compliance"),
            ),
        ),
        default_roles=(
            "Chief Information Officer",
            "Business Sponsor",
            "Finance Leader",
            "Operations Leader",
            "Security or Risk Leader",
        ),
    ),
}


def get_industry_profile(profile_id: str) -> IndustryProfile:
    return INDUSTRY_PROFILES.get(profile_id, INDUSTRY_PROFILES["general_enterprise"])


def detect_industry_profile(texts: Iterable[str]) -> IndustryProfile:
    corpus = " ".join(texts).lower()
    scored: list[tuple[int, str]] = []
    for profile_id, profile in INDUSTRY_PROFILES.items():
        score = sum(1 for token in profile.detection_terms if token in corpus)
        scored.append((score, profile_id))

    best_score, best_id = max(
        scored, key=lambda item: item[0], default=(0, "general_enterprise")
    )
    if best_score <= 0:
        return INDUSTRY_PROFILES["general_enterprise"]
    return INDUSTRY_PROFILES[best_id]
