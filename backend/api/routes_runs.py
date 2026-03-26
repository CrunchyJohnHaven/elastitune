from __future__ import annotations

import logging
import uuid
from typing import Optional

import orjson
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from ..engine.persona_generator import build_personas
from ..models.contracts import (
    ModelCompareRequest,
    ModelComparisonEntry,
    ModelComparisonResult,
    PersonaViewModel,
    RunSnapshot,
    StartRunRequest,
    StartRunResponse,
    StopRunResponse,
)
from ..models.runtime import RunContext
from ..services.report_service import ReportService
from ..services.run_manager import RunManager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["runs"])


def _get_run_manager(request: Request) -> RunManager:
    return request.app.state.run_manager


@router.post("/runs", response_model=StartRunResponse)
async def start_run(body: StartRunRequest, request: Request) -> StartRunResponse:
    """Create and start a new optimization run for the given connection."""
    run_manager: RunManager = _get_run_manager(request)

    conn_ctx = await run_manager.get_connection(body.connectionId)
    if not conn_ctx:
        raise HTTPException(
            status_code=404,
            detail=f"Connection '{body.connectionId}' not found. Call /connect first.",
        )

    run_id = str(uuid.uuid4())
    previous_best_profile = None
    previous_experiments = []
    original_baseline_score: float | None = None
    prior_experiments_run = 0
    prior_improvements_kept = 0

    if body.previousRunId:
        prev_ctx = await run_manager.get_run(body.previousRunId)
        if prev_ctx and prev_ctx.best_profile:
            previous_best_profile = prev_ctx.best_profile.model_copy(deep=True)
            previous_experiments = list(prev_ctx.experiments)
            original_baseline_score = (
                prev_ctx.original_baseline_score
                if prev_ctx.original_baseline_score is not None
                else prev_ctx.metrics.baselineScore
            )
            prior_experiments_run = (
                prev_ctx.prior_experiments_run + prev_ctx.metrics.experimentsRun
            )
            prior_improvements_kept = (
                prev_ctx.prior_improvements_kept + prev_ctx.metrics.improvementsKept
            )
            logger.info(
                "Continuing from run %s with original baseline %.4f after %d prior experiments",
                body.previousRunId,
                original_baseline_score or 0.0,
                prior_experiments_run,
            )
        else:
            prev_report = await run_manager.get_report(body.previousRunId)
            if prev_report and prev_report.searchProfileAfter:
                previous_best_profile = prev_report.searchProfileAfter.model_copy(
                    deep=True
                )
                previous_experiments = list(prev_report.experiments)
                original_baseline_score = (
                    prev_report.summary.baselineScore if prev_report.summary else None
                )
                prior_experiments_run = len(prev_report.experiments)
                prior_improvements_kept = sum(
                    1
                    for experiment in prev_report.experiments
                    if experiment.decision == "kept"
                )

    personas: list[PersonaViewModel] = await build_personas(
        persona_count=body.personaCount,
        mode=conn_ctx.mode,
        domain=conn_ctx.summary.detectedDomain,
        sample_docs=conn_ctx.sample_docs,
        text_fields=conn_ctx.text_fields,
        llm_config=conn_ctx.llm_config,
    )

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
        run_ctx.original_baseline_score = original_baseline_score
        run_ctx.prior_experiments_run = prior_experiments_run
        run_ctx.prior_improvements_kept = prior_improvements_kept

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
    run_manager: RunManager = _get_run_manager(request)
    runs = await run_manager.list_search_runs(
        limit=min(limit, 200),
        index_name=indexName,
        completed_only=completedOnly,
    )
    return JSONResponse(content={"runs": runs})


@router.post("/runs/{run_id}/stop", response_model=StopRunResponse)
async def stop_run(run_id: str, request: Request) -> StopRunResponse:
    run_manager: RunManager = _get_run_manager(request)
    ctx = await run_manager.get_run(run_id)
    if not ctx:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    await run_manager.stop_run(run_id)
    return StopRunResponse(runId=run_id, stage="stopping")


