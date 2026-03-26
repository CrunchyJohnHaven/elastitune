from pydantic import BaseModel
from typing import Optional, List
from .contracts import (
    CompressionSummary,
    ConnectionSummary,
    EvalCase,
    ExperimentRecord,
    LlmConfig,
    SearchProfile,
    SearchProfileChange,
)


class QueryBreakdownRow(BaseModel):
    class ResultPreview(BaseModel):
        docId: str
        title: str
        excerpt: str = ""
        score: float = 0.0

    queryId: str
    query: str
    difficulty: str = "medium"
    baselineScore: float
    bestScore: float
    deltaPct: float
    failureReason: Optional[str] = None
    topRelevantDocIds: List[str] = []
    baselineTopResults: List[ResultPreview] = []
    bestTopResults: List[ResultPreview] = []


class PersonaImpactRow(BaseModel):
    personaId: str
    name: str
    role: str
    beforeSuccessRate: float
    afterSuccessRate: float
    deltaPct: float


class ReportSummary(BaseModel):
    headline: str
    overview: str
    nextSteps: List[str]
    baselineScore: float
    bestScore: float
    improvementPct: float
    experimentsRun: int
    improvementsKept: int
    durationSeconds: float = 0.0
    projectedMonthlySavingsUsd: Optional[float] = None
    # Continuation tracking — populated when this run continued from a previous one
    isContinuation: bool = False
    originalBaselineScore: Optional[float] = None
    totalExperimentsRun: Optional[int] = None  # Cumulative across all runs in the chain
    totalImprovementsKept: Optional[int] = (
        None  # Cumulative across all runs in the chain
    )


class ReportConnectionConfig(BaseModel):
    mode: str
    esUrl: Optional[str] = None
    apiKey: Optional[str] = None
    hasApiKey: bool = False
    indexName: Optional[str] = None
    evalSet: List[EvalCase] = []
    llm: Optional[LlmConfig] = None

    def sanitize_for_client(self) -> "ReportConnectionConfig":
        return self.model_copy(
            update={
                "apiKey": None,
                "hasApiKey": self.hasApiKey or bool(self.apiKey),
                "llm": self.llm.sanitize_for_client() if self.llm else None,
            }
        )


class ReportPayload(BaseModel):
    runId: str
    generatedAt: str
    mode: str
    summary: ReportSummary
    connection: ConnectionSummary
    connectionConfig: Optional[ReportConnectionConfig] = None
    searchProfileBefore: SearchProfile
    searchProfileAfter: SearchProfile
    diff: List[SearchProfileChange]
    queryBreakdown: List[QueryBreakdownRow] = []
    personaImpact: List[PersonaImpactRow]
    experiments: List[ExperimentRecord]
    compression: CompressionSummary
    warnings: List[str] = []
    previousRunId: Optional[str] = (
        None  # Set when this run continued from a previous one
    )

    def sanitize_for_client(self) -> "ReportPayload":
        return self.model_copy(
            update={
                "connectionConfig": self.connectionConfig.sanitize_for_client()
                if self.connectionConfig
                else None
            },
            deep=True,
        )
