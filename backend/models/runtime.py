from __future__ import annotations
import asyncio
from typing import Optional, List, Dict, Any
from .contracts import (
    RunMode,
    RunStage,
    ConnectionSummary,
    SearchProfile,
    HeroMetrics,
    PersonaViewModel,
    ExperimentRecord,
    CompressionSummary,
    LlmConfig,
    EvalCase,
)
from .report import ReportPayload


class ConnectionContext:
    def __init__(
        self,
        connection_id: str,
        mode: RunMode,
        summary: ConnectionSummary,
        eval_set: List[EvalCase],
        baseline_profile: SearchProfile,
        llm_config: Optional[LlmConfig] = None,
        es_url: Optional[str] = None,
        api_key: Optional[str] = None,
        index_name: Optional[str] = None,
        text_fields: Optional[List[str]] = None,
        sample_docs: Optional[List[Dict[str, Any]]] = None,
    ):
        self.connection_id = connection_id
        self.mode = mode
        self.summary = summary
        self.eval_set = eval_set
        self.baseline_profile = baseline_profile
        self.llm_config = llm_config
        self.es_url = es_url
        self.api_key = api_key
        self.index_name = index_name or summary.indexName
        self.text_fields = text_fields or list(summary.primaryTextFields)
        self.sample_docs = sample_docs or []


class RunContext:
    def __init__(
        self,
        run_id: str,
        connection: ConnectionContext,
        personas: List[PersonaViewModel],
        max_experiments: int = 60,
        duration_minutes: int = 30,
        auto_stop_on_plateau: bool = True,
    ):
        self.run_id = run_id
        self.mode = connection.mode
        self.stage: RunStage = "starting"
        self.summary = connection.summary
        self.eval_set = connection.eval_set
        self.llm_config = connection.llm_config
        self.es_url = connection.es_url
        self.api_key = connection.api_key
        self.index_name = connection.index_name
        self.text_fields = connection.text_fields
        self.sample_docs = connection.sample_docs
        self.current_profile: SearchProfile = connection.baseline_profile.model_copy(
            deep=True
        )
        self.best_profile: SearchProfile = connection.baseline_profile.model_copy(
            deep=True
        )
        self.baseline_profile: SearchProfile = connection.baseline_profile.model_copy(
            deep=True
        )
        self.metrics: HeroMetrics = HeroMetrics()
        self.personas: List[PersonaViewModel] = personas
        self.experiments: List[ExperimentRecord] = []
        self.compression: CompressionSummary = CompressionSummary()
        self.warnings: List[str] = []
        self.max_experiments = max_experiments
        self.duration_minutes = duration_minutes
        self.auto_stop_on_plateau = auto_stop_on_plateau
        self.cancel_flag = asyncio.Event()
        self.tasks: List[asyncio.Task] = []
        self.report: Optional[ReportPayload] = None
        self.started_at: Optional[str] = None
        self.completed_at: Optional[str] = None
        self.best_score: float = 0.0
        self._current_query_failures: List[str] = []
        self.previous_run_id: Optional[str] = (
            None  # Set when continuing from a previous run
        )
        self.prior_experiments: List[ExperimentRecord] = []
        self.original_baseline_score: Optional[float] = (
            None  # From the very first run in chain
        )
        self.prior_experiments_run: int = (
            0  # Cumulative experiment count from prior runs
        )
        self.prior_improvements_kept: int = 0  # Cumulative kept count from prior runs
        self.per_query_scores: Dict[
            str, Dict[str, float]
        ] = {}  # {queryId: {"baseline": x, "best": y}}
        self.per_query_results: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
