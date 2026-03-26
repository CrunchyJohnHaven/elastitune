export type CommitteeStage =
  | 'idle'
  | 'ready'
  | 'analyzing'
  | 'starting'
  | 'running'
  | 'stopping'
  | 'completed'
  | 'error';

export type CommitteeDecision = 'kept' | 'reverted';
export type CommitteeEvaluationMode = 'full_committee' | 'adversarial' | 'champion_only';
export type CommitteeEvaluationSource = 'llm' | 'heuristic' | 'mixed';
export interface CommitteeScoreThresholds {
  supportive: number;
  cautiouslyInterested: number;
  neutral: number;
  skeptical: number;
  positiveEmotion: number;
  enthusiasticQuote: number;
  cautiousQuote: number;
}
export type CommitteeSentiment =
  | 'supportive'
  | 'cautiously_interested'
  | 'neutral'
  | 'skeptical'
  | 'opposed';

export interface CommitteeSection {
  id: number;
  title: string;
  content: string;
  type: string;
  slideRefs: number[];
  stats: string[];
  claims: string[];
  proofPoints: string[];
  cta?: string | null;
}

export interface CommitteeDocument {
  documentId: string;
  documentName: string;
  sourceType: 'pdf' | 'pptx' | 'docx' | 'txt' | 'md' | 'unknown';
  sections: CommitteeSection[];
  rawText: string;
  parseMode: 'native' | 'compatibility' | 'fallback';
  parseWarnings: string[];
}

export interface CommitteePersona {
  id: string;
  name: string;
  title: string;
  organization: string;
  roleInDecision: string;
  authorityWeight: number;
  priorities: string[];
  concerns: string[];
  decisionCriteria: string[];
  likelyObjections: string[];
  whatWinsThemOver: string[];
  skepticismLevel: number;
  domainExpertise?: string | null;
  politicalMotivations?: string[];
}

export interface PersonaSectionRollup {
  sectionId: number;
  sectionTitle: string;
  compositeScore: number;
  reactionQuote: string;
  riskFlags: string[];
  missing: string[];
  source: CommitteeEvaluationSource;
  confidence: number;
}

export interface CommitteePersonaView {
  id: string;
  name: string;
  title: string;
  roleInDecision: string;
  authorityWeight: number;
  skepticismLevel: number;
  sentiment: CommitteeSentiment;
  currentScore: number;
  supportScore: number;
  reactionQuote: string;
  topObjection?: string | null;
  riskFlags: string[];
  missing: string[];
  perSection: PersonaSectionRollup[];
  priorities: string[];
  concerns: string[];
  evaluationSource: CommitteeEvaluationSource;
  evaluationConfidence: number;
}

export interface RewriteAttempt {
  experimentId: number;
  timestamp: string;
  sectionId: number;
  sectionTitle: string;
  parameterName: string;
  oldValue: string;
  newValue: string;
  description: string;
  baselineScore: number;
  candidateScore: number;
  deltaAbsolute: number;
  deltaPercent: number;
  decision: CommitteeDecision;
  doNoHarmSatisfied: boolean;
  worstPersonaDrop: number;
  beforeText: string;
  afterText: string;
  personaDeltas: Record<string, number>;
  durationMs: number;
}

export interface CommitteeMetrics {
  currentScore: number;
  baselineScore: number;
  bestScore: number;
  improvementPct: number;
  rewritesTested: number;
  acceptedRewrites: number;
  elapsedSeconds: number;
  scoreTimeline: Array<{ t: number; score: number }>;
  currentSectionId?: number | null;
  currentSectionTitle?: string | null;
  aiEvaluations: number;
  heuristicEvaluations: number;
  llmCoveragePct: number;
  doNoHarmFloor: number;
}

export interface CommitteeSummary {
  documentName: string;
  sourceType: string;
  sectionsCount: number;
  personasCount: number;
  evaluationMode: CommitteeEvaluationMode;
  industryProfileId: string;
  industryLabel: string;
}

export interface CommitteeConnectionResponse {
  connectionId: string;
  productMode: 'committee';
  stage: CommitteeStage;
  summary: CommitteeSummary;
  document: CommitteeDocument;
  personas: CommitteePersona[];
  warnings: string[];
}

export interface CommitteeSnapshot {
  runId: string;
  productMode: 'committee';
  stage: CommitteeStage;
  summary: CommitteeSummary;
  document: CommitteeDocument;
  personas: CommitteePersonaView[];
  rewrites: RewriteAttempt[];
  metrics: CommitteeMetrics;
  evaluationMode: CommitteeEvaluationMode;
  warnings: string[];
  startedAt?: string;
  completedAt?: string | null;
}

export interface CommitteeReport {
  runId: string;
  productMode: 'committee';
  generatedAt: string;
  summary: {
    headline: string;
    baselineScore: number;
    bestScore: number;
    improvementPct: number;
    rewritesTested: number;
    acceptedRewrites: number;
  };
  document: CommitteeDocument;
  personas: CommitteePersonaView[];
  rewrites: RewriteAttempt[];
  evaluationMode: CommitteeEvaluationMode;
  warnings: string[];
}

export interface CommitteeExportPayload {
  documentName: string;
  exportedAt: string;
  committeeSummary: {
    evaluationMode?: CommitteeEvaluationMode;
    industryProfileId?: string;
    industryLabel?: string;
    baselineScore?: number;
    bestScore?: number;
    improvementPct?: number;
    acceptedRewrites?: number;
    rewritesTested?: number;
    aiEvaluations?: number;
    heuristicEvaluations?: number;
    llmCoveragePct?: number;
    personas?: Array<{
      name: string;
      title: string;
      authorityWeight: number;
      currentScore: number;
      topObjection?: string | null;
      evaluationSource?: CommitteeEvaluationSource;
    }>;
  };
  sections: Array<{
    sectionId: number;
    title: string;
    originalContent: string;
    optimizedContent: string;
  }>;
  rewriteLog: RewriteAttempt[];
  llmHandoff: {
    task?: string;
    documentName?: string;
    industryProfile?: {
      id: string;
      label: string;
    };
    evaluationCoverage?: {
      aiEvaluations: number;
      heuristicEvaluations: number;
      llmCoveragePct: number;
    };
    targetAudience?: Array<Record<string, unknown>>;
    documentSummary?: Record<string, unknown>;
    rewriteGoals?: string[];
    actionableSectionFeedback?: Array<Record<string, unknown>>;
    materials?: Record<string, unknown>;
    suggestedPrompt?: string;
  };
}

export type CommitteeRunSocketEvent =
  | { type: 'snapshot'; payload: CommitteeSnapshot }
  | { type: 'run.stage'; payload: { runId: string; stage: CommitteeStage; message?: string } }
  | { type: 'rewrite.completed'; payload: RewriteAttempt }
  | { type: 'committee.persona.batch'; payload: { runId: string; personas: CommitteePersonaView[] } }
  | { type: 'metrics.tick'; payload: CommitteeMetrics }
  | { type: 'committee.report.ready'; payload: CommitteeReport }
  | { type: 'error'; payload: { code: string; message: string } };
