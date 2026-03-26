from __future__ import annotations

import logging
import re
import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from ..models.contracts import (
    ConnectRequest,
    ConnectResponse,
    ConnectionSummary,
    EvalCase,
    LlmConfig,
    SampleDoc,
    SearchProfile,
)
from ..models.runtime import ConnectionContext
from ..services.run_manager import RunManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["connect"])


_BENCHMARK_CONFIGS = {
    "products-catalog": {
        "id": "products",
        "label": "Product Store",
        "expected_doc_count": 931,
        "setup_command": "python benchmarks/setup.py --only products-catalog",
    },
    "books-catalog": {
        "id": "books",
        "label": "Books Catalog",
        "expected_doc_count": 2000,
        "setup_command": "python benchmarks/setup.py --only books-catalog",
    },
    "workplace-docs": {
        "id": "workplace",
        "label": "Workplace Docs",
        "expected_doc_count": 15,
        "setup_command": "python benchmarks/setup.py --only workplace-docs",
    },
    "security-siem": {
        "id": "security",
        "label": "Security SIEM",
        "expected_doc_count": 301,
        "setup_command": "python benchmarks/setup.py --only security-siem",
    },
    "tmdb": {
        "id": "tmdb",
        "label": "TMDB Movies",
        "expected_doc_count": 8516,
        "setup_command": "python benchmarks/setup.py --only tmdb",
    },
}


def _get_run_manager(request: Request) -> RunManager:
    return request.app.state.run_manager


@router.get("/connect/benchmarks")
async def benchmark_health(
    request: Request, esUrl: str = "http://127.0.0.1:9200"
) -> JSONResponse:
    from ..services.es_service import ESService

    es_svc = ESService(es_url=esUrl)
    reachable = False
    presets = []

    try:
        reachable = await es_svc.ping()
        for index_name, config in _BENCHMARK_CONFIGS.items():
            ready = False
            doc_count = 0
            try:
                await es_svc.get_mapping(index_name)
                doc_count = await es_svc.count_docs(index_name)
                ready = doc_count >= config["expected_doc_count"]
            except Exception:
                ready = False

            presets.append(
                {
                    "id": config["id"],
                    "label": config["label"],
                    "indexName": index_name,
                    "expectedDocCount": config["expected_doc_count"],
                    "docCount": doc_count,
                    "ready": ready,
                    "setupCommand": config["setup_command"],
                    "reachable": reachable,
                }
            )
    finally:
        await es_svc.close()

    return JSONResponse(content={"reachable": reachable, "presets": presets})


