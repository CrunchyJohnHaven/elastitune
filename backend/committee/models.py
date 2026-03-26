from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from ..models.contracts import LlmConfig, RunStage

CommitteeProductMode = Literal["committee"]
CommitteeDecision = Literal["kept", "reverted"]
CommitteeSentiment = Literal["supportive", "cautiously_interested", "neutral", "skeptical", "opposed"]
CommitteeEmotion = Literal["positive", "neutral", "negative"]
CommitteeEvaluationMode = Literal["full_committee", "adversarial", "champion_only"]
CommitteeEvaluationSource = Literal["llm", "heuristic", "mixed"]
CommitteeParseMode = Literal["native", "compatibility", "fallback"]


class DocumentSection(BaseModel):
    id: int
    title: str
    content: str
    type: str = "content"
    slideRefs: List[int] = []
    stats: List[str] = []
    claims: List[str] = []
    proofPoints: List[str] = []
    cta: Optional[str] = None


class CommitteeDocument(BaseModel):
    documentId: str
    documentName: str
    sourceType: Literal["pdf", "pptx", "docx", "txt", "md", "unknown"] = "unknown"
    sections: List[DocumentSection]
    rawText: str = ""
    parseMode: CommitteeParseMode = "native"
    parseWarnings: List[str] = []


class CommitteePersona(BaseModel):
    id: str
    name: str
    title: str
    organization: str
    roleInDecision: str
    authorityWeight: float = 0.2
    priorities: List[str] = []
    concerns: List[str] = []
    decisionCriteria: List[str] = []
    likelyObjections: List[str] = []
    whatWinsThemOver: List[str] = []
    skepticismLevel: int = 5
    domainExpertise: Optional[str] = None
    politicalMotivations: List[str] = []


class SectionScoreBreakdown(BaseModel):
    relevance: float = 0.0
    persuasiveness: float = 0.0
    evidenceQuality: float = 0.0
    riskScore: float = 0.0
    completeness: float = 0.0


class SectionEvaluation(BaseModel):
    personaId: str
    sectionId: int
    sectionTitle: str
    scores: SectionScoreBreakdown
    riskFlags: List[str] = []
    missing: List[str] = []
    emotionalResponse: CommitteeEmotion = "neutral"
    reactionQuote: str = ""
    compositeScore: float = 0.0
    source: CommitteeEvaluationSource = "heuristic"
    confidence: float = 0.5


class PersonaSectionRollup(BaseModel):
    sectionId: int
    sectionTitle: str
    compositeScore: float
    reactionQuote: str
    riskFlags: List[str] = []
    missing: List[str] = []
    source: CommitteeEvaluationSource = "heuristic"
    confidence: float = 0.5


class CommitteePersonaView(BaseModel):
    id: str
    name: str
    title: str
    roleInDecision: str
    authorityWeight: float
    skepticismLevel: int
    sentiment: CommitteeSentiment = "neutral"
    currentScore: float = 0.0
    supportScore: float = 0.0
    reactionQuote: str = ""
    topObjection: Optional[str] = None
    riskFlags: List[str] = []
    missing: List[str] = []
    perSection: List[PersonaSectionRollup] = []
    priorities: List[str] = []
    concerns: List[str] = []
    evaluationSource: CommitteeEvaluationSource = "heuristic"
    evaluationConfidence: float = 0.5


class RewriteAttempt(BaseModel):
    experimentId: int
    timestamp: str
    sectionId: int
    sectionTitle: str
    parameterName: str
    oldValue: str
    newValue: str
    description: str
    baselineScore: float
    candidateScore: float
    deltaAbsolute: float
    deltaPercent: float
    decision: CommitteeDecision
    doNoHarmSatisfied: bool = True
    worstPersonaDrop: float = 0.0
    beforeText: str
    afterText: str
    personaDeltas: Dict[str, float] = {}
    durationMs: int = 0


class ScoreTimelinePoint(BaseModel):
    t: float
    score: float


