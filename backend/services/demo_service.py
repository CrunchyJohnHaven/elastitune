from __future__ import annotations

import asyncio
import importlib.resources
import json
import logging
import math
import random
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..models.contracts import (
    CompressionSummary,
    ConnectionSummary,
    EvalCase,
    ExperimentRecord,
    HeroMetrics,
    LlmConfig,
    PersonaDefinition,
    PersonaRuntime,
    PersonaViewModel,
    SearchProfile,
)
from ..models.report import ReportPayload
from ..models.runtime import ConnectionContext, RunContext

logger = logging.getLogger(__name__)

# Path to the demo data directory
_DATA_DIR = Path(__file__).parent.parent / "data" / "demo"


def _format_demo_duration(duration_seconds: float) -> str:
    if duration_seconds < 60:
        return f"{max(1, round(duration_seconds))} seconds"
    minutes = duration_seconds / 60
    if minutes < 60:
        return f"{max(1, round(minutes))} minutes"
    hours = int(minutes // 60)
    rem_minutes = int(round(minutes % 60))
    if rem_minutes == 0:
        return f"{hours} hours"
    return f"{hours}h {rem_minutes}m"


def _load_demo_json(filename: str, default: Any = None) -> Any:
    """Load a JSON file from the demo data directory. Returns default if missing."""
    path = _DATA_DIR / filename
    if not path.exists():
        logger.warning("Demo data file not found: %s", path)
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        logger.error("Failed to load demo file %s: %s", filename, exc)
        return default


# ---------------------------------------------------------------------------
# Built-in fallback demo data (used when JSON files are absent)
# ---------------------------------------------------------------------------

_FALLBACK_CONNECTION: Dict[str, Any] = {
    "clusterName": "demo-cluster",
    "clusterVersion": "8.15.0",
    "indexName": "security-advisories",
    "docCount": 42381,
    "detectedDomain": "security",
    "primaryTextFields": ["title", "description", "cve_id", "affected_products"],
    "vectorField": "description_embedding",
    "vectorDims": 384,
    "sampleDocs": [
        {
            "id": "CVE-2024-0001",
            "title": "Critical RCE in OpenSSL 3.x",
            "excerpt": "A buffer overflow in OpenSSL's X.509 certificate verification allows remote code execution.",
            "fieldPreview": {
                "title": "Critical RCE in OpenSSL 3.x",
                "cve_id": "CVE-2024-0001",
                "severity": "CRITICAL",
            },
        },
        {
            "id": "CVE-2024-0042",
            "title": "SQL Injection in PostgreSQL",
            "excerpt": "Improper input sanitisation in PostgreSQL 16 allows privilege escalation via crafted queries.",
            "fieldPreview": {
                "title": "SQL Injection in PostgreSQL",
                "cve_id": "CVE-2024-0042",
                "severity": "HIGH",
            },
        },
    ],
    "baselineEvalCount": 24,
    "baselineReady": True,
}

_FALLBACK_PERSONAS: List[Dict[str, Any]] = [
    {
        "id": f"persona_{i:03d}",
        "name": name,
        "role": role,
        "department": dept,
        "archetype": arch,
        "goal": goal,
        "orbit": orbit,
        "colorSeed": colorSeed,
        "queries": queries,
        "state": "idle",
        "lastQuery": None,
        "lastResultRank": None,
        "successRate": 0.0,
        "totalSearches": 0,
        "successes": 0,
        "partials": 0,
        "failures": 0,
        "angle": (i * 2 * math.pi / 24),
        "speed": 0.06 + random.Random(i).random() * 0.04,
        "radius": 100.0 + (orbit * 30.0),
        "pulseUntil": None,
        "reactUntil": None,
    }
    for i, (name, role, dept, arch, goal, orbit, colorSeed, queries) in enumerate(
        [
            ("Alex", "SOC Analyst", "Security", "Power User", "Find active CVEs", 1, 42, ["openssl rce 2024", "critical vulnerabilities this month"]),
            ("Sam", "Threat Hunter", "Security", "Expert", "Hunt lateral movement", 1, 77, ["lateral movement detection", "mimikatz indicators"]),
            ("Jordan", "CISO", "Executive", "Casual", "Board-level risk summary", 2, 15, ["top critical risks", "compliance status"]),
            ("Taylor", "DevSecOps", "Engineering", "Power User", "Patch prioritisation", 1, 88, ["patch tuesday", "cvss 9+ 2024"]),
            ("Morgan", "Incident Responder", "Security", "Expert", "Rapid triage", 1, 23, ["ransomware ioc", "active exploitation"]),
            ("Casey", "Vulnerability Manager", "IT", "Expert", "Asset risk scoring", 2, 55, ["affected products nginx", "unpatched critical"]),
            ("Riley", "Compliance Officer", "Legal", "Casual", "Regulatory mapping", 3, 31, ["gdpr security controls", "soc2 vulnerabilities"]),
            ("Drew", "Pen Tester", "Security", "Expert", "Exploit research", 1, 66, ["exploit poc available", "metasploit modules"]),
            ("Avery", "Security Architect", "Engineering", "Power User", "Design guidance", 2, 12, ["zero trust architecture", "cloud misconfigurations"]),
            ("Blake", "Cloud Engineer", "DevOps", "Casual", "Cloud CVEs", 2, 99, ["aws security advisory", "kubernetes cve"]),
            ("Charlie", "Data Privacy", "Legal", "Casual", "Data exposure risks", 3, 44, ["data leak cve", "pii exposure vulnerability"]),
            ("Dana", "Red Team Lead", "Security", "Expert", "Attack simulation", 1, 78, ["privilege escalation windows", "credential dumping"]),
            ("Evan", "Blue Team", "Security", "Power User", "Defence hardening", 1, 33, ["mitigation controls", "hardening guides"]),
            ("Fran", "IT Manager", "IT", "Casual", "Operational impact", 2, 61, ["service disruption vulnerability", "availability impact"]),
            ("Glen", "App Dev", "Engineering", "Casual", "Dependency auditing", 2, 17, ["log4j cve", "npm package vulnerability"]),
            ("Hana", "Audit Lead", "Compliance", "Power User", "Evidence collection", 3, 84, ["audit finding cve", "control effectiveness"]),
            ("Ivan", "Network Engineer", "IT", "Expert", "Network CVEs", 2, 50, ["cisco ios vulnerability", "fortinet critical"]),
            ("Jess", "Malware Analyst", "Security", "Expert", "Malware signatures", 1, 25, ["trojan indicators", "botnet c2 cve"]),
            ("Kim", "Product Security", "Engineering", "Power User", "Product risk", 2, 72, ["supply chain attack", "open source risk"]),
            ("Lee", "Security Trainer", "HR", "Casual", "Training content", 3, 38, ["phishing cve", "social engineering"]),
            ("Mel", "CTO", "Executive", "Casual", "Technology risk", 3, 91, ["infrastructure vulnerabilities", "critical patch"]),
            ("Nora", "Forensics Analyst", "Security", "Expert", "Digital evidence", 1, 56, ["log4shell forensics", "post-exploitation artifacts"]),
            ("Omar", "Bug Bounty", "External", "Expert", "Vulnerability research", 1, 14, ["out-of-bounds write", "use after free 2024"]),
            ("Pat", "Security PM", "Product", "Casual", "Sprint planning", 2, 69, ["security backlog items", "high severity backlog"]),
        ]
    )
]

_FALLBACK_EXPERIMENTS: List[Dict[str, Any]] = [
    {
        "experimentId": 1,
        "timestamp": "2024-01-15T10:00:00Z",
        "hypothesis": "Increasing minimum_should_match from 75% to 85% will reduce noise for multi-word queries.",
        "change": {"path": "minimumShouldMatch", "before": "75%", "after": "85%", "label": "minimumShouldMatch 75% → 85%"},
        "baselineScore": 0.612,
        "candidateScore": 0.641,
        "deltaAbsolute": 0.029,
        "deltaPercent": 4.74,
        "decision": "kept",
        "durationMs": 1823,
        "queryFailuresBefore": [],
        "queryFailuresAfter": [],
    },
    {
        "experimentId": 2,
        "timestamp": "2024-01-15T10:00:05Z",
        "hypothesis": "Adding a phrase boost of 1.5 will reward exact phrase matches in security queries.",
        "change": {"path": "phraseBoost", "before": 0.0, "after": 1.5, "label": "phraseBoost 0.0 → 1.5"},
        "baselineScore": 0.641,
        "candidateScore": 0.659,
        "deltaAbsolute": 0.018,
        "deltaPercent": 2.81,
        "decision": "kept",
        "durationMs": 1654,
        "queryFailuresBefore": [],
        "queryFailuresAfter": [],
    },
    {
        "experimentId": 3,
        "timestamp": "2024-01-15T10:00:10Z",
        "hypothesis": "Switching multi-match type to cross_fields may improve recall for CVE IDs split across fields.",
        "change": {"path": "multiMatchType", "before": "best_fields", "after": "cross_fields", "label": "multiMatchType best_fields → cross_fields"},
        "baselineScore": 0.659,
        "candidateScore": 0.648,
        "deltaAbsolute": -0.011,
        "deltaPercent": -1.67,
        "decision": "reverted",
        "durationMs": 1901,
        "queryFailuresBefore": [],
        "queryFailuresAfter": [],
    },
    {
        "experimentId": 4,
        "timestamp": "2024-01-15T10:00:16Z",
        "hypothesis": "Tie breaker of 0.3 will reward docs that match in multiple fields for broad security queries.",
        "change": {"path": "tieBreaker", "before": 0.0, "after": 0.3, "label": "tieBreaker 0.0 → 0.3"},
        "baselineScore": 0.659,
        "candidateScore": 0.672,
        "deltaAbsolute": 0.013,
        "deltaPercent": 1.97,
        "decision": "kept",
        "durationMs": 1711,
        "queryFailuresBefore": [],
        "queryFailuresAfter": [],
    },
    {
        "experimentId": 5,
        "timestamp": "2024-01-15T10:00:22Z",
        "hypothesis": "Enabling fuzziness AUTO will help with common CVE ID typos.",
        "change": {"path": "fuzziness", "before": "0", "after": "AUTO", "label": "fuzziness 0 → AUTO"},
        "baselineScore": 0.672,
        "candidateScore": 0.661,
        "deltaAbsolute": -0.011,
        "deltaPercent": -1.64,
        "decision": "reverted",
        "durationMs": 1987,
        "queryFailuresBefore": [],
        "queryFailuresAfter": [],
    },
    {
        "experimentId": 6,
        "timestamp": "2024-01-15T10:00:28Z",
        "hypothesis": "Hybrid search with vector weight 0.35 will improve semantic matching for vague threat queries.",
        "change": {"path": "useVector", "before": False, "after": True, "label": "Hybrid search enabled"},
        "baselineScore": 0.672,
        "candidateScore": 0.698,
        "deltaAbsolute": 0.026,
        "deltaPercent": 3.87,
        "decision": "kept",
        "durationMs": 2234,
        "queryFailuresBefore": [],
        "queryFailuresAfter": [],
    },
    {
        "experimentId": 7,
        "timestamp": "2024-01-15T10:00:35Z",
        "hypothesis": "Increasing vector weight to 0.50 may help for ambiguous threat intelligence queries.",
        "change": {"path": "vectorWeight", "before": 0.35, "after": 0.50, "label": "vectorWeight 0.35 → 0.50"},
        "baselineScore": 0.698,
        "candidateScore": 0.694,
        "deltaAbsolute": -0.004,
        "deltaPercent": -0.57,
        "decision": "reverted",
        "durationMs": 1876,
        "queryFailuresBefore": [],
        "queryFailuresAfter": [],
    },
    {
        "experimentId": 8,
        "timestamp": "2024-01-15T10:00:41Z",
        "hypothesis": "Switching fusion method to RRF (Reciprocal Rank Fusion) for more balanced hybrid scoring.",
        "change": {"path": "fusionMethod", "before": "weighted_sum", "after": "rrf", "label": "fusionMethod weighted_sum → rrf"},
        "baselineScore": 0.698,
        "candidateScore": 0.714,
        "deltaAbsolute": 0.016,
        "deltaPercent": 2.29,
        "decision": "kept",
        "durationMs": 2102,
        "queryFailuresBefore": [],
        "queryFailuresAfter": [],
    },
]

_FALLBACK_COMPRESSION: Dict[str, Any] = {
    "available": True,
    "vectorField": "description_embedding",
    "vectorDims": 384,
    "methods": [
        {
            "method": "float32",
            "sizeBytes": 1536000000,
            "recallAt10": 1.0,
            "estimatedMonthlyCostUsd": 145.92,
            "sizeReductionPct": 0.0,
            "status": "done",
            "note": "Baseline: full precision",
        },
        {
            "method": "int8",
            "sizeBytes": 384000000,
            "recallAt10": 0.987,
            "estimatedMonthlyCostUsd": 36.48,
            "sizeReductionPct": 75.0,
            "status": "done",
            "note": "75% size reduction with <2% recall loss",
        },
        {
            "method": "int4",
            "sizeBytes": 192000000,
            "recallAt10": 0.971,
            "estimatedMonthlyCostUsd": 18.24,
            "sizeReductionPct": 87.5,
            "status": "done",
            "note": "87.5% size reduction with ~3% recall loss",
        },
        {
            "method": "rotated_int4",
            "sizeBytes": 192000000,
            "recallAt10": 0.979,
            "estimatedMonthlyCostUsd": 18.24,
            "sizeReductionPct": 87.5,
            "status": "done",
            "note": "Rotated quantisation improves recall vs plain int4",
        },
    ],
    "bestRecommendation": "int8",
    "projectedMonthlySavingsUsd": 109.44,
    "status": "done",
}


class DemoService:
    """Provides all demo-mode data and the demo run orchestrator."""

    def __init__(self) -> None:
        self._connection_data: Dict[str, Any] = (
            _load_demo_json("demo_connection.json") or _FALLBACK_CONNECTION
        )
        self._personas_data: List[Dict[str, Any]] = (
            _load_demo_json("demo_personas.json") or _FALLBACK_PERSONAS
        )
        self._experiments_data: List[Dict[str, Any]] = (
            _load_demo_json("demo_experiments.json") or _FALLBACK_EXPERIMENTS
        )
        self._compression_data: Dict[str, Any] = (
            _load_demo_json("demo_compression.json") or _FALLBACK_COMPRESSION
        )
        self._report_data: Optional[Dict[str, Any]] = _load_demo_json("demo_report.json")

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def create_connection(self, connection_id: str) -> ConnectionContext:
        summary = ConnectionSummary(**self._connection_data)

        # Build a simple baseline eval set
        eval_set = [
            EvalCase(
                id=f"demo_eval_{i:03d}",
                query=q,
                relevantDocIds=[doc["id"] for doc in self._connection_data.get("sampleDocs", [])[:2]],
                difficulty="medium",
                personaHint="demo",
            )
            for i, q in enumerate(
                [
                    "openssl remote code execution",
                    "critical vulnerabilities 2024",
                    "sql injection database",
                    "ransomware indicators compromise",
                    "kubernetes security advisory",
                    "privilege escalation windows",
                    "log4j vulnerability",
                    "phishing campaign cve",
                ]
            )
        ]

        baseline_profile = SearchProfile(
            lexicalFields=[
                {"field": f, "boost": 2.0 if i == 0 else 1.0}
                for i, f in enumerate(
                    self._connection_data.get("primaryTextFields", ["title", "description"])
                )
            ],
            useVector=False,
        )

        return ConnectionContext(
            connection_id=connection_id,
            mode="demo",
            summary=summary,
            eval_set=eval_set,
            baseline_profile=baseline_profile,
            llm_config=None,
            es_url=None,
            api_key=None,
            index_name=summary.indexName,
            text_fields=list(summary.primaryTextFields),
            sample_docs=[],
        )

    # ------------------------------------------------------------------
    # Personas
    # ------------------------------------------------------------------

    def build_personas(self, persona_count: int = 36) -> List[PersonaViewModel]:
        data = self._personas_data[:persona_count]
        if len(data) < persona_count:
            # Pad with generated personas if needed
            extras_needed = persona_count - len(data)
            for i in range(extras_needed):
                idx = len(data) + i
                data.append(
                    {
                        "id": f"persona_{idx:03d}",
                        "name": f"User {idx}",
                        "role": "Analyst",
                        "department": "Security",
                        "archetype": "Casual",
                        "goal": "Search for relevant content",
                        "orbit": (idx % 5) + 1,
                        "colorSeed": idx * 7,
                        "queries": ["security vulnerability", "patch advisory"],
                        "state": "idle",
                        "lastQuery": None,
                        "lastResultRank": None,
                        "successRate": 0.0,
                        "totalSearches": 0,
                        "successes": 0,
                        "partials": 0,
                        "failures": 0,
                        "angle": (idx * 2 * math.pi / persona_count),
                        "speed": 0.06 + random.Random(idx).random() * 0.04,
                        "radius": 72.0 + (((idx % 5) + 1) * 38.0),
                        "pulseUntil": None,
                        "reactUntil": None,
                    }
                )

        personas: List[PersonaViewModel] = []
        for i, p in enumerate(data):
            orbit = ((i % 5) + 1)
            angle = p.get("angle", (i * 2 * math.pi / len(data)))
            radius = 72.0 + (orbit * 38.0)
            try:
                personas.append(
                    PersonaViewModel(
                        id=p.get("id", f"persona_{i:03d}"),
                        name=p.get("name", f"Persona {i}"),
                        role=p.get("role", "Analyst"),
                        department=p.get("department", "Unknown"),
                        archetype=p.get("archetype", "Casual"),
                        goal=p.get("goal", "Search"),
                        orbit=orbit,
                        colorSeed=p.get("colorSeed", i * 7),
                        queries=p.get("queries", ["query"]),
                        state="idle",
                        lastQuery=None,
                        lastResultRank=None,
                        successRate=0.0,
                        totalSearches=0,
                        successes=0,
                        partials=0,
                        failures=0,
                        angle=angle,
                        speed=p.get("speed", 0.06 + random.Random(i).random() * 0.04),
                        radius=radius,
                        pulseUntil=None,
                        reactUntil=None,
                    )
                )
            except Exception as exc:
                logger.warning("Failed to build persona %d: %s", i, exc)

        return personas

    # ------------------------------------------------------------------
    # Experiments data access
    # ------------------------------------------------------------------

    @property
    def experiments(self) -> List[Dict[str, Any]]:
        return list(self._experiments_data)

    @property
    def compression(self) -> Dict[str, Any]:
        return dict(self._compression_data)

    # ------------------------------------------------------------------
    # Demo orchestrator
    # ------------------------------------------------------------------

    async def run_demo_orchestrator(
        self,
        ctx: RunContext,
        run_manager: Any,  # RunManager - avoid circular import
        experiment_interval_seconds: float = 2.0,
    ) -> None:
        """
        Replay demo_experiments.json with timing delays, updating the RunContext
        and publishing WebSocket events via run_manager.
        """
        from ..models.contracts import ExperimentRecord, SearchProfileChange

        run_id = ctx.run_id
        now_ts = lambda: datetime.now(timezone.utc).isoformat()

        # Set initial baseline score from first experiment
        experiments_data = self._experiments_data
        if experiments_data:
            ctx.metrics.baselineScore = experiments_data[0]["baselineScore"]
            ctx.metrics.currentScore = experiments_data[0]["baselineScore"]
            ctx.metrics.bestScore = experiments_data[0]["baselineScore"]

        # Pre-set compression as available + running so the UI doesn't show "no vector field"
        if ctx.summary.vectorField:
            ctx.compression.available = True
            ctx.compression.vectorField = ctx.summary.vectorField
            ctx.compression.vectorDims = ctx.summary.vectorDims
            ctx.compression.status = "running"

        ctx.stage = "running"
        ctx.started_at = now_ts()

        await run_manager.publish(
            run_id,
            {
                "type": "run.stage",
                "payload": {"runId": run_id, "stage": "running"},
            },
        )

        start_time = time.monotonic()

        for i, exp_data in enumerate(experiments_data):
            if ctx.cancel_flag.is_set():
                break

            # Wait for the experiment interval
            try:
                await asyncio.wait_for(
                    asyncio.shield(ctx.cancel_flag.wait()),
                    timeout=experiment_interval_seconds,
                )
                break  # cancel was set
            except asyncio.TimeoutError:
                pass  # normal - continue

            try:
                change = SearchProfileChange(**exp_data["change"])
                record = ExperimentRecord(
                    experimentId=exp_data["experimentId"],
                    timestamp=now_ts(),
                    hypothesis=exp_data["hypothesis"],
                    change=change,
                    baselineScore=exp_data["baselineScore"],
                    candidateScore=exp_data["candidateScore"],
                    deltaAbsolute=exp_data["deltaAbsolute"],
                    deltaPercent=exp_data["deltaPercent"],
                    decision=exp_data["decision"],
                    durationMs=exp_data.get("durationMs", 1500),
                    queryFailuresBefore=exp_data.get("queryFailuresBefore", []),
                    queryFailuresAfter=exp_data.get("queryFailuresAfter", []),
                )
                ctx.experiments.append(record)

                # Apply profile change if kept
                if record.decision == "kept":
                    _apply_profile_change(ctx.current_profile, change)
                    _apply_profile_change(ctx.best_profile, change)
                    ctx.metrics.improvementsKept += 1

                ctx.metrics.currentScore = record.candidateScore if record.decision == "kept" else record.baselineScore
                if ctx.metrics.currentScore > ctx.metrics.bestScore:
                    ctx.metrics.bestScore = ctx.metrics.currentScore
                    ctx._best_score = ctx.metrics.bestScore

                ctx.metrics.experimentsRun = i + 1
                ctx.metrics.improvementPct = (
                    (ctx.metrics.bestScore - ctx.metrics.baselineScore)
                    / max(ctx.metrics.baselineScore, 0.001)
                ) * 100
                ctx.metrics.elapsedSeconds = time.monotonic() - start_time
                ctx.metrics.scoreTimeline.append(
                    {"t": ctx.metrics.elapsedSeconds, "score": ctx.metrics.currentScore}
                )

                # Publish experiment event
                await run_manager.publish(
                    run_id,
                    {
                        "type": "experiment.completed",
                        "payload": record.model_dump(),
                    },
                )

                # Publish metrics update
                await run_manager.publish(
                    run_id,
                    {
                        "type": "metrics.tick",
                        "payload": ctx.metrics.model_dump(),
                    },
                )

                # Simulate persona activity for this experiment cycle
                # First reset all personas to idle so the frontend sees fresh transitions
                for persona in ctx.personas:
                    persona.state = "idle"

                rng = random.Random(i + 100)
                batch_size = min(8, len(ctx.personas))
                if batch_size > 0:
                    selected = rng.sample(ctx.personas, batch_size)
                    for persona in selected:
                        if not persona.queries:
                            continue
                        persona.lastQuery = rng.choice(persona.queries)
                        persona.totalSearches += 1
                        roll = rng.random()
                        base = ctx.metrics.currentScore
                        if roll < base:
                            persona.state = "success"
                            persona.successes += 1
                            persona.lastResultRank = rng.randint(1, 3)
                        elif roll < base + 0.2:
                            persona.state = "partial"
                            persona.partials += 1
                            persona.lastResultRank = rng.randint(4, 8)
                        else:
                            persona.state = "failure"
                            persona.failures += 1
                            persona.lastResultRank = None
                        total = persona.totalSearches
                        persona.successRate = (persona.successes + persona.partials * 0.5) / max(total, 1)

                    ctx.metrics.personaSuccessRate = sum(
                        p.successRate for p in ctx.personas
                    ) / len(ctx.personas)

                    await run_manager.publish(
                        run_id,
                        {
                            "type": "persona.batch",
                            "payload": {
                                "runId": run_id,
                                "personas": [p.model_dump() for p in ctx.personas],
                            },
                        },
                    )

            except Exception as exc:
                logger.error("Demo orchestrator error on experiment %d: %s", i, exc)

        # Finalize compression
        try:
            compression = CompressionSummary(**self._compression_data)
            ctx.compression = compression
            ctx.metrics.projectedMonthlySavingsUsd = compression.projectedMonthlySavingsUsd
            await run_manager.publish(
                run_id,
                {
                    "type": "compression.updated",
                    "payload": compression.model_dump(),
                },
            )
        except Exception as exc:
            logger.error("Demo compression setup failed: %s", exc)

        # Generate and publish report
        try:
            report_data = self._report_data
            duration_seconds = round(ctx.metrics.elapsedSeconds, 2)
            top_changes = [e.change.label for e in ctx.experiments if e.decision == "kept"][:2]
            top_changes_text = " and ".join(top_changes) if top_changes else "query weighting changes"
            dynamic_summary = {
                "headline": (
                    f"Search quality improved {ctx.metrics.improvementPct:.1f}% on "
                    f"{ctx.summary.baselineEvalCount} test queries."
                ),
                "overview": (
                    f"This demo run lasted about {_format_demo_duration(duration_seconds)}, "
                    f"tested {ctx.metrics.experimentsRun} profile changes, and kept "
                    f"{ctx.metrics.improvementsKept} of them. The best profile moved nDCG@10 "
                    f"from {ctx.metrics.baselineScore:.3f} to {ctx.metrics.bestScore:.3f}, "
                    f"with the biggest gains coming from {top_changes_text}."
                ),
                "nextSteps": [
                    "Review the accepted search-profile changes and compare them against the queries your users care about most.",
                    "Run the same workflow against a real Elasticsearch index or benchmark target with a larger test set.",
                    "Use this result as the baseline for the next tuning pass and add fresh failure cases before rerunning.",
                ],
                "baselineScore": ctx.metrics.baselineScore,
                "bestScore": ctx.metrics.bestScore,
                "improvementPct": round(ctx.metrics.improvementPct, 2),
                "experimentsRun": ctx.metrics.experimentsRun,
                "improvementsKept": ctx.metrics.improvementsKept,
                "durationSeconds": duration_seconds,
                "projectedMonthlySavingsUsd": ctx.metrics.projectedMonthlySavingsUsd,
            }
            if report_data:
                report_data["runId"] = run_id
                report_data["generatedAt"] = now_ts()
                report_data["summary"] = dynamic_summary
                report_data["connection"] = ctx.summary.model_dump()
                report_data["searchProfileBefore"] = ctx.baseline_profile.model_dump()
                report_data["searchProfileAfter"] = ctx.best_profile.model_dump()
                report_data["compression"] = ctx.compression.model_dump()
                report_data["warnings"] = ctx.warnings
            else:
                report_data = {
                    "runId": run_id,
                    "generatedAt": now_ts(),
                    "mode": "demo",
                    "summary": dynamic_summary,
                    "connection": ctx.summary.model_dump(),
                    "searchProfileBefore": ctx.baseline_profile.model_dump(),
                    "searchProfileAfter": ctx.best_profile.model_dump(),
                    "diff": [e.change.model_dump() for e in ctx.experiments if e.decision == "kept"],
                    "personaImpact": [],
                    "experiments": [e.model_dump() for e in ctx.experiments],
                    "compression": ctx.compression.model_dump(),
                    "warnings": ctx.warnings,
                }
            await run_manager.publish(
                run_id,
                {
                    "type": "report.ready",
                    "payload": report_data,
                },
            )
        except Exception as exc:
            logger.error("Demo report generation failed: %s", exc)

        # Mark completed
        ctx.stage = "completed"
        ctx.completed_at = now_ts()

        await run_manager.publish(
            run_id,
            {
                "type": "run.stage",
                "payload": {"runId": run_id, "stage": "completed"},
            },
        )

        logger.info("Demo run %s completed with %d experiments", run_id, len(ctx.experiments))


def _apply_profile_change(profile: SearchProfile, change: SearchProfileChange) -> None:
    """Apply a single SearchProfileChange to a SearchProfile in-place."""
    path = change.path
    value = change.after
    try:
        if hasattr(profile, path):
            setattr(profile, path, value)
    except Exception as exc:
        logger.warning("Failed to apply profile change %s=%r: %s", path, value, exc)
