export type RunMode = 'demo' | 'live';
export type ProductMode = 'search' | 'committee';
export type RunStage =
  | 'idle'
  | 'analyzing'
  | 'ready'
  | 'starting'
  | 'running'
  | 'stopping'
  | 'completed'
  | 'error';

export type PersonaState =
  | 'idle'
  | 'searching'
  | 'success'
  | 'partial'
  | 'failure'
  | 'reacting';

export type ExperimentDecision = 'kept' | 'reverted';

export interface LlmConfig {
  provider: 'openai_compatible' | 'openai' | 'anthropic' | 'disabled';
  baseUrl?: string;
  model?: string;
  apiKey?: string;
}

export interface ConnectRequest {
  mode: RunMode;
  esUrl?: string;
  apiKey?: string;
  indexName?: string;
  llm?: LlmConfig;
  uploadedEvalSet?: EvalCase[];
  autoGenerateEval?: boolean;
  vectorFieldOverride?: string | null;
  maxSampleDocs?: number;
}

export interface ConnectResponse {
  connectionId: string;
  productMode: ProductMode;
  mode: RunMode;
  stage: RunStage;
  summary: ConnectionSummary;
  warnings: string[];
}

export interface ConnectionSummary {
  clusterName: string;
  clusterVersion?: string;
  indexName: string;
  docCount: number;
  detectedDomain: 'security' | 'developer_docs' | 'compliance' | 'general';
  primaryTextFields: string[];
  vectorField?: string | null;
  vectorDims?: number | null;
  sampleDocs: SampleDoc[];
  baselineEvalCount: number;
  baselineReady: boolean;
}

export interface SampleDoc {
  id: string;
  title: string;
  excerpt: string;
  fieldPreview: Record<string, string>;
}

export interface EvalCase {
  id: string;
  query: string;
  relevantDocIds: string[];
  personaHint?: string;
  difficulty?: 'easy' | 'medium' | 'hard';
}

export interface SearchProfile {
  lexicalFields: Array<{ field: string; boost: number }>;
  multiMatchType: 'best_fields' | 'most_fields' | 'cross_fields' | 'phrase';
  minimumShouldMatch: string;
  tieBreaker: number;
  phraseBoost: number;
  fuzziness: 'AUTO' | '0';
  useVector: boolean;
  vectorField?: string | null;
  vectorWeight: number;
  lexicalWeight: number;
  fusionMethod: 'weighted_sum' | 'rrf';
  rrfRankConstant: number;
  knnK: number;
  numCandidates: number;
}

export interface SearchProfileChange {
  path: string;
  before: string | number | boolean | null;
  after: string | number | boolean | null;
  label: string;
}

export interface ExperimentRecord {
  experimentId: number;
  timestamp: string;
  hypothesis: string;
  change: SearchProfileChange;
  baselineScore: number;
  candidateScore: number;
  deltaAbsolute: number;
  deltaPercent: number;
  decision: ExperimentDecision;
  durationMs: number;
  queryFailuresBefore: string[];
  queryFailuresAfter: string[];
}

export interface PersonaDefinition {
  id: string;
  name: string;
  role: string;
  department: string;
  archetype: string;
  goal: string;
  orbit: number;
  colorSeed: number;
  queries: string[];
}

export interface PersonaRuntime {
  id: string;
  state: PersonaState;
  lastQuery?: string;
  lastResultRank?: number | null;
  successRate: number;
  totalSearches: number;
  successes: number;
  partials: number;
  failures: number;
  angle: number;
  speed: number;
  radius: number;
  pulseUntil?: number | null;
  reactUntil?: number | null;
}

export interface PersonaViewModel extends PersonaDefinition, PersonaRuntime {}

export interface PersonaActivityEntry {
  id: string;
  kind: 'query' | 'success' | 'partial' | 'failure' | 'reacting';
  title: string;
  detail: string;
  timestamp: string;
}

export interface RunLaunchConfig {
  durationMinutes: number;
  maxExperiments: number;
  personaCount: number;
  autoStopOnPlateau: boolean;
  personaPrompt: string;
}

export interface CompressionMethodResult {
  method: 'float32' | 'int8' | 'int4' | 'rotated_int4';
  sizeBytes: number;
  recallAt10: number;
  estimatedMonthlyCostUsd: number;
  sizeReductionPct: number;
  status: 'pending' | 'running' | 'done' | 'skipped' | 'error';
  note?: string;
}

