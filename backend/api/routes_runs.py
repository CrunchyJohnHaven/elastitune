from __future__ import annotations

import logging
import math
import random
import re
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from ..models.contracts import (
    PersonaViewModel,
    RunSnapshot,
    StartRunRequest,
    StartRunResponse,
    StopRunResponse,
)
from ..models.runtime import RunContext
from ..services.llm_service import LLMService
from ..services.run_manager import RunManager
from ..services.report_service import ReportService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["runs"])


def _get_run_manager(request: Request) -> RunManager:
    return request.app.state.run_manager


@router.post("/runs", response_model=StartRunResponse)
async def start_run(body: StartRunRequest, request: Request) -> StartRunResponse:
    """
    Create and start a new optimization run for the given connectionId.
    Builds personas, creates a RunContext, stores it, and launches background tasks.
    """
    run_manager: RunManager = _get_run_manager(request)

    conn_ctx = await run_manager.get_connection(body.connectionId)
    if not conn_ctx:
        raise HTTPException(
            status_code=404,
            detail=f"Connection '{body.connectionId}' not found. Call /connect first.",
        )

    run_id = str(uuid.uuid4())

    # If continuing from a previous run, load its best profile as the new baseline
    previous_best_profile = None
    previous_experiments = []
    if body.previousRunId:
        prev_ctx = await run_manager.get_run(body.previousRunId)
        if prev_ctx and prev_ctx.best_profile:
            previous_best_profile = prev_ctx.best_profile.model_copy(deep=True)
            previous_experiments = list(prev_ctx.experiments)
            logger.info(
                "Continuing from run %s — using its best profile as baseline",
                body.previousRunId,
            )
        else:
            # Try loading from persisted report
            prev_report = await run_manager.get_report(body.previousRunId)
            if prev_report and prev_report.searchProfileAfter:
                previous_best_profile = prev_report.searchProfileAfter.model_copy(deep=True)
                previous_experiments = list(prev_report.experiments)
                logger.info(
                    "Continuing from persisted run %s — using its recommended profile",
                    body.previousRunId,
                )

    # Build personas
    personas: List[PersonaViewModel] = await _build_personas(
        persona_count=body.personaCount,
        mode=conn_ctx.mode,
        domain=conn_ctx.summary.detectedDomain,
        sample_docs=conn_ctx.sample_docs,
        text_fields=conn_ctx.text_fields,
        llm_config=conn_ctx.llm_config,
    )

    # Override baseline profile if continuing from a previous run
    if previous_best_profile:
        conn_ctx.baseline_profile = previous_best_profile

    run_ctx = RunContext(
        run_id=run_id,
        connection=conn_ctx,
        personas=personas,
        max_experiments=body.maxExperiments,
        duration_minutes=body.durationMinutes,
        auto_stop_on_plateau=body.autoStopOnPlateau,
    )
    if body.previousRunId:
        run_ctx.previous_run_id = body.previousRunId
        run_ctx.prior_experiments = previous_experiments

    # Pre-set compression as available if the cluster has a vector field
    if conn_ctx.summary.vectorField:
        run_ctx.compression.available = True
        run_ctx.compression.vectorField = conn_ctx.summary.vectorField
        run_ctx.compression.vectorDims = conn_ctx.summary.vectorDims
        run_ctx.compression.status = "running"

    await run_manager.create_run(run_id, run_ctx)
    await run_manager.start_run_tasks(run_id)

    return StartRunResponse(runId=run_id, stage="starting")


