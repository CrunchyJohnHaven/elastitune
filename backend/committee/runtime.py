from __future__ import annotations

import asyncio
from typing import Dict, Optional, Tuple

from .industry_profiles import IndustryProfile
from ..models.contracts import LlmConfig, RunStage
from .models import (
    CommitteeDocument,
    CommitteeEvaluationMode,
    CommitteeMetrics,
    CommitteePersona,
    CommitteePersonaView,
    CommitteeReport,
    CommitteeScoreThresholds,
    CommitteeSummary,
    RewriteAttempt,
    SectionEvaluation,
)


class CommitteeConnectionContext:
    def __init__(
        self,
        connection_id: str,
        document: CommitteeDocument,
        personas: list[CommitteePersona],
        profile: IndustryProfile,
        evaluation_mode: CommitteeEvaluationMode,
        llm_config: Optional[LlmConfig] = None,
        warnings: Optional[list[str]] = None,
    ) -> None:
        self.connection_id = connection_id
        self.document = document
        self.personas = personas
        self.profile = profile
        self.evaluation_mode = evaluation_mode
        self.llm_config = llm_config
        self.warnings = warnings or []
        self.summary = CommitteeSummary(
            documentName=document.documentName,
            sourceType=document.sourceType,
            sectionsCount=len(document.sections),
            personasCount=len(personas),
            evaluationMode=evaluation_mode,
            industryProfileId=profile.id,
            industryLabel=profile.label,
        )


class CommitteeRunContext:
    def __init__(
        self,
        run_id: str,
        connection: CommitteeConnectionContext,
        persona_views: list[CommitteePersonaView],
        max_rewrites: int = 36,
        duration_minutes: int = 4,
        auto_stop_on_plateau: bool = True,
        do_no_harm_floor: float = -0.05,
        score_thresholds: Optional[CommitteeScoreThresholds] = None,
    ) -> None:
        self.run_id = run_id
        self.product_mode = "committee"
        self.stage: RunStage = "starting"
        self.summary = connection.summary
        self.evaluation_mode = connection.evaluation_mode
        self.llm_config = connection.llm_config
        self.profile = connection.profile
        self.document = connection.document.model_copy(deep=True)
        self.baseline_document = connection.document.model_copy(deep=True)
        self.best_document = connection.document.model_copy(deep=True)
        self.persona_definitions = connection.personas
        self.personas = persona_views
        self.metrics = CommitteeMetrics()
        self.rewrites: list[RewriteAttempt] = []
        self.warnings: list[str] = list(
            dict.fromkeys(
                list(connection.warnings) + list(connection.document.parseWarnings)
            )
        )
        self.max_rewrites = max_rewrites
        self.duration_minutes = duration_minutes
        self.auto_stop_on_plateau = auto_stop_on_plateau
        self.do_no_harm_floor = do_no_harm_floor
        self.score_thresholds = score_thresholds or CommitteeScoreThresholds()
        self.metrics.doNoHarmFloor = do_no_harm_floor
        self.cancel_flag = asyncio.Event()
        self.tasks: list[asyncio.Task] = []
        self.report: Optional[CommitteeReport] = None
        self.started_at: Optional[str] = None
        self.started_monotonic: Optional[float] = None
        self.completed_at: Optional[str] = None
        self.best_score: float = 0.0
        self.section_evaluations: Dict[Tuple[int, str], SectionEvaluation] = {}
        self.baseline_section_text: Dict[int, str] = {
            section.id: section.content for section in connection.document.sections
        }
