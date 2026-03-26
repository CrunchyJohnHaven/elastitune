import json
import random
from pathlib import Path
from typing import List, Optional, Dict, Any
from ..models.contracts import PersonaDefinition, PersonaViewModel, ConnectionSummary

# Archetype libraries by domain
ARCHETYPES = {
    "security": [
        ("Maya Chen", "Senior SOC Analyst", "Security Operations", "SOC Analyst",
         "Investigate alerts and identify true positives quickly",
         ["lateral movement smb east west", "failed auth admin account", "powershell execution suspicious", "alert rule triggered last hour"]),
        ("Jordan Price", "Threat Hunter", "Threat Intelligence", "Threat Hunter",
         "Proactively search for advanced persistent threats",
         ["c2 beacon dns exfil", "credential access lsass", "persistence registry run keys", "unusual outbound port 443 traffic"]),
        ("Priya Raman", "IAM Administrator", "Identity & Access", "IAM Administrator",
         "Manage identity policies and investigate access anomalies",
         ["privileged account creation", "service account lateral", "mfa bypass attempt", "stale admin credentials"]),
        ("Elena Ortiz", "Detection Engineer", "Security Engineering", "Detection Engineer",
         "Build and tune detection rules for maximum fidelity",
         ["rule false positive ratio", "detection coverage mitre t1059", "sigma rule edr deployment", "low signal high noise alerts"]),
        ("Marcus Lee", "Compliance Auditor", "Compliance", "Compliance Auditor",
         "Audit security controls and generate evidence for audits",
         ["access log evidence soc2", "policy exception approval workflow", "encryption at rest compliance", "data retention violation"]),
        ("Samir Patel", "Incident Commander", "CISO Office", "Incident Commander",
         "Coordinate and manage active security incidents end to end",
         ["incident timeline reconstruction", "blast radius assessment", "stakeholder update template", "containment action log"]),
        ("Hannah Brooks", "AppSec Engineer", "Application Security", "AppSec Engineer",
         "Identify and remediate application vulnerabilities",
         ["sql injection application layer", "xss vulnerability web app", "insecure deserialization java", "api authentication bypass"]),
        ("Diego Silva", "SRE", "Infrastructure", "SRE",
         "Maintain reliability and investigate infrastructure-level alerts",
         ["cpu spike k8s node", "memory leak container crash", "disk io high latency", "network timeout pod restart"]),
        ("Nora Kim", "Vulnerability Analyst", "Vulnerability Management", "Vulnerability Analyst",
         "Track and prioritize vulnerability remediation",
         ["critical cve unpatched servers", "cvss 9 exploitable remote", "patch tuesday windows server", "vulnerability scanner coverage gap"]),
        ("Tessa Moore", "Helpdesk Lead", "IT Support", "Helpdesk Lead",
         "Triage user-reported security issues and escalate appropriately",
         ["user account locked out", "phishing email report employee", "vpn connection failure", "device compliance failure"]),
        ("Alex Rivers", "Red Team Lead", "Offensive Security", "Threat Hunter",
         "Simulate adversary techniques and validate defenses",
         ["kerberoasting golden ticket", "dcsync active directory", "living off land binaries", "pass the hash ntlm"]),
        ("Sam Torres", "Cloud Security Engineer", "Cloud Security", "SOC Analyst",
         "Monitor and secure cloud infrastructure environments",
         ["s3 bucket public exposure", "iam role overpermission", "cloudtrail log gaps", "ec2 security group wide open"]),
    ],
    "developer_docs": [
        ("Alex Kim", "Backend Engineer", "Engineering", "Backend Engineer",
         "Find API documentation and implementation patterns",
         ["rest api authentication oauth2", "database connection pool config", "async handler error retry", "pagination cursor based"]),
        ("Sam Rivera", "Frontend Engineer", "Engineering", "Frontend Engineer",
         "Look up component docs and UI framework patterns",
         ["react hook useState example", "css grid responsive layout", "form validation library", "bundle size optimization"]),
        ("Jordan Lee", "SRE", "Platform", "SRE",
         "Find runbooks and infrastructure documentation",
         ["kubernetes deployment rollback", "prometheus alert rule", "log aggregation fluentd", "circuit breaker pattern"]),
        ("Casey Nguyen", "Developer Advocate", "Developer Relations", "Developer Advocate",
         "Research developer experience improvements",
         ["getting started quickstart guide", "sdk installation npm", "example project tutorial", "common error troubleshooting"]),
        ("Morgan Davis", "Product Manager", "Product", "Product Manager",
         "Understand feature capabilities and roadmap context",
         ["feature flag rollout strategy", "api versioning deprecation", "user analytics instrumentation", "a/b test implementation"]),
        ("Riley Chen", "Support Engineer", "Customer Support", "Support Engineer",
         "Answer customer technical questions accurately",
         ["rate limit exceeded 429 error", "webhook signature validation", "idempotency key implementation", "data export csv endpoint"]),
        ("Quinn Williams", "QA Lead", "Quality Assurance", "QA Lead",
         "Find test patterns and quality documentation",
         ["integration test setup teardown", "mock external dependency", "load test k6 script", "regression test coverage"]),
        ("Blake Thompson", "Platform Engineer", "Infrastructure", "Platform Engineer",
         "Build internal tooling on top of platform APIs",
         ["service mesh configuration", "ci cd pipeline template", "secret management vault", "observability tracing opentelemetry"]),
    ],
    "compliance": [
        ("Morgan Chen", "Compliance Manager", "Legal & Compliance", "Compliance Manager",
         "Manage compliance programs and regulatory requirements",
         ["gdpr data subject request", "soc2 control evidence collection", "policy update review cycle", "vendor risk assessment template"]),
        ("Taylor Brown", "Privacy Counsel", "Legal", "Privacy Counsel",
         "Advise on data privacy and regulatory obligations",
         ["data retention schedule policy", "consent management platform", "privacy impact assessment template", "cross border transfer mechanism"]),
        ("Jamie Wilson", "Internal Auditor", "Audit", "Internal Auditor",
         "Conduct internal audits and assess control effectiveness",
         ["control testing evidence", "audit finding remediation plan", "risk rating methodology", "audit trail completeness check"]),
        ("Drew Martinez", "Risk Analyst", "Risk Management", "Risk Analyst",
         "Identify and quantify operational and compliance risks",
         ["risk register update q4", "inherent residual risk rating", "control gap analysis", "risk appetite threshold breach"]),
        ("Chris Rodriguez", "Policy Manager", "Governance", "Policy Manager",
         "Maintain and distribute organizational policies",
         ["acceptable use policy update", "policy exception request process", "policy acknowledgment tracking", "version control policy document"]),
        ("Pat Anderson", "Security Compliance Lead", "Security", "Security Compliance Lead",
         "Bridge security operations and compliance requirements",
         ["nist csf control mapping", "pentest finding compliance", "security awareness training completion", "vulnerability scan compliance report"]),
    ],
    "general": [
        ("Alex Chen", "Analyst", "Operations", "Analyst",
         "Research and analyze data to support decisions",
         ["monthly report summary", "trend analysis Q3", "data quality issue", "KPI dashboard update"]),
        ("Sam Williams", "Researcher", "Research", "Researcher",
         "Deep-dive into topics and synthesize information",
         ["background research topic overview", "literature review methodology", "data source comparison", "research gap analysis"]),
        ("Jordan Smith", "Team Lead", "Management", "Team Lead",
         "Coordinate team work and escalate blockers",
         ["team standup notes", "project status update", "blocker escalation process", "sprint retrospective actions"]),
        ("Casey Jones", "Support Specialist", "Customer Success", "Support Specialist",
         "Help customers find answers quickly",
         ["customer error message fix", "how to configure integration", "billing question FAQ", "account settings help"]),
        ("Morgan Brown", "Operations Manager", "Operations", "Operations Manager",
         "Oversee operations and drive efficiency",
         ["process improvement checklist", "vendor contract renewal", "operational metric review", "SLA compliance report"]),
        ("Riley Davis", "New Hire", "General", "New Hire",
         "Onboard quickly and find orientation resources",
         ["getting started onboarding", "company policy handbook", "tool access request", "first day checklist"]),
        ("Quinn Miller", "Power User", "Advanced Users", "Power User",
         "Push the boundaries of what the system can do",
         ["advanced filter complex query", "bulk export all records", "api integration setup", "custom report template"]),
        ("Drew Wilson", "Auditor", "Compliance", "Auditor",
         "Review records and verify process compliance",
         ["audit log complete records", "change history review", "access log compliance", "evidence export for review"]),
    ],
}


