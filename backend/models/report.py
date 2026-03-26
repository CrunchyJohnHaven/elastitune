from pydantic import BaseModel
from typing import Optional, List, Any
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


class ReportConnectionConfig(BaseModel):
    mode: str
    esUrl: Optional[str] = None
    apiKey: Optional[str] = None
    indexName: Optional[str] = None
    evalSet: List[EvalCase] = []
    llm: Optional[LlmConfig] = None


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
    previousRunId: Optional[str] = None  # Set when this run continued from a previous one
