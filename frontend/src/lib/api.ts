import type {
  ConnectRequest, ConnectResponse, RunSnapshot, ReportPayload
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
  }) =>
    request<{ runId: string; stage: string }>('/runs', {
      method: 'POST',
      body: JSON.stringify({
        connectionId,
        durationMinutes: opts?.durationMinutes ?? 30,
        maxExperiments: opts?.maxExperiments ?? 60,
        personaCount: opts?.personaCount ?? 36,
        autoStopOnPlateau: opts?.autoStopOnPlateau ?? true,
      }),
    }),

  getSnapshot: (runId: string) =>
    request<RunSnapshot>(`/runs/${runId}`),

  stopRun: (runId: string) =>
    request<{ runId: string; stage: string }>(`/runs/${runId}/stop`, { method: 'POST' }),

  getReport: (runId: string) =>
    request<ReportPayload>(`/runs/${runId}/report`),

  connectCommittee: async (req: {
    file: File;
    evaluationMode: 'full_committee' | 'adversarial' | 'champion_only';
    useSeedPersonas: boolean;
    committeeDescription?: string;
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
  }) =>
    request<{ runId: string; stage: string; productMode: 'committee' }>('/committee/runs', {
      method: 'POST',
      body: JSON.stringify({
        connectionId,
        durationMinutes: opts?.durationMinutes ?? 4,
        maxRewrites: opts?.maxRewrites ?? 36,
        autoStopOnPlateau: opts?.autoStopOnPlateau ?? true,
        doNoHarmFloor: opts?.doNoHarmFloor ?? -0.05,
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
};