@router.post("/connect", response_model=ConnectResponse)
async def connect(body: ConnectRequest, request: Request) -> ConnectResponse:
    """
    Validate connection parameters, analyse the target index (live mode)
    or load demo data (demo mode), build an initial eval set, and return
    a ConnectResponse that the frontend uses to transition to the ready state.
    """
    run_manager: RunManager = _get_run_manager(request)
    connection_id = str(uuid.uuid4())
    warnings: List[str] = []

    # ------------------------------------------------------------------ demo
    if body.mode == "demo":
        from ..services.demo_service import DemoService

        demo_svc = DemoService()
        ctx = demo_svc.create_connection(connection_id)
        await run_manager.create_connection(connection_id, ctx)

        return ConnectResponse(
            connectionId=connection_id,
            mode="demo",
            stage="ready",
            summary=ctx.summary,
            warnings=[],
        )

    # ------------------------------------------------------------------ live
    if not body.esUrl:
        raise HTTPException(status_code=422, detail="esUrl is required for live mode")
    if not body.indexName:
        raise HTTPException(
            status_code=422, detail="indexName is required for live mode"
        )

    from ..services.es_service import ESService
    from ..services.llm_service import LLMService
    from ..services.profile_recommender import ProfileRecommender

    es_svc = ESService(es_url=body.esUrl, api_key=body.apiKey or None)

    # Ping
    try:
        alive = await es_svc.ping()
        if not alive:
            raise HTTPException(
                status_code=502, detail="Cannot reach Elasticsearch cluster"
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502, detail=f"Elasticsearch connection failed: {exc}"
        )

    # Cluster info
    cluster_info = await es_svc.get_cluster_info()
    cluster_name: str = cluster_info.get("cluster_name", "unknown")
    cluster_version: Optional[str] = (
        cluster_info.get("version", {}).get("number")
        if isinstance(cluster_info.get("version"), dict)
        else None
    )

    # Analyse index
    try:
        analysis = await es_svc.analyze_index(
            index=body.indexName,
            vector_field_override=body.vectorFieldOverride,
            max_sample_docs=body.maxSampleDocs,
        )
    except ValueError as exc:
        benchmark = _BENCHMARK_CONFIGS.get(body.indexName)
        if benchmark:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"The {body.indexName} index hasn't been created yet. "
                    f"Run: {benchmark['setup_command']}"
                ),
            )
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Index analysis failed: {exc}")

    text_fields: List[str] = analysis["text_fields"]
    vector_field: Optional[str] = analysis["vector_field"]
    vector_dims: Optional[int] = analysis["vector_dims"]
    raw_docs: List = analysis["sample_docs"]
    domain = analysis["domain"]

    if not text_fields:
        warnings.append(
            "No text fields detected in index mapping. Search quality may be limited."
        )

    doc_count = await es_svc.count_docs(body.indexName)
    benchmark = _BENCHMARK_CONFIGS.get(body.indexName)
    if benchmark and doc_count < benchmark["expected_doc_count"]:
        warnings.append(
            f"{body.indexName} currently has {doc_count} docs; the benchmark target is {benchmark['expected_doc_count']}. "
            f"If results look unstable, rerun: {benchmark['setup_command']}"
        )

    # Build SampleDoc list
    sample_docs: List[SampleDoc] = []
    title_field = text_fields[0] if text_fields else "title"
    excerpt_field = (
        text_fields[1]
        if len(text_fields) > 1
        else text_fields[0]
        if text_fields
        else "description"
    )

    for doc in raw_docs[:10]:
        doc_id = str(doc.get("_id", ""))
        title_val = str(doc.get(title_field, doc_id))[:100]
        excerpt_val = str(doc.get(excerpt_field, ""))[:300]
        field_preview = {
            f: str(doc.get(f, ""))[:100] for f in text_fields[:4] if f in doc
        }
        sample_docs.append(
            SampleDoc(
                id=doc_id,
                title=title_val,
                excerpt=excerpt_val,
                fieldPreview=field_preview,
            )
        )

    # Build eval set
    eval_set: List[EvalCase] = []

    if body.uploadedEvalSet:
        eval_set = body.uploadedEvalSet
    elif body.autoGenerateEval:
        llm_config = body.llm or LlmConfig(provider="disabled")
        llm_svc = LLMService(llm_config)

        if llm_svc.available:
            try:
                generated = await llm_svc.generate_eval_set(
                    domain=domain,
                    sample_docs=raw_docs[:15],
                    text_fields=text_fields,
                    count=20,
                )
                for i, item in enumerate(generated):
                    if isinstance(item, dict):
                        try:
                            eval_set.append(
                                EvalCase(
                                    id=item.get("id", f"eval_{i:03d}"),
                                    query=item.get("query", ""),
                                    relevantDocIds=item.get("relevantDocIds", []),
                                    difficulty=item.get("difficulty"),
                                    personaHint=item.get("personaHint"),
                                )
                            )
                        except Exception as e:
                            logger.warning("Skipping invalid eval case %d: %s", i, e)
            except Exception as exc:
                logger.warning("LLM eval generation failed: %s", exc)
                warnings.append("LLM eval generation failed; using heuristic eval set.")

        if not eval_set:
            # Heuristic eval set from sample docs
            eval_set = _build_heuristic_eval_set(raw_docs, text_fields, domain)

    summary = ConnectionSummary(
        clusterName=cluster_name,
        clusterVersion=cluster_version,
        indexName=body.indexName,
        docCount=doc_count,
        detectedDomain=domain,
        primaryTextFields=text_fields[:8],
        vectorField=vector_field,
        vectorDims=vector_dims,
        sampleDocs=sample_docs,
        baselineEvalCount=len(eval_set),
        baselineReady=len(eval_set) > 0,
    )

    # Build baseline SearchProfile
    profile_dict = await es_svc.build_baseline_profile(
        text_fields=text_fields,
        vector_field=vector_field,
    )
    baseline_profile = SearchProfile(**profile_dict)
    baseline_profile, benchmark_hint = ProfileRecommender().recommend(
        summary, baseline_profile
    )
    if benchmark_hint:
        warnings.append(
            f"Seeded the starting profile using the {benchmark_hint} benchmark pattern."
        )

    ctx = ConnectionContext(
        connection_id=connection_id,
        mode="live",
        summary=summary,
        eval_set=eval_set,
        baseline_profile=baseline_profile,
        llm_config=body.llm,
        es_url=body.esUrl,
        api_key=body.apiKey or None,
        index_name=body.indexName,
        text_fields=text_fields,
        sample_docs=raw_docs,
    )

    await run_manager.create_connection(connection_id, ctx)
    await es_svc.close()

    return ConnectResponse(
        connectionId=connection_id,
        mode="live",
        stage="ready",
        summary=summary,
        warnings=warnings,
    )


