from __future__ import annotations

import json
import logging
import uuid
from typing import List, Optional

import orjson
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from ..config import settings
from ..committee.document_parser import parse_document_bytes
from ..committee.models import (
    CommitteeConnectionResponse,
    CommitteePersona,
    CommitteeRunListItem,
    StartCommitteeRunRequest,
    StartCommitteeRunResponse,
    StopCommitteeRunResponse,
)
from ..committee.personas import build_committee_personas
from ..committee.runtime import CommitteeConnectionContext, CommitteeRunContext
from ..services.llm_service import LLMService
from ..services.run_manager import RunManager
from ..models.contracts import LlmConfig

logger = logging.getLogger(__name__)

router = APIRouter(tags=["committee"])


def _get_run_manager(request: Request) -> RunManager:
    return request.app.state.run_manager


def _apply_persona_weighting(
    personas: List[CommitteePersona],
    weighting_mode: str,
) -> List[CommitteePersona]:
    if not personas:
        return personas
    if weighting_mode == "balanced":
        weight = round(1.0 / len(personas), 4)
        return [persona.model_copy(update={"authorityWeight": weight}) for persona in personas]
    if weighting_mode == "skeptic_priority":
        weighted = [
            max(persona.authorityWeight, 0.05) * (1.0 + persona.skepticismLevel / 10)
            for persona in personas
        ]
    else:
        weighted = [max(persona.authorityWeight, 0.05) for persona in personas]
    total = sum(weighted) or 1.0
    return [
        persona.model_copy(update={"authorityWeight": round(weight / total, 4)})
        for persona, weight in zip(personas, weighted)
    ]


@router.post("/committee/connect", response_model=CommitteeConnectionResponse)
async def connect_committee(
    request: Request,
    document: UploadFile = File(...),
    evaluationMode: str = Form("full_committee"),
    useSeedPersonas: bool = Form(True),
    committeeDescription: Optional[str] = Form(None),
    industryProfileId: Optional[str] = Form(None),
    personasJson: Optional[str] = Form(None),
    llmJson: Optional[str] = Form(None),
) -> CommitteeConnectionResponse:
    run_manager = _get_run_manager(request)
    connection_id = str(uuid.uuid4())
    warnings: List[str] = []

    filename = document.filename or "committee_document"
    payload = await document.read()
    if not payload:
        raise HTTPException(status_code=422, detail="Uploaded document was empty")
    if len(payload) > settings.max_committee_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Uploaded document exceeds the {settings.max_committee_upload_bytes // (1024 * 1024)} MB safety limit"
            ),
        )

    try:
        parsed_document = parse_document_bytes(filename, payload)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Document parsing failed: {exc}")
    warnings.extend(parsed_document.parseWarnings)

    llm_config: Optional[LlmConfig] = None
    if llmJson:
        try:
            llm_config = LlmConfig(**json.loads(llmJson))
        except Exception as exc:
            warnings.append(f"Invalid LLM config ignored: {exc}")

    provided_personas: Optional[List[CommitteePersona]] = None
    if personasJson:
        try:
            provided_personas = [
                CommitteePersona(**item) for item in json.loads(personasJson)
            ]
        except Exception as exc:
            raise HTTPException(
                status_code=422, detail=f"Invalid personasJson payload: {exc}"
            )

    llm_service = (
        LLMService(llm_config)
        if llm_config and llm_config.provider != "disabled"
        else None
    )
    persona_build = await build_committee_personas(
        document=parsed_document,
        committee_description=committeeDescription,
        provided_personas=provided_personas,
        use_seed_personas=useSeedPersonas,
        llm_service=llm_service,
        industry_profile_id=industryProfileId,
    )
    personas = persona_build.personas
    warnings.extend(persona_build.warnings)

    ctx = CommitteeConnectionContext(
        connection_id=connection_id,
        document=parsed_document,
        personas=personas,
        profile=persona_build.profile,
        evaluation_mode=evaluationMode,  # type: ignore[arg-type]
        llm_config=llm_config,
        warnings=warnings,
    )
    await run_manager.create_committee_connection(connection_id, ctx)

    return CommitteeConnectionResponse(
        connectionId=connection_id,
        stage="ready",
        summary=ctx.summary,
        document=parsed_document,
        personas=personas,
        warnings=warnings,
    )


