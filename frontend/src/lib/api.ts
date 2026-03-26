import type {
  BenchmarkHealthPreset, ConnectRequest, ConnectResponse, ModelComparisonResult, QueryPreviewPayload, RunSnapshot, ReportPayload, SearchRunListItem
} from '@/types/contracts';
import type {
  CommitteeConnectionResponse,
  CommitteeExportPayload,
  CommitteeReport,
  CommitteeSnapshot,
} from '@/types/committee';

const BASE = '/api';
const DEFAULT_TIMEOUT_MS = 30_000;

async function request<T>(path: string, options?: RequestInit & { timeoutMs?: number }): Promise<T> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, ...fetchOpts } = options ?? {};
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      ...fetchOpts,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new Error('Request timed out. Check that the backend is running and responsive.');
    }
    if (error instanceof TypeError) {
      throw new Error('Cannot reach the ElastiTune backend. Make sure the API server is running.');
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`HTTP ${res.status}: ${body}`);
  }
  return res.json();
}

export const api = {
  health: () => request<{ ok: boolean; app: string; version: string }>('/health'),

  connect: (req: ConnectRequest) =>
    request<ConnectResponse>('/connect', {
      method: 'POST',
      body: JSON.stringify(req),
    }),

  startRun: (connectionId: string, opts?: {
    durationMinutes?: number;
    maxExperiments?: number;
    personaCount?: number;
    autoStopOnPlateau?: boolean;
    previousRunId?: string;
  }) =>
    request<{ runId: string; stage: string }>('/runs', {
      method: 'POST',
      body: JSON.stringify({
        connectionId,
        durationMinutes: opts?.durationMinutes ?? 30,
        maxExperiments: opts?.maxExperiments ?? 200,
        personaCount: opts?.personaCount ?? 36,
        autoStopOnPlateau: opts?.autoStopOnPlateau ?? true,
        previousRunId: opts?.previousRunId ?? null,
      }),
    }),

  getSnapshot: (runId: string) =>
    request<RunSnapshot>(`/runs/${runId}`),

  stopRun: (runId: string) =>
    request<{ runId: string; stage: string }>(`/runs/${runId}/stop`, { method: 'POST' }),

  getReport: (runId: string) =>
    request<ReportPayload>(`/runs/${runId}/report`),

  previewQuery: (runId: string, queryId: string) =>
    request<QueryPreviewPayload>(`/runs/${runId}/preview-query?queryId=${encodeURIComponent(queryId)}`),

  listRuns: (opts?: {
    limit?: number;
    indexName?: string;
    completedOnly?: boolean;
  }) => {
    const params = new URLSearchParams();
    if (opts?.limit) params.set('limit', String(opts.limit));
    if (opts?.indexName) params.set('indexName', opts.indexName);
    if (opts?.completedOnly) params.set('completedOnly', 'true');
    const suffix = params.toString() ? `?${params.toString()}` : '';
    return request<{ runs: SearchRunListItem[] }>(`/runs${suffix}`);
  },

  getBenchmarkHealth: (esUrl?: string) => {
    const params = new URLSearchParams();
    if (esUrl) params.set('esUrl', esUrl);
    const suffix = params.toString() ? `?${params.toString()}` : '';
    return request<{ reachable: boolean; presets: BenchmarkHealthPreset[] }>(`/connect/benchmarks${suffix}`);
  },

  connectCommittee: async (req: {
    file: File;
    evaluationMode: 'full_committee' | 'adversarial' | 'champion_only';
    useSeedPersonas: boolean;
    committeeDescription?: string;
    industryProfileId?: string;
    llm?: {
      provider: 'openai_compatible' | 'openai' | 'anthropic' | 'disabled';
      baseUrl?: string;
      model?: string;
      apiKey?: string;
    };
    personas?: unknown[];
  }) => {
    const form = new FormData();
    form.append('document', req.file);
    form.append('evaluationMode', req.evaluationMode);
    form.append('useSeedPersonas', String(req.useSeedPersonas));
    if (req.committeeDescription) form.append('committeeDescription', req.committeeDescription);
    if (req.industryProfileId) form.append('industryProfileId', req.industryProfileId);
    if (req.llm) form.append('llmJson', JSON.stringify(req.llm));
    if (req.personas) form.append('personasJson', JSON.stringify(req.personas));
    const res = await fetch(`${BASE}/committee/connect`, {
      method: 'POST',
      body: form,
    });
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`HTTP ${res.status}: ${body}`);
    }
    return res.json() as Promise<CommitteeConnectionResponse>;
  },

  startCommitteeRun: (connectionId: string, opts?: {
    durationMinutes?: number;
    maxRewrites?: number;
    autoStopOnPlateau?: boolean;
    doNoHarmFloor?: number;
    scoreThresholds?: {
      supportive?: number;
      cautiouslyInterested?: number;
      neutral?: number;
      skeptical?: number;
      positiveEmotion?: number;
      enthusiasticQuote?: number;
      cautiousQuote?: number;
    };
  }) =>
    request<{ runId: string; stage: string; productMode: 'committee' }>('/committee/runs', {
      method: 'POST',
      body: JSON.stringify({
        connectionId,
        durationMinutes: opts?.durationMinutes ?? 4,
        maxRewrites: opts?.maxRewrites ?? 36,
        autoStopOnPlateau: opts?.autoStopOnPlateau ?? true,
        doNoHarmFloor: opts?.doNoHarmFloor ?? -0.05,
        scoreThresholds: opts?.scoreThresholds,
      }),
    }),

  getCommitteeSnapshot: (runId: string) =>
    request<CommitteeSnapshot>(`/committee/runs/${runId}`),

  stopCommitteeRun: (runId: string) =>
    request<{ runId: string; stage: string; productMode: 'committee' }>(
      `/committee/runs/${runId}/stop`,
      { method: 'POST' },
    ),

  getCommitteeReport: (runId: string) =>
    request<CommitteeReport>(`/committee/runs/${runId}/report`),

  getCommitteeExport: (runId: string) =>
    request<CommitteeExportPayload>(`/committee/runs/${runId}/export`),

  async compareModels(connectionId: string, modelIds: string[], maxExperimentsPerModel = 10): Promise<ModelComparisonResult> {
    const res = await fetch(`${BASE}/model-compare`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ connectionId, modelIds, maxExperimentsPerModel }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },
};
