from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import AliasChoices, BaseModel, Field

RunMode = Literal["demo", "live"]
ProductMode = Literal["search", "committee"]
RunStage = Literal[
    "idle",
    "analyzing",
    "ready",
    "starting",
    "running",
    "stopping",
    "completed",
    "error",
]
PersonaState = Literal["idle", "searching", "success", "partial", "failure", "reacting"]
ExperimentDecision = Literal["kept", "reverted"]


class LlmConfig(BaseModel):
    provider: Literal["openai_compatible", "openai", "anthropic", "disabled"] = (
        "disabled"
    )
    baseUrl: Optional[str] = None
    model: Optional[str] = None
    apiKey: Optional[str] = None

    def sanitize_for_client(self) -> "LlmConfig":
        return self.model_copy(update={"apiKey": None})


class LexicalFieldEntry(BaseModel):
    field: str
    boost: float = 1.0

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


class EvalCase(BaseModel):
    id: str
    query: str
    relevantDocIds: List[str]
    personaHint: Optional[str] = None
    difficulty: Optional[Literal["easy", "medium", "hard"]] = None


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
    detectedDomain: Literal["security", "developer_docs", "compliance", "general"]
    primaryTextFields: List[str]
    vectorField: Optional[str] = None
    vectorDims: Optional[int] = None
    sampleDocs: List[SampleDoc] = []
    baselineEvalCount: int = 0
    baselineReady: bool = False


class ConnectResponse(BaseModel):
    connectionId: str
    productMode: ProductMode = "search"
    mode: RunMode
    stage: RunStage
    summary: ConnectionSummary
    warnings: List[str] = []


class SearchProfile(BaseModel):
    lexicalFields: List[LexicalFieldEntry] = Field(default_factory=list)
    multiMatchType: Literal["best_fields", "most_fields", "cross_fields", "phrase"] = (
        "best_fields"
    )
    minimumShouldMatch: str = "75%"
    tieBreaker: float = 0.0
    phraseBoost: float = 0.0
    fuzziness: Literal["AUTO", "0"] = "0"
    useVector: bool = False
    vectorField: Optional[str] = None
    vectorWeight: float = 0.35
    lexicalWeight: float = 0.65
    fusionMethod: Literal["weighted_sum", "rrf"] = "weighted_sum"
    rrfRankConstant: int = 60
    knnK: int = 20
    numCandidates: int = 100
    modelId: Optional[str] = None  # Elasticsearch model_id for query_vector_builder (e.g. ".elser_model_2", ".multilingual-e5-small")


class SearchProfileChange(BaseModel):
    path: str
    before: str | int | float | bool | None
    after: str | int | float | bool | None
    label: str


class ExperimentRecord(BaseModel):
    experimentId: int
    timestamp: str
    hypothesis: str
    change: SearchProfileChange
    beforeScore: float = Field(
        validation_alias=AliasChoices("beforeScore", "baselineScore"),
        serialization_alias="beforeScore",
    )
    candidateScore: float
    deltaAbsolute: float
    deltaPercent: float
    decision: ExperimentDecision
    durationMs: int
    queryFailuresBefore: List[str] = []
    queryFailuresAfter: List[str] = []

    @property
    def baselineScore(self) -> float:
        return self.beforeScore


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
    state: PersonaState = "idle"
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
    method: Literal["float32", "int8", "int4", "rotated_int4"]
    sizeBytes: int
    recallAt10: float
    estimatedMonthlyCostUsd: float
    sizeReductionPct: float
    status: Literal["pending", "running", "done", "skipped", "error"] = "pending"
    note: Optional[str] = None


class CompressionSummary(BaseModel):
    available: bool = False
    vectorField: Optional[str] = None
    vectorDims: Optional[int] = None
    methods: List[CompressionMethodResult] = []
    bestRecommendation: Optional[str] = None
    projectedMonthlySavingsUsd: Optional[float] = None
    status: Literal["idle", "running", "done", "skipped", "error"] = "idle"


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
    scoreTimeline: List[Dict[str, float]] = []  # Each entry: {"t": float, "score": float}
    # Continuation tracking — cumulative progress across run chain
    originalBaselineScore: Optional[float] = (
        None  # Score from the very first run in chain
    )
    priorExperimentsRun: int = 0  # Total experiments from all previous runs
    priorImprovementsKept: int = 0  # Total kept from all previous runs


class RunConfig(BaseModel):
    durationMinutes: int = 30
    maxExperiments: int = 200
    personaCount: int = 36
    autoStopOnPlateau: bool = True


class RunSnapshot(BaseModel):
    runId: str
    productMode: ProductMode = "search"
    mode: RunMode
    stage: RunStage
    summary: ConnectionSummary
    searchProfile: SearchProfile
    recommendedProfile: SearchProfile
    metrics: HeroMetrics
    personas: List[PersonaViewModel] = Field(default_factory=list)
    experiments: List[ExperimentRecord] = Field(default_factory=list)
    compression: CompressionSummary
    warnings: List[str] = Field(default_factory=list)
    runConfig: RunConfig = Field(default_factory=RunConfig)
    startedAt: Optional[str] = None
    completedAt: Optional[str] = None

    def sanitize_for_client(self) -> "RunSnapshot":
        return self.model_copy(deep=True)


class StartRunRequest(BaseModel):
    connectionId: str
    durationMinutes: int = 30
    maxExperiments: int = 200
    personaCount: int = 36
    autoStopOnPlateau: bool = True
    previousRunId: Optional[str] = None  # Resume from a previous run's best profile


class StartRunResponse(BaseModel):
    runId: str
    productMode: ProductMode = "search"
    stage: RunStage


class StopRunResponse(BaseModel):
    runId: str
    productMode: ProductMode = "search"
    stage: RunStage


class ModelCompareRequest(BaseModel):
    connectionId: str
    modelIds: List[str]  # e.g. [".elser_model_2", ".multilingual-e5-small"]
    maxExperimentsPerModel: int = 10


class ModelComparisonEntry(BaseModel):
    modelId: str
    baselineScore: float
    bestScore: float
    improvementPct: float
    experimentsRun: int
    improvementsKept: int
    bestProfile: SearchProfile
    topChanges: List[str] = []


class ModelComparisonResult(BaseModel):
    entries: List[ModelComparisonEntry] = []
    recommendedModel: Optional[str] = None
    comparisonNote: str = ""


# WebSocket event union type aliases (used as dicts in practice)