@router.post("/committee/runs", response_model=StartCommitteeRunResponse)
async def start_committee_run(
    body: StartCommitteeRunRequest,
    request: Request,
) -> StartCommitteeRunResponse:
    run_manager = _get_run_manager(request)
    conn_ctx = await run_manager.get_committee_connection(body.connectionId)
    if not conn_ctx:
        raise HTTPException(status_code=404, detail="Committee connection not found")

    run_id = str(uuid.uuid4())
    weighted_personas = _apply_persona_weighting(
        conn_ctx.personas,
        body.personaWeightingMode,
    )
    persona_views = []
    for persona in weighted_personas:
        persona_views.append(
            {
                "id": persona.id,
                "name": persona.name,
                "title": persona.title,
                "roleInDecision": persona.roleInDecision,
                "authorityWeight": persona.authorityWeight,
                "skepticismLevel": persona.skepticismLevel,
                "sentiment": "neutral",
                "currentScore": 0.0,
                "supportScore": 0.0,
                "reactionQuote": "",
                "topObjection": None,
                "riskFlags": [],
                "missing": [],
                "perSection": [],
                "priorities": persona.priorities,
                "concerns": persona.concerns,
            }
        )

    run_ctx = CommitteeRunContext(
        run_id=run_id,
        connection=conn_ctx,
        persona_views=persona_views,  # type: ignore[arg-type]
        max_rewrites=body.maxRewrites,
        duration_minutes=body.durationMinutes,
        auto_stop_on_plateau=body.autoStopOnPlateau,
        do_no_harm_floor=body.doNoHarmFloor,
        persona_weighting_mode=body.personaWeightingMode,
        reaction_memory_weight=body.reactionMemoryWeight,
        score_thresholds=body.scoreThresholds,
    )
    run_ctx.persona_definitions = weighted_personas
    await run_manager.create_committee_run(run_id, run_ctx)
    await run_manager.start_committee_run_tasks(run_id)

    return StartCommitteeRunResponse(runId=run_id, stage="starting")


@router.get("/committee/runs")
async def list_committee_runs(
    request: Request,
    limit: int = 50,
    industryProfileId: Optional[str] = None,
    completedOnly: bool = False,
) -> JSONResponse:
    run_manager = _get_run_manager(request)
    runs = await run_manager.list_committee_runs(
        limit=min(limit, 200),
        industry_profile_id=industryProfileId,
        completed_only=completedOnly,
    )
    return JSONResponse(
        content={
            "runs": [
                CommitteeRunListItem(**run).model_dump()
                for run in runs
            ]
        }
    )


@router.get("/committee/runs/{run_id}")
async def get_committee_run(run_id: str, request: Request) -> JSONResponse:
    run_manager = _get_run_manager(request)
    snapshot = await run_manager.get_committee_snapshot(run_id)
    if not snapshot:
        raise HTTPException(
            status_code=404, detail=f"Committee run '{run_id}' not found"
        )
    return JSONResponse(content=orjson.loads(snapshot.model_dump_json()))


@router.post("/committee/runs/{run_id}/stop", response_model=StopCommitteeRunResponse)
async def stop_committee_run(run_id: str, request: Request) -> StopCommitteeRunResponse:
    run_manager = _get_run_manager(request)
    ctx = await run_manager.get_committee_run(run_id)
    if not ctx:
        raise HTTPException(
            status_code=404, detail=f"Committee run '{run_id}' not found"
        )
    await run_manager.stop_committee_run(run_id)
    return StopCommitteeRunResponse(runId=run_id, stage="stopping")


@router.get("/committee/runs/{run_id}/report")
async def get_committee_report(run_id: str, request: Request) -> JSONResponse:
    run_manager = _get_run_manager(request)
    ctx = await run_manager.get_committee_run(run_id)
    if not ctx:
        persisted = await run_manager.get_committee_report(run_id)
        if not persisted:
            raise HTTPException(
                status_code=404, detail=f"Committee run '{run_id}' not found"
            )
        return JSONResponse(content=orjson.loads(persisted.model_dump_json()))
    if ctx.report is None:
        if ctx.stage not in ("completed", "stopping", "error"):
            raise HTTPException(status_code=409, detail="Committee run is still active")
        from ..committee.reporting import build_report_async

        ctx.report = await build_report_async(ctx)

    return JSONResponse(content=orjson.loads(ctx.report.model_dump_json()))


@router.get("/committee/runs/{run_id}/export")
async def get_committee_export(run_id: str, request: Request) -> JSONResponse:
    run_manager = _get_run_manager(request)
    payload = await run_manager.get_committee_export(run_id)
    if payload is None:
        raise HTTPException(
            status_code=404, detail=f"Committee run '{run_id}' not found"
        )
    return JSONResponse(content=payload)