@router.get("/runs/{run_id}", response_model=RunSnapshot)
async def get_run(run_id: str, request: Request) -> RunSnapshot:
    """Return the current snapshot of the run."""
    run_manager: RunManager = _get_run_manager(request)
    snapshot = await run_manager.get_snapshot(run_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return snapshot


@router.get("/runs")
async def list_runs(
    request: Request,
    limit: int = 50,
    indexName: Optional[str] = None,
    completedOnly: bool = False,
) -> JSONResponse:
    """List persisted search runs for report/history views."""
    run_manager: RunManager = _get_run_manager(request)
    runs = await run_manager.list_search_runs(
        limit=limit,
        index_name=indexName,
        completed_only=completedOnly,
    )
    return JSONResponse(content={"runs": runs})


@router.post("/runs/{run_id}/stop", response_model=StopRunResponse)
async def stop_run(run_id: str, request: Request) -> StopRunResponse:
    """Request graceful stop of a running optimization run."""
    run_manager: RunManager = _get_run_manager(request)
    ctx = await run_manager.get_run(run_id)
    if not ctx:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    await run_manager.stop_run(run_id)
    return StopRunResponse(runId=run_id, stage="stopping")


@router.get("/runs/{run_id}/report")
async def get_report(run_id: str, request: Request) -> JSONResponse:
    """
    Return the final report for a completed run.
    Generates the report on demand if not already cached.
    """
    run_manager: RunManager = _get_run_manager(request)
    ctx = await run_manager.get_run(run_id)
    if not ctx:
        persisted = await run_manager.get_report(run_id)
        if not persisted:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
        import orjson

        return JSONResponse(
            content=orjson.loads(persisted.model_dump_json()),
            media_type="application/json",
        )

    if ctx.stage not in ("completed", "stopping", "error"):
        raise HTTPException(
            status_code=409,
            detail=f"Run is still in stage '{ctx.stage}'. Wait for completion.",
        )

    if ctx.report is None:
        persisted = await run_manager.get_report(run_id)
        if persisted is not None:
            ctx.report = persisted
        else:
            report_svc = ReportService()
            ctx.report = report_svc.generate(ctx)

    import orjson

    return JSONResponse(
        content=orjson.loads(ctx.report.model_dump_json()),
        media_type="application/json",
    )


@router.get("/runs/{run_id}/preview-query")
async def preview_query(run_id: str, queryId: str, request: Request) -> JSONResponse:
    """Return before/after result previews and ready-to-paste query DSL for one eval query."""
    run_manager: RunManager = _get_run_manager(request)

    ctx = await run_manager.get_run(run_id)
    report = await run_manager.get_report(run_id)
    if ctx is None and report is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    if report is None and ctx and ctx.report:
        report = ctx.report

    if report is None:
        raise HTTPException(status_code=404, detail=f"Report for run '{run_id}' not found")

    query_row = next((row for row in report.queryBreakdown if row.queryId == queryId), None)
    if query_row is None:
        raise HTTPException(status_code=404, detail=f"Query '{queryId}' not found in report")

    baseline_results = [item.model_dump() for item in query_row.baselineTopResults]
    optimized_results = [item.model_dump() for item in query_row.bestTopResults]
    baseline_query = None
    optimized_query = None

    connection_config = report.connectionConfig
    if connection_config and connection_config.indexName and connection_config.esUrl:
        try:
            from ..services.es_service import ESService

            es_svc = ESService(
                es_url=connection_config.esUrl,
                api_key=connection_config.apiKey or None,
            )
            try:
                baseline_query = es_svc.build_query_body(
                    query_row.query,
                    report.searchProfileBefore,
                    size=5,
                )
                optimized_query = es_svc.build_query_body(
                    query_row.query,
                    report.searchProfileAfter,
                    size=5,
                )
                baseline_results = await es_svc.execute_profile_query_with_hits(
                    index=connection_config.indexName,
                    query_text=query_row.query,
                    profile=report.searchProfileBefore,
                    size=5,
                )
                optimized_results = await es_svc.execute_profile_query_with_hits(
                    index=connection_config.indexName,
                    query_text=query_row.query,
                    profile=report.searchProfileAfter,
                    size=5,
                )
            finally:
                await es_svc.close()
        except Exception as exc:
            logger.warning("Preview query fallback for run %s query %s: %s", run_id, queryId, exc)

    return JSONResponse(
        content={
            "queryId": query_row.queryId,
            "query": query_row.query,
            "baselineResults": baseline_results,
            "optimizedResults": optimized_results,
            "baselineQueryDsl": baseline_query,
            "optimizedQueryDsl": optimized_query,
        }
    )


# ---------------------------------------------------------------------------
# Persona generation helpers
# ---------------------------------------------------------------------------

_PERSONA_TEMPLATES = [
    ("Alex", "SOC Analyst", "Security", "Power User", "Detect active threats", ["critical cve", "active exploitation", "threat intel"]),
    ("Sam", "Threat Hunter", "Security", "Expert", "Hunt advanced threats", ["lateral movement", "persistence mechanism", "c2 beacon"]),
    ("Jordan", "CISO", "Executive", "Casual", "Understand risk posture", ["top risks", "compliance gap", "board report"]),
    ("Taylor", "DevSecOps Engineer", "Engineering", "Power User", "Secure CI/CD pipeline", ["supply chain vulnerability", "container cve", "sast findings"]),
    ("Morgan", "Incident Responder", "Security", "Expert", "Triage active incidents", ["ioc hash", "ransomware playbook", "evidence collection"]),
    ("Casey", "Vulnerability Manager", "IT", "Expert", "Prioritise patching", ["cvss 9", "patch priority", "asset exposure"]),
    ("Riley", "Compliance Officer", "Legal", "Casual", "Map controls to regulations", ["gdpr control", "hipaa requirement", "audit evidence"]),
    ("Drew", "Penetration Tester", "Security", "Expert", "Research exploitation paths", ["exploit poc", "privilege escalation", "bypass technique"]),
    ("Avery", "Security Architect", "Engineering", "Power User", "Design secure systems", ["zero trust pattern", "cloud misconfiguration", "network segmentation"]),
    ("Blake", "Cloud Engineer", "DevOps", "Casual", "Harden cloud infrastructure", ["aws advisory", "azure cve", "kubernetes security"]),
    ("Charlie", "Privacy Analyst", "Legal", "Casual", "Assess data exposure risks", ["pii leak", "data breach notification", "dpo guidance"]),
    ("Dana", "Red Team Lead", "Security", "Expert", "Simulate adversary TTPs", ["credential dumping", "kerberoasting", "living off the land"]),
    ("Evan", "Blue Team Analyst", "Security", "Power User", "Detect and respond", ["detection rule", "sigma rule", "yara signature"]),
    ("Fran", "IT Operations Manager", "IT", "Casual", "Minimize service disruption", ["availability impact", "service outage cve", "emergency patch"]),
    ("Glen", "Application Developer", "Engineering", "Casual", "Audit open source dependencies", ["npm vulnerability", "log4j", "dependency confusion"]),
    ("Hana", "Internal Auditor", "Compliance", "Power User", "Gather audit evidence", ["control failure", "remediation status", "risk acceptance"]),
    ("Ivan", "Network Engineer", "IT", "Expert", "Secure network infrastructure", ["cisco advisory", "fortinet vulnerability", "bgp hijack"]),
    ("Jess", "Malware Analyst", "Security", "Expert", "Reverse engineer threats", ["dropper behaviour", "c2 protocol", "sandbox evasion"]),
    ("Kim", "Product Security Manager", "Engineering", "Power User", "Manage product risk", ["third party risk", "sbom vulnerability", "responsible disclosure"]),
    ("Lee", "Security Awareness Trainer", "HR", "Casual", "Create training content", ["phishing simulation", "social engineering cve", "security culture"]),
    ("Mel", "CTO", "Executive", "Casual", "Strategic technology risk", ["critical infrastructure", "nation state threat", "technology dependency"]),
    ("Nora", "Digital Forensics Analyst", "Security", "Expert", "Investigate breaches", ["forensic artifact", "timeline analysis", "disk image"]),
    ("Omar", "Bug Bounty Researcher", "External", "Expert", "Find and report vulnerabilities", ["memory corruption", "use after free", "heap overflow"]),
    ("Pat", "Security Product Manager", "Product", "Casual", "Plan security roadmap", ["security debt", "feature request", "risk register"]),
]


_GENERAL_PERSONA_SEEDS: List[Dict[str, Any]] = [
    {
        "name": "Jamie",
        "role": "Researcher",
        "department": "Knowledge",
        "archetype": "Power User",
        "goal": "Find the most relevant source fast",
        "queries": ["getting started guide", "best practice", "troubleshooting workflow"],
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

_ECOMMERCE_PERSONA_SEEDS: List[Dict[str, Any]] = [
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
        "queries": ["sensitive skin foundation", "matte lip color", "shade matching help"],
    },
]

_STOPWORDS = {
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


async def _build_personas(
    persona_count: int = 36,
    mode: str = "demo",
    domain: str = "general",
    sample_docs: Optional[List[Dict[str, Any]]] = None,
    text_fields: Optional[List[str]] = None,
    llm_config: Optional[Any] = None,
) -> List[PersonaViewModel]:
    """Build PersonaViewModel instances for a run."""
    sample_docs = sample_docs or []
    text_fields = text_fields or []

    templates = await _resolve_persona_templates(
        persona_count=persona_count,
        mode=mode,
        domain=domain,
        sample_docs=sample_docs,
        text_fields=text_fields,
        llm_config=llm_config,
    )

    personas: List[PersonaViewModel] = []
    rng = random.Random(2024)

    template_count = len(templates)
    for i, template in enumerate(templates[:persona_count]):
        name, role, dept, arch, goal, queries = template
        cycle = i // template_count
        display_name = name if cycle == 0 else f"{name} {cycle + 1}"
        orbit = (i % 5) + 1
        angle = (i * 2 * math.pi) / persona_count
        speed = 0.05 + rng.random() * 0.05
        radius = 72.0 + orbit * 38.0

        personas.append(
            PersonaViewModel(
                id=f"persona_{i:03d}",
                name=display_name,
                role=role,
                department=dept,
                archetype=arch,
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
                angle=angle,
                speed=speed,
                radius=radius,
                pulseUntil=None,
                reactUntil=None,
            )
        )

    return personas


async def _resolve_persona_templates(
    persona_count: int,
    mode: str,
    domain: str,
    sample_docs: List[Dict[str, Any]],
    text_fields: List[str],
    llm_config: Optional[Any],
) -> List[tuple[str, str, str, str, str, List[str]]]:
    if mode == "demo":
        return _cycle_templates(_PERSONA_TEMPLATES, persona_count)

    llm_templates = await _generate_personas_with_llm(
        persona_count=persona_count,
        domain=domain,
        sample_docs=sample_docs,
        text_fields=text_fields,
        llm_config=llm_config,
    )
    if llm_templates:
        return llm_templates

    if _looks_like_product_catalog(sample_docs, text_fields):
        return _cycle_templates(_seed_dicts_to_templates(_ECOMMERCE_PERSONA_SEEDS), persona_count)

    if domain == "general":
        generated = _generate_general_persona_templates(sample_docs, text_fields, persona_count)
        if generated:
            return generated

    return _cycle_templates(_PERSONA_TEMPLATES, persona_count)


async def _generate_personas_with_llm(
    persona_count: int,
    domain: str,
    sample_docs: List[Dict[str, Any]],
    text_fields: List[str],
    llm_config: Optional[Any],
) -> List[tuple[str, str, str, str, str, List[str]]]:
    if not llm_config or llm_config.provider == "disabled":
        return []

    llm_svc = LLMService(llm_config)
    generated = await llm_svc.generate_personas(
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

    if not templates:
        return []
    return _cycle_templates(templates, persona_count)


def _generate_general_persona_templates(
    sample_docs: List[Dict[str, Any]],
    text_fields: List[str],
    persona_count: int,
) -> List[tuple[str, str, str, str, str, List[str]]]:
    seeds = list(_GENERAL_PERSONA_SEEDS)
    query_bank: List[str] = []
    for doc in sample_docs[:18]:
        for field in text_fields[:3]:
            value = doc.get(field)
            if not isinstance(value, str):
                continue
            query = _derive_query(value)
            if query and query not in query_bank:
                query_bank.append(query)
        if len(query_bank) >= persona_count * 2:
            break

    if not query_bank:
        return _cycle_templates(_seed_dicts_to_templates(seeds), persona_count)

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


def _seed_dicts_to_templates(
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


def _cycle_templates(
    templates: List[tuple[str, str, str, str, str, List[str]]],
    persona_count: int,
) -> List[tuple[str, str, str, str, str, List[str]]]:
    if not templates:
        templates = _PERSONA_TEMPLATES

    cycled = list(templates[:persona_count])
    while len(cycled) < persona_count:
        cycled.extend(templates[: persona_count - len(cycled)])
    return cycled


def _looks_like_product_catalog(sample_docs: List[Dict[str, Any]], text_fields: List[str]) -> bool:
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


def _derive_query(value: str) -> str:
    tokens = [
        token
        for token in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9._-]*", value.lower())
        if len(token) >= 3 and token not in _STOPWORDS
    ]
    return " ".join(tokens[:5])
