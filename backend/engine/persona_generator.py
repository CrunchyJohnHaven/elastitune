from __future__ import annotations

import math
import random
import re
from typing import Any, Dict, List, Optional

from ..models.contracts import ConnectionSummary, PersonaViewModel
from ..services.llm_service import LLMService

PERSONA_TEMPLATES: List[tuple[str, str, str, str, str, List[str]]] = [
    (
        "Alex",
        "SOC Analyst",
        "Security",
        "Power User",
        "Detect active threats",
        ["critical cve", "active exploitation", "threat intel"],
    ),
    (
        "Sam",
        "Threat Hunter",
        "Security",
        "Expert",
        "Hunt advanced threats",
        ["lateral movement", "persistence mechanism", "c2 beacon"],
    ),
    (
        "Jordan",
        "CISO",
        "Executive",
        "Casual",
        "Understand risk posture",
        ["top risks", "compliance gap", "board report"],
    ),
    (
        "Taylor",
        "DevSecOps Engineer",
        "Engineering",
        "Power User",
        "Secure CI/CD pipeline",
        ["supply chain vulnerability", "container cve", "sast findings"],
    ),
    (
        "Morgan",
        "Incident Responder",
        "Security",
        "Expert",
        "Triage active incidents",
        ["ioc hash", "ransomware playbook", "evidence collection"],
    ),
    (
        "Casey",
        "Vulnerability Manager",
        "IT",
        "Expert",
        "Prioritise patching",
        ["cvss 9", "patch priority", "asset exposure"],
    ),
    (
        "Riley",
        "Compliance Officer",
        "Legal",
        "Casual",
        "Map controls to regulations",
        ["gdpr control", "hipaa requirement", "audit evidence"],
    ),
    (
        "Drew",
        "Penetration Tester",
        "Security",
        "Expert",
        "Research exploitation paths",
        ["exploit poc", "privilege escalation", "bypass technique"],
    ),
    (
        "Avery",
        "Security Architect",
        "Engineering",
        "Power User",
        "Design secure systems",
        ["zero trust pattern", "cloud misconfiguration", "network segmentation"],
    ),
    (
        "Blake",
        "Cloud Engineer",
        "DevOps",
        "Casual",
        "Harden cloud infrastructure",
        ["aws advisory", "azure cve", "kubernetes security"],
    ),
    (
        "Charlie",
        "Privacy Analyst",
        "Legal",
        "Casual",
        "Assess data exposure risks",
        ["pii leak", "data breach notification", "dpo guidance"],
    ),
    (
        "Dana",
        "Red Team Lead",
        "Security",
        "Expert",
        "Simulate adversary TTPs",
        ["credential dumping", "kerberoasting", "living off the land"],
    ),
    (
        "Evan",
        "Blue Team Analyst",
        "Security",
        "Power User",
        "Detect and respond",
        ["detection rule", "sigma rule", "yara signature"],
    ),
    (
        "Fran",
        "IT Operations Manager",
        "IT",
        "Casual",
        "Minimize service disruption",
        ["availability impact", "service outage cve", "emergency patch"],
    ),
    (
        "Glen",
        "Application Developer",
        "Engineering",
        "Casual",
        "Audit open source dependencies",
        ["npm vulnerability", "log4j", "dependency confusion"],
    ),
    (
        "Hana",
        "Internal Auditor",
        "Compliance",
        "Power User",
        "Gather audit evidence",
        ["control failure", "remediation status", "risk acceptance"],
    ),
    (
        "Ivan",
        "Network Engineer",
        "IT",
        "Expert",
        "Secure network infrastructure",
        ["cisco advisory", "fortinet vulnerability", "bgp hijack"],
    ),
    (
        "Jess",
        "Malware Analyst",
        "Security",
        "Expert",
        "Reverse engineer threats",
        ["dropper behaviour", "c2 protocol", "sandbox evasion"],
    ),
    (
        "Kim",
        "Product Security Manager",
        "Engineering",
        "Power User",
        "Manage product risk",
        ["third party risk", "sbom vulnerability", "responsible disclosure"],
    ),
    (
        "Lee",
        "Security Awareness Trainer",
        "HR",
        "Casual",
        "Create training content",
        ["phishing simulation", "social engineering cve", "security culture"],
    ),
    (
        "Mel",
        "CTO",
        "Executive",
        "Casual",
        "Strategic technology risk",
        ["critical infrastructure", "nation state threat", "technology dependency"],
    ),
    (
        "Nora",
        "Digital Forensics Analyst",
        "Security",
        "Expert",
        "Investigate breaches",
        ["forensic artifact", "timeline analysis", "disk image"],
    ),
    (
        "Omar",
        "Bug Bounty Researcher",
        "External",
        "Expert",
        "Find and report vulnerabilities",
        ["memory corruption", "use after free", "heap overflow"],
    ),
    (
        "Pat",
        "Security Product Manager",
        "Product",
        "Casual",
        "Plan security roadmap",
        ["security debt", "feature request", "risk register"],
    ),
]