class CommitteeMetrics(BaseModel):
    currentScore: float = 0.0
    baselineScore: float = 0.0
    bestScore: float = 0.0
    improvementPct: float = 0.0
    rewritesTested: int = 0
    acceptedRewrites: int = 0
    elapsedSeconds: float = 0.0
    scoreTimeline: List[ScoreTimelinePoint] = []
    currentSectionId: Optional[int] = None
    currentSectionTitle: Optional[str] = None
    aiEvaluations: int = 0
    heuristicEvaluations: int = 0
    llmCoveragePct: float = 0.0
    doNoHarmFloor: float = -0.05


class CommitteeSummary(BaseModel):
    documentName: str
    sourceType: str
    sectionsCount: int
    personasCount: int
    evaluationMode: CommitteeEvaluationMode
    industryProfileId: str = "general_enterprise"
    industryLabel: str = "General Enterprise"


class CommitteeConnectionResponse(BaseModel):
    connectionId: str
    productMode: CommitteeProductMode = "committee"
    stage: RunStage = "ready"
    summary: CommitteeSummary
    document: CommitteeDocument
    personas: List[CommitteePersona]
    warnings: List[str] = []


class CommitteeScoreThresholds(BaseModel):
    supportive: float = 0.72
    cautiouslyInterested: float = 0.58
    neutral: float = 0.45
    skeptical: float = 0.32
    positiveEmotion: float = 0.65
    enthusiasticQuote: float = 0.72
    cautiousQuote: float = 0.55


class CommitteeConnectPayload(BaseModel):
    evaluationMode: CommitteeEvaluationMode = "full_committee"
    useSeedPersonas: bool = True
    committeeDescription: Optional[str] = None
    industryProfileId: Optional[str] = None
    llm: Optional[LlmConfig] = None
    personas: Optional[List[CommitteePersona]] = None


class StartCommitteeRunRequest(BaseModel):
    connectionId: str
    durationMinutes: int = 4
    maxRewrites: int = 36
    autoStopOnPlateau: bool = True
    doNoHarmFloor: float = -0.05
    scoreThresholds: Optional[CommitteeScoreThresholds] = None


class StartCommitteeRunResponse(BaseModel):
    runId: str
    stage: RunStage
    productMode: CommitteeProductMode = "committee"


class StopCommitteeRunResponse(BaseModel):
    runId: str
    stage: RunStage
    productMode: CommitteeProductMode = "committee"


class CommitteeSnapshot(BaseModel):
    runId: str
    productMode: CommitteeProductMode = "committee"
    stage: RunStage
    summary: CommitteeSummary
    document: CommitteeDocument
    personas: List[CommitteePersonaView]
    rewrites: List[RewriteAttempt] = []
    metrics: CommitteeMetrics = Field(default_factory=CommitteeMetrics)
    evaluationMode: CommitteeEvaluationMode = "full_committee"
    warnings: List[str] = []
    startedAt: Optional[str] = None
    completedAt: Optional[str] = None


class CommitteeReportSummary(BaseModel):
    headline: str
    baselineScore: float
    bestScore: float
    improvementPct: float
    rewritesTested: int
    acceptedRewrites: int


class CommitteeReport(BaseModel):
    runId: str
    productMode: CommitteeProductMode = "committee"
    generatedAt: str
    summary: CommitteeReportSummary
    document: CommitteeDocument
    personas: List[CommitteePersonaView]
    rewrites: List[RewriteAttempt]
    evaluationMode: CommitteeEvaluationMode
    warnings: List[str] = []


class CommitteeSectionExport(BaseModel):
    sectionId: int
    title: str
    originalContent: str
    optimizedContent: str


class CommitteeExportPayload(BaseModel):
    documentName: str
    exportedAt: str
    committeeSummary: Dict[str, Any] = {}
    sections: List[CommitteeSectionExport]
    rewriteLog: List[RewriteAttempt]
    llmHandoff: Dict[str, Any] = {}