export interface CompressionSummary {
  available: boolean;
  vectorField?: string | null;
  vectorDims?: number | null;
  methods: CompressionMethodResult[];
  bestRecommendation?: string;
  projectedMonthlySavingsUsd?: number;
  status: 'idle' | 'running' | 'done' | 'skipped' | 'error';
}

export interface HeroMetrics {
  currentScore: number;
  baselineScore: number;
  bestScore: number;
  improvementPct: number;
  experimentsRun: number;
  improvementsKept: number;
  personaSuccessRate: number;
  elapsedSeconds: number;
  projectedMonthlySavingsUsd?: number | null;
  scoreTimeline: Array<{ t: number; score: number }>;
}

export interface RunConfig {
  durationMinutes: number;
  maxExperiments: number;
  personaCount: number;
  autoStopOnPlateau: boolean;
}

export interface RunSnapshot {
  runId: string;
  productMode: ProductMode;
  mode: RunMode;
  stage: RunStage;
  summary: ConnectionSummary;
  searchProfile: SearchProfile;
  recommendedProfile: SearchProfile;
  metrics: HeroMetrics;
  personas: PersonaViewModel[];
  experiments: ExperimentRecord[];
  compression: CompressionSummary;
  warnings: string[];
  runConfig?: RunConfig;
  startedAt?: string;
  completedAt?: string | null;
}

export interface QueryBreakdownRow {
  baselineTopResults?: Array<{
    docId: string;
    title: string;
    excerpt: string;
    score: number;
  }>;
  bestTopResults?: Array<{
    docId: string;
    title: string;
    excerpt: string;
    score: number;
  }>;
  queryId: string;
  query: string;
  difficulty: string;
  baselineScore: number;
  bestScore: number;
  deltaPct: number;
  failureReason?: string | null;
  topRelevantDocIds: string[];
}

export interface PersonaImpactRow {
  personaId: string;
  name: string;
  role: string;
  beforeSuccessRate: number;
  afterSuccessRate: number;
  deltaPct: number;
}

export interface ReportPayload {
  runId: string;
  generatedAt: string;
  mode: RunMode;
  summary: {
    headline: string;
    overview: string;
    nextSteps: string[];
    baselineScore: number;
    bestScore: number;
    improvementPct: number;
    experimentsRun: number;
    improvementsKept: number;
    durationSeconds: number;
    projectedMonthlySavingsUsd?: number | null;
  };
  connection: ConnectionSummary;
  connectionConfig?: {
    mode: RunMode;
    esUrl?: string | null;
    apiKey?: string | null;
    indexName?: string | null;
    evalSet: EvalCase[];
    llm?: LlmConfig | null;
  } | null;
  searchProfileBefore: SearchProfile;
  searchProfileAfter: SearchProfile;
  diff: SearchProfileChange[];
  queryBreakdown: QueryBreakdownRow[];
  personaImpact: PersonaImpactRow[];
  experiments: ExperimentRecord[];
  compression: CompressionSummary;
  warnings: string[];
  previousRunId?: string | null;
}

export interface SearchRunListItem {
  run_id: string;
  mode: RunMode;
  stage: RunStage;
  index_name?: string | null;
  cluster_name?: string | null;
  baseline_score: number;
  best_score: number;
  improvement_pct: number;
  experiments_run: number;
  started_at?: string | null;
  completed_at?: string | null;
  updated_at?: string | null;
}

export interface BenchmarkHealthPreset {
  id: string;
  label: string;
  indexName: string;
  expectedDocCount: number;
  docCount: number;
  ready: boolean;
  setupCommand: string;
  reachable: boolean;
}

export interface QueryPreviewPayload {
  queryId: string;
  query: string;
  baselineResults: Array<{
    docId: string;
    title: string;
    excerpt: string;
    score: number;
  }>;
  optimizedResults: Array<{
    docId: string;
    title: string;
    excerpt: string;
    score: number;
  }>;
  baselineQueryDsl?: Record<string, unknown> | null;
  optimizedQueryDsl?: Record<string, unknown> | null;
}

export type RunSocketEvent =
  | { type: 'snapshot'; payload: RunSnapshot }
  | { type: 'run.stage'; payload: { runId: string; stage: RunStage; message?: string } }
  | { type: 'run.complete'; payload: { runId: string; stage: RunStage } }
  | { type: 'experiment.completed'; payload: ExperimentRecord }
  | { type: 'persona.batch'; payload: { runId: string; personas: PersonaRuntime[] } }
  | { type: 'metrics.tick'; payload: HeroMetrics }
  | { type: 'compression.updated'; payload: CompressionSummary }
  | { type: 'report.ready'; payload: ReportPayload }
  | { type: 'error'; payload: { code: string; message: string } };