GENERAL_PERSONA_SEEDS: List[Dict[str, Any]] = [
    {
        "name": "Jamie",
        "role": "Researcher",
        "department": "Knowledge",
        "archetype": "Power User",
        "goal": "Find the most relevant source fast",
        "queries": [
            "getting started guide",
            "best practice",
            "troubleshooting workflow",
        ],
    },
    {
        "name": "Taylor",
        "role": "Program Manager",
        "department": "Operations",
        "archetype": "Casual",
        "goal": "Answer stakeholder questions with confidence",
        "queries": ["policy summary", "latest update", "process overview"],
    },
    {
        "name": "Morgan",
        "role": "Analyst",
        "department": "Strategy",
        "archetype": "Expert",
        "goal": "Compare detailed records across the corpus",
        "queries": ["deep dive analysis", "root cause", "detailed reference"],
    },
]

ECOMMERCE_PERSONA_SEEDS: List[Dict[str, Any]] = [
    {
        "name": "Ava",
        "role": "Online Shopper",
        "department": "Customer",
        "archetype": "Casual",
        "goal": "Find the exact product quickly",
        "queries": ["lip pencil", "serum foundation", "waterproof mascara"],
    },
    {
        "name": "Noah",
        "role": "Category Merchandiser",
        "department": "E-commerce",
        "archetype": "Power User",
        "goal": "Check whether high-intent products surface correctly",
        "queries": ["best selling foundation", "long wear concealer", "gift set"],
    },
    {
        "name": "Mia",
        "role": "Customer Support Lead",
        "department": "Support",
        "archetype": "Power User",
        "goal": "Resolve product questions from customer language",
        "queries": [
            "sensitive skin foundation",
            "matte lip color",
            "shade matching help",
        ],
    },
]

STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "from",
    "how",
    "in",
    "into",
    "of",
    "on",
    "the",
    "to",
    "with",
}


async def build_personas(
    persona_count: int = 36,
    mode: str = "demo",
    domain: str = "general",
    sample_docs: Optional[List[Dict[str, Any]]] = None,
    text_fields: Optional[List[str]] = None,
    llm_config: Optional[Any] = None,
) -> List[PersonaViewModel]:
    sample_docs = sample_docs or []
    text_fields = text_fields or []
    templates = await resolve_persona_templates(
        persona_count=persona_count,
        mode=mode,
        domain=domain,
        sample_docs=sample_docs,
        text_fields=text_fields,
        llm_config=llm_config,
    )

    personas: List[PersonaViewModel] = []
    rng = random.Random(2024)
    template_count = max(1, len(templates))

    for i, template in enumerate(templates[:persona_count]):
        name, role, department, archetype, goal, queries = template
        cycle = i // template_count
        display_name = name if cycle == 0 else f"{name} {cycle + 1}"
        orbit = (i % 5) + 1
        personas.append(
            PersonaViewModel(
                id=f"persona_{i:03d}",
                name=display_name,
                role=role,
                department=department,
                archetype=archetype,
                goal=goal,
                orbit=orbit,
                colorSeed=rng.randint(0, 255),
                queries=queries,
                state="idle",
                lastQuery=None,
                lastResultRank=None,
                successRate=0.0,
                totalSearches=0,
                successes=0,
                partials=0,
                failures=0,
                angle=(i * 2 * math.pi) / max(persona_count, 1),
                speed=0.05 + rng.random() * 0.05,
                radius=72.0 + orbit * 38.0,
                pulseUntil=None,
                reactUntil=None,
            )
        )
    return personas


async def resolve_persona_templates(
    persona_count: int,
    mode: str,
    domain: str,
    sample_docs: List[Dict[str, Any]],
    text_fields: List[str],
    llm_config: Optional[Any],
) -> List[tuple[str, str, str, str, str, List[str]]]:
    if mode == "demo":
        return cycle_templates(PERSONA_TEMPLATES, persona_count)

    llm_templates = await generate_personas_with_llm(
        persona_count=persona_count,
        domain=domain,
        sample_docs=sample_docs,
        text_fields=text_fields,
        llm_config=llm_config,
    )
    if llm_templates:
        return llm_templates

    if looks_like_product_catalog(sample_docs, text_fields):
        return cycle_templates(
            seed_dicts_to_templates(ECOMMERCE_PERSONA_SEEDS), persona_count
        )

    if domain == "general":
        generated = generate_general_persona_templates(
            sample_docs, text_fields, persona_count
        )
        if generated:
            return generated

    return cycle_templates(PERSONA_TEMPLATES, persona_count)