class PersonaGenerator:
    def __init__(self, llm_service=None):
        self.llm = llm_service

    async def generate(self, summary: ConnectionSummary, count: int = 24) -> List[PersonaViewModel]:
        domain = summary.detectedDomain
        archetypes = ARCHETYPES.get(domain, ARCHETYPES["general"])

        # If LLM available and we want more variety, could use LLM
        # For now, use archetype library with cycling
        personas = []
        rng = random.Random(42)  # Deterministic for consistency

        for i in range(count):
            template = archetypes[i % len(archetypes)]
            name, role, dept, archetype, goal, queries = template

            # Add some variety in names for duplicates
            if i >= len(archetypes):
                suffix = rng.choice(["Jr.", "II", "Sr.", ""])
                name_parts = name.split()
                name = f"{name_parts[0]} {rng.choice(['M.', 'J.', 'A.', 'R.', 'K.'])} {name_parts[-1]} {suffix}".strip()

            orbit = i % 6  # 6 orbit lanes

            p = PersonaViewModel(
                id=f"persona_{i:03d}",
                name=name,
                role=role,
                department=dept,
                archetype=archetype,
                goal=goal,
                orbit=orbit,
                colorSeed=i * 37 + 13,
                queries=queries,
                # Runtime defaults
                state='idle',
                successRate=0.0,
                totalSearches=0,
                successes=0,
                partials=0,
                failures=0,
                angle=rng.uniform(0, 6.283),
                speed=rng.uniform(0.06, 0.14),
                radius=120.0 + orbit * 52.0,
            )
            personas.append(p)

        return personas