@router.get("/runs/{run_id}/report")
async def get_report(run_id: str, request: Request) -> JSONResponse:
    run_manager: RunManager = _get_run_manager(request)
    ctx = await run_manager.get_run(run_id)
    if not ctx:
        persisted = await run_manager.get_report(run_id)
        if not persisted:
            raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
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
        ctx.report = persisted or await ReportService().generate_async(ctx)

    return JSONResponse(
        content=orjson.loads(ctx.report.model_dump_json()),
        media_type="application/json",
    )


@router.get("/runs/{run_id}/preview-query")
async def preview_query(run_id: str, queryId: str, request: Request) -> JSONResponse:
    """Return result previews and query DSL for one eval query."""
    run_manager: RunManager = _get_run_manager(request)
    ctx = await run_manager.get_run(run_id)
    report = await run_manager.get_report(run_id)
    if ctx is None and report is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    if report is None and ctx and ctx.report:
        report = ctx.report
    if report is None:
        raise HTTPException(
            status_code=404, detail=f"Report for run '{run_id}' not found"
        )

    query_row = next(
        (row for row in report.queryBreakdown if row.queryId == queryId), None
    )
    if query_row is None:
        raise HTTPException(
            status_code=404, detail=f"Query '{queryId}' not found in report"
        )

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
            logger.warning(
                "Preview query fallback for run %s query %s: %s",
                run_id,
                queryId,
                exc,
            )

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


@router.post("/model-compare", response_model=ModelComparisonResult)
async def start_model_comparison(
    req: ModelCompareRequest, request: Request
) -> ModelComparisonResult:
    """Evaluate the baseline profile with each provided model and return a ranked comparison."""
    run_manager: RunManager = _get_run_manager(request)

    conn_ctx = await run_manager.get_connection(req.connectionId)
    if not conn_ctx:
        raise HTTPException(
            status_code=404,
            detail=f"Connection '{req.connectionId}' not found. Call /connect first.",
        )

    from ..services.es_service import ESService
    from ..services.task_runner import SearchTaskRunner

    task_runner = SearchTaskRunner(run_manager)
    entries: list[ModelComparisonEntry] = []

    for model_id in req.modelIds:
        # Clone baseline profile and set modelId
        profile = conn_ctx.baseline_profile.model_copy(deep=True)
        profile.modelId = model_id

        # Build a lightweight RunContext-like object using the connection context
        # We use a minimal RunContext so evaluate_profile can run
        from ..models.runtime import RunContext

        tmp_ctx = RunContext(
            run_id=f"model-compare-{model_id}",
            connection=conn_ctx,
            personas=[],
            max_experiments=0,
            duration_minutes=0,
            auto_stop_on_plateau=False,
        )

        score = 0.0
        es_svc = None
        try:
            if conn_ctx.es_url:
                es_svc = ESService(
                    es_url=conn_ctx.es_url, api_key=conn_ctx.api_key or None
                )
            score, _failures, _per_query = await task_runner.evaluate_profile(
                tmp_ctx, profile, es_svc=es_svc
            )
        except Exception as exc:
            logger.warning("Model comparison evaluation failed for model %s: %s", model_id, exc)
        finally:
            if es_svc is not None:
                await es_svc.close()

        entries.append(
            ModelComparisonEntry(
                modelId=model_id,
                baselineScore=score,
                bestScore=score,
                improvementPct=0.0,
                experimentsRun=0,
                improvementsKept=0,
                bestProfile=profile,
                topChanges=[],
            )
        )

    # Sort by bestScore descending
    entries.sort(key=lambda e: e.bestScore, reverse=True)

    recommended_model: Optional[str] = entries[0].modelId if entries else None

    if len(entries) == 0:
        comparison_note = "No models were evaluated."
    elif len(entries) == 1:
        comparison_note = (
            f"Only one model evaluated: {entries[0].modelId} scored {entries[0].bestScore:.4f}."
        )
    else:
        top = entries[0]
        runner_up = entries[1]
        gap = top.bestScore - runner_up.bestScore
        comparison_note = (
            f"{top.modelId} achieved the highest baseline nDCG@10 of {top.bestScore:.4f}, "
            f"outperforming {runner_up.modelId} ({runner_up.bestScore:.4f}) by {gap:.4f}. "
            f"Run a full optimization using the recommended model for best results."
        )

    return ModelComparisonResult(
        entries=entries,
        recommendedModel=recommended_model,
        comparisonNote=comparison_note,
    )