async def generate_personas_with_llm(
    persona_count: int,
    domain: str,
    sample_docs: List[Dict[str, Any]],
    text_fields: List[str],
    llm_config: Optional[Any],
) -> List[tuple[str, str, str, str, str, List[str]]]:
    if not llm_config or llm_config.provider == "disabled":
        return []

    generated = await LLMService(llm_config).generate_personas(
        domain=domain,
        sample_docs=sample_docs,
        text_fields=text_fields,
        count=min(persona_count, 12),
    )
    templates: List[tuple[str, str, str, str, str, List[str]]] = []
    for item in generated:
        if not isinstance(item, dict):
            continue
        queries = item.get("queries") or []
        if not isinstance(queries, list) or not queries:
            continue
        templates.append(
            (
                str(item.get("name", "Search User")),
                str(item.get("role", "User")),
                str(item.get("department", "Search")),
                str(item.get("archetype", "Casual")),
                str(item.get("goal", "Find relevant results")),
                [str(query) for query in queries[:4]],
            )
        )

    return cycle_templates(templates, persona_count) if templates else []


def generate_general_persona_templates(
    sample_docs: List[Dict[str, Any]],
    text_fields: List[str],
    persona_count: int,
) -> List[tuple[str, str, str, str, str, List[str]]]:
    seeds = list(GENERAL_PERSONA_SEEDS)
    query_bank: List[str] = []
    for doc in sample_docs[:18]:
        for field in text_fields[:3]:
            value = doc.get(field)
            if not isinstance(value, str):
                continue
            query = derive_query(value)
            if query and query not in query_bank:
                query_bank.append(query)
        if len(query_bank) >= persona_count * 2:
            break

    if not query_bank:
        return cycle_templates(seed_dicts_to_templates(seeds), persona_count)

    templates: List[tuple[str, str, str, str, str, List[str]]] = []
    for index in range(persona_count):
        seed = seeds[index % len(seeds)]
        start = (index * 2) % len(query_bank)
        queries = [
            query_bank[start],
            query_bank[(start + 1) % len(query_bank)],
            query_bank[(start + 2) % len(query_bank)],
        ]
        templates.append(
            (
                f"{seed['name']} {index + 1}" if index >= len(seeds) else seed["name"],
                seed["role"],
                seed["department"],
                seed["archetype"],
                seed["goal"],
                queries,
            )
        )
    return templates


def seed_dicts_to_templates(
    seed_dicts: List[Dict[str, Any]],
) -> List[tuple[str, str, str, str, str, List[str]]]:
    return [
        (
            str(seed["name"]),
            str(seed["role"]),
            str(seed["department"]),
            str(seed["archetype"]),
            str(seed["goal"]),
            [str(query) for query in seed["queries"]],
        )
        for seed in seed_dicts
    ]


def cycle_templates(
    templates: List[tuple[str, str, str, str, str, List[str]]],
    persona_count: int,
) -> List[tuple[str, str, str, str, str, List[str]]]:
    if not templates:
        templates = PERSONA_TEMPLATES

    cycled = list(templates[:persona_count])
    while len(cycled) < persona_count:
        cycled.extend(templates[: persona_count - len(cycled)])
    return cycled


def looks_like_product_catalog(
    sample_docs: List[Dict[str, Any]], text_fields: List[str]
) -> bool:
    keywords = {
        "foundation",
        "lip",
        "mascara",
        "concealer",
        "price",
        "sku",
        "brand",
        "product",
        "collection",
        "category",
        "shade",
        "size",
    }
    text_blob = " ".join(
        str(doc.get(field, "")).lower()
        for doc in sample_docs[:20]
        for field in text_fields[:3]
        if isinstance(doc.get(field), str)
    )
    return sum(1 for keyword in keywords if keyword in text_blob) >= 2


def derive_query(value: str) -> str:
    tokens = [
        token
        for token in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9._-]*", value.lower())
        if len(token) >= 3 and token not in STOPWORDS
    ]
    return " ".join(tokens[:5])


class PersonaGenerator:
    def __init__(self, llm_service: Optional[LLMService] = None) -> None:
        self.llm = llm_service

    async def generate(
        self,
        summary: ConnectionSummary,
        count: int = 24,
        sample_docs: Optional[List[Dict[str, Any]]] = None,
        text_fields: Optional[List[str]] = None,
        llm_config: Optional[Any] = None,
        mode: str = "live",
    ) -> List[PersonaViewModel]:
        return await build_personas(
            persona_count=count,
            mode=mode,
            domain=summary.detectedDomain,
            sample_docs=sample_docs or [],
            text_fields=text_fields or list(summary.primaryTextFields),
            llm_config=llm_config,
        )


__all__ = [
    "PERSONA_TEMPLATES",
    "PersonaGenerator",
    "build_personas",
    "resolve_persona_templates",
    "generate_personas_with_llm",
    "generate_general_persona_templates",
    "looks_like_product_catalog",
]