@router.post("/probe")
async def probe_index(body: ConnectRequest, request: Request) -> JSONResponse:
    """
    Generate adversarial audit queries and report which obvious intents still fail.
    """
    if not body.esUrl or not body.indexName:
        raise HTTPException(status_code=422, detail="esUrl and indexName are required")

    from ..services.es_service import ESService

    es_svc = ESService(es_url=body.esUrl, api_key=body.apiKey or None)
    try:
        analysis = await es_svc.analyze_index(
            index=body.indexName,
            vector_field_override=body.vectorFieldOverride,
            max_sample_docs=min(body.maxSampleDocs, 30),
        )
        profile = SearchProfile(
            **await es_svc.build_baseline_profile(
                text_fields=analysis["text_fields"],
                vector_field=analysis["vector_field"],
            )
        )

        failures = []
        for idx, doc in enumerate(analysis["sample_docs"][:12], start=1):
            title = str(
                doc.get("title")
                or doc.get("name")
                or doc.get("summary")
                or doc.get("_id", "")
            )
            query_terms = [
                part
                for part in re.split(r"[^a-zA-Z0-9]+", title.lower())
                if len(part) > 3
            ][:4]
            if not query_terms:
                continue
            query = " ".join(query_terms)
            ranked_doc_ids = await es_svc.execute_profile_query(
                index=body.indexName,
                query_text=query,
                profile=profile,
                size=10,
            )
            found_rank = None
            for rank, doc_id in enumerate(ranked_doc_ids, start=1):
                if doc_id == str(doc.get("_id")):
                    found_rank = rank
                    break

            if found_rank is None or found_rank > 5:
                failures.append(
                    {
                        "id": f"probe_{idx:03d}",
                        "query": query,
                        "expectedDocId": str(doc.get("_id")),
                        "expectedTitle": title[:140],
                        "foundRank": found_rank,
                        "issue": "Expected document did not surface near the top results.",
                    }
                )

        return JSONResponse(
            content={
                "indexName": body.indexName,
                "generatedQueries": len(analysis["sample_docs"][:12]),
                "failures": failures,
            }
        )
    finally:
        await es_svc.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DOMAIN_QUERIES = {
    "security": [
        "critical remote code execution vulnerability",
        "privilege escalation exploit",
        "zero day advisory",
        "ransomware indicators of compromise",
        "patch tuesday high severity",
    ],
    "developer_docs": [
        "authentication api example",
        "rate limiting configuration",
        "error handling best practices",
        "sdk installation quickstart",
        "webhook payload format",
    ],
    "compliance": [
        "gdpr data retention policy",
        "access control audit log",
        "encryption at rest requirements",
        "third party vendor assessment",
        "incident response procedure",
    ],
    "general": [
        "getting started guide",
        "configuration reference",
        "troubleshooting common errors",
        "performance tuning tips",
        "release notes latest version",
    ],
}

_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "by",
    "for",
    "from",
    "how",
    "in",
    "into",
    "of",
    "on",
    "or",
    "the",
    "to",
    "with",
}


def _build_heuristic_eval_set(
    docs: List[dict],
    text_fields: List[str],
    domain: str,
) -> List[EvalCase]:
    """Build deterministic eval cases from sampled documents before falling back to generic prompts."""
    cases: List[EvalCase] = []
    seen_queries: set[str] = set()

    for doc in docs[:24]:
        doc_id = str(doc.get("_id", "")).strip()
        if not doc_id:
            continue

        text_candidates = [
            str(doc.get(field, "")).strip()
            for field in text_fields[:4]
            if isinstance(doc.get(field), str) and str(doc.get(field, "")).strip()
        ]
        if not text_candidates:
            continue

        query = _derive_query_from_doc(text_candidates)
        if not query:
            continue

        normalized = query.lower()
        if normalized in seen_queries:
            continue
        seen_queries.add(normalized)

        difficulty = "easy" if len(query.split()) <= 4 else "medium"
        cases.append(
            EvalCase(
                id=f"heuristic_{len(cases):03d}",
                query=query,
                relevantDocIds=[doc_id],
                difficulty=difficulty,
                personaHint=domain,
            )
        )

        if len(cases) >= 12:
            break

    if len(cases) >= 6:
        return cases

    queries = _DOMAIN_QUERIES.get(domain, _DOMAIN_QUERIES["general"])
    fallback_doc_ids = [str(d.get("_id", "")) for d in docs if d.get("_id")][:2]
    for query in queries:
        normalized = query.lower()
        if normalized in seen_queries:
            continue
        cases.append(
            EvalCase(
                id=f"heuristic_{len(cases):03d}",
                query=query,
                relevantDocIds=fallback_doc_ids,
                difficulty="medium",
                personaHint=domain,
            )
        )
        if len(cases) >= 10:
            break

    return cases


def _derive_query_from_doc(text_candidates: List[str]) -> str:
    title = text_candidates[0]
    title_tokens = _meaningful_tokens(title)
    if title_tokens:
        return " ".join(title_tokens[: min(5, len(title_tokens))])

    for body in text_candidates[1:]:
        body_tokens = _meaningful_tokens(body)
        if body_tokens:
            return " ".join(body_tokens[: min(6, len(body_tokens))])

    return ""


def _meaningful_tokens(value: str) -> List[str]:
    tokens = re.findall(r"[a-zA-Z0-9][a-zA-Z0-9._-]*", value.lower())
    cleaned: List[str] = []
    for token in tokens:
        if len(token) < 3:
            continue
        if token in _STOPWORDS:
            continue
        if token.isdigit():
            continue
        cleaned.append(token)
    return cleaned
