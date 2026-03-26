from pydantic import BaseModel
from typing import Optional, List, Any
from .contracts import ConnectionSummary, SearchProfile, SearchProfileChange, ExperimentRecord, CompressionSummary


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


class ReportPayload(BaseModel):
    runId: str
    generatedAt: str
    mode: str
    summary: ReportSummary
    connection: ConnectionSummary
    searchProfileBefore: SearchProfile
    searchProfileAfter: SearchProfile
    diff: List[SearchProfileChange]
    personaImpact: List[PersonaImpactRow]
    experiments: List[ExperimentRecord]
    compression: CompressionSummary
    warnings: List[str] = []
