from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Any, Dict
from enum import Enum

RunMode = Literal['demo', 'live']
ProductMode = Literal['search', 'committee']
RunStage = Literal['idle', 'analyzing', 'ready', 'starting', 'running', 'stopping', 'completed', 'error']
PersonaState = Literal['idle', 'searching', 'success', 'partial', 'failure', 'reacting']
ExperimentDecision = Literal['kept', 'reverted']


class LlmConfig(BaseModel):
    provider: Literal['openai_compatible', 'openai', 'anthropic', 'disabled'] = 'disabled'
    baseUrl: Optional[str] = None
    model: Optional[str] = None
    apiKey: Optional[str] = None


class EvalCase(BaseModel):
    id: str
    query: str
    relevantDocIds: List[str]
    personaHint: Optional[str] = None
    difficulty: Optional[Literal['easy', 'medium', 'hard']] = None


class ConnectRequest(BaseModel):
    mode: RunMode
    esUrl: Optional[str] = None
    apiKey: Optional[str] = None
    indexName: Optional[str] = None
    llm: Optional[LlmConfig] = None
    uploadedEvalSet: Optional[List[EvalCase]] = None
    autoGenerateEval: bool = True
    vectorFieldOverride: Optional[str] = None
    maxSampleDocs: int = 120


class SampleDoc(BaseModel):
    id: str
    title: str
    excerpt: str
    fieldPreview: Dict[str, str]


class ConnectionSummary(BaseModel):
    clusterName: str
    clusterVersion: Optional[str] = None
    indexName: str
    docCount: int
    detectedDomain: Literal['security', 'developer_docs', 'compliance', 'general']
    primaryTextFields: List[str]
    vectorField: Optional[str] = None
    vectorDims: Optional[int] = None
    sampleDocs: List[SampleDoc] = []
    baselineEvalCount: int = 0
    baselineReady: bool = False


class ConnectResponse(BaseModel):
    connectionId: str
    productMode: ProductMode = 'search'
    mode: RunMode
    stage: RunStage
    summary: ConnectionSummary
    warnings: List[str] = []


class SearchProfile(BaseModel):
    lexicalFields: List[Dict[str, Any]] = []
    multiMatchType: Literal['best_fields', 'most_fields', 'cross_fields', 'phrase'] = 'best_fields'
    minimumShouldMatch: str = '75%'
    tieBreaker: float = 0.0
    phraseBoost: float = 0.0
    fuzziness: Literal['AUTO', '0'] = '0'
    useVector: bool = False
    vectorField: Optional[str] = None
    vectorWeight: float = 0.35
    lexicalWeight: float = 0.65
    fusionMethod: Literal['weighted_sum', 'rrf'] = 'weighted_sum'
    rrfRankConstant: int = 60
    knnK: int = 20
    numCandidates: int = 100


class SearchProfileChange(BaseModel):
    path: str
    before: Any
    after: Any
    label: str


class ExperimentRecord(BaseModel):
    experimentId: int
    timestamp: str
    hypothesis: str
    change: SearchProfileChange
    baselineScore: float
    candidateScore: float
    deltaAbsolute: float
    deltaPercent: float
    decision: ExperimentDecision
    durationMs: int
    queryFailuresBefore: List[str] = []
    queryFailuresAfter: List[str] = []


class PersonaDefinition(BaseModel):
    id: str
    name: str
    role: str
    department: str
    archetype: str
    goal: str
    orbit: int
    colorSeed: int
    queries: List[str]


class PersonaRuntime(BaseModel):
    id: str
    state: PersonaState = 'idle'
    lastQuery: Optional[str] = None
    lastResultRank: Optional[int] = None
    successRate: float = 0.0
    totalSearches: int = 0
    successes: int = 0
    partials: int = 0
    failures: int = 0
    angle: float = 0.0
    speed: float = 0.08
    radius: float = 120.0
    pulseUntil: Optional[float] = None
    reactUntil: Optional[float] = None


class PersonaViewModel(PersonaDefinition, PersonaRuntime):
    pass


class CompressionMethodResult(BaseModel):
    method: Literal['float32', 'int8', 'int4', 'rotated_int4']
    sizeBytes: int
    recallAt10: float
    estimatedMonthlyCostUsd: float
    sizeReductionPct: float
    status: Literal['pending', 'running', 'done', 'skipped', 'error'] = 'pending'
    note: Optional[str] = None


class CompressionSummary(BaseModel):
    available: bool = False
    vectorField: Optional[str] = None
    vectorDims: Optional[int] = None
    methods: List[CompressionMethodResult] = []
    bestRecommendation: Optional[str] = None
    projectedMonthlySavingsUsd: Optional[float] = None
    status: Literal['idle', 'running', 'done', 'skipped', 'error'] = 'idle'


class HeroMetrics(BaseModel):
    currentScore: float = 0.0
    baselineScore: float = 0.0
    bestScore: float = 0.0
    improvementPct: float = 0.0
    experimentsRun: int = 0
    improvementsKept: int = 0
    personaSuccessRate: float = 0.0
    elapsedSeconds: float = 0.0
    projectedMonthlySavingsUsd: Optional[float] = None
    scoreTimeline: List[Dict[str, float]] = []


class RunConfig(BaseModel):
    durationMinutes: int = 30
    maxExperiments: int = 200
    personaCount: int = 36
    autoStopOnPlateau: bool = True


class RunSnapshot(BaseModel):
    runId: str
    productMode: ProductMode = 'search'
    mode: RunMode
    stage: RunStage
    summary: ConnectionSummary
    searchProfile: SearchProfile
    recommendedProfile: SearchProfile
    metrics: HeroMetrics
    personas: List[PersonaViewModel] = []
    experiments: List[ExperimentRecord] = []
    compression: CompressionSummary
    warnings: List[str] = []
    runConfig: RunConfig = Field(default_factory=RunConfig)
    startedAt: Optional[str] = None
    completedAt: Optional[str] = None


class StartRunRequest(BaseModel):
    connectionId: str
    durationMinutes: int = 30
    maxExperiments: int = 200
    personaCount: int = 36
    autoStopOnPlateau: bool = True
    previousRunId: Optional[str] = None  # Resume from a previous run's best profile


class StartRunResponse(BaseModel):
    runId: str
    productMode: ProductMode = 'search'
    stage: RunStage


class StopRunResponse(BaseModel):
    runId: str
    productMode: ProductMode = 'search'
    stage: RunStage


# WebSocket event union type aliases (used as dicts in practice)
