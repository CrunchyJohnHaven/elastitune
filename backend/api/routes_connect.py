from __future__ import annotations

import logging
import re
import uuid
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request

from ..models.contracts import (
    ConnectRequest,
    ConnectResponse,
    ConnectionSummary,
    EvalCase,
    LlmConfig,
    RunStage,
    SampleDoc,
    SearchProfile,
)
from ..models.runtime import ConnectionContext
from ..services.run_manager import RunManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["connect"])


def _get_run_manager(request: Request) -> RunManager:
    return request.app.state.run_manager


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
        raise HTTPException(status_code=422, detail="indexName is required for live mode")

    from ..services.es_service import ESService
    from ..services.llm_service import LLMService

    es_svc = ESService(es_url=body.esUrl, api_key=body.apiKey or None)

    # Ping
    try:
        alive = await es_svc.ping()
        if not alive:
            raise HTTPException(status_code=502, detail="Cannot reach Elasticsearch cluster")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Elasticsearch connection failed: {exc}")

    # Cluster info
    cluster_info = await es_svc.get_cluster_info()
    cluster_name: str = cluster_info.get("cluster_name", "unknown")
    cluster_version: Optional[str] = (
        cluster_info.get("version", {}).get("number") if isinstance(cluster_info.get("version"), dict) else None
    )

    # Analyse index
    try:
        analysis = await es_svc.analyze_index(
            index=body.indexName,
            vector_field_override=body.vectorFieldOverride,
            max_sample_docs=body.maxSampleDocs,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Index analysis failed: {exc}")

    text_fields: List[str] = analysis["text_fields"]
    vector_field: Optional[str] = analysis["vector_field"]
    vector_dims: Optional[int] = analysis["vector_dims"]
    raw_docs: List = analysis["sample_docs"]
    domain = analysis["domain"]

    if not text_fields:
        warnings.append("No text fields detected in index mapping. Search quality may be limited.")

    doc_count = await es_svc.count_docs(body.indexName)

    # Build SampleDoc list
    sample_docs: List[SampleDoc] = []
    title_field = text_fields[0] if text_fields else "title"
    excerpt_field = text_fields[1] if len(text_fields) > 1 else text_fields[0] if text_fields else "description"

    for doc in raw_docs[:10]:
        doc_id = str(doc.get("_id", ""))
        title_val = str(doc.get(title_field, doc_id))[:100]
        excerpt_val = str(doc.get(excerpt_field, ""))[:300]
        field_preview = {
            f: str(doc.get(f, ""))[:100]
            for f in text_fields[:4]
            if f in doc
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

    # Build baseline SearchProfile
    profile_dict = await es_svc.build_baseline_profile(
        text_fields=text_fields,
        vector_field=vector_field,
    )
    baseline_profile = SearchProfile(**profile_dict)

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
