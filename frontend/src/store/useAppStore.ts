import { create } from 'zustand';
import type {
  RunSnapshot, ReportPayload, ConnectionSummary,
  ExperimentRecord, PersonaRuntime, HeroMetrics,
  CompressionSummary, RunStage, PersonaActivityEntry
} from '@/types/contracts';

const MAX_PERSONA_ACTIVITY = 8;

function hasPersonaRuntimeChanges(current: PersonaRuntime, next: PersonaRuntime) {
  return current.state !== next.state
    || current.lastQuery !== next.lastQuery
    || current.lastResultRank !== next.lastResultRank
    || current.successRate !== next.successRate
    || current.totalSearches !== next.totalSearches
    || current.successes !== next.successes
    || current.partials !== next.partials
    || current.failures !== next.failures
    || current.angle !== next.angle
    || current.speed !== next.speed
    || current.radius !== next.radius
    || current.pulseUntil !== next.pulseUntil
    || current.reactUntil !== next.reactUntil;
}

function buildPersonaActivityEntries(
  current: PersonaRuntime,
  next: PersonaRuntime,
  timestamp: string
): PersonaActivityEntry[] {
  const entries: PersonaActivityEntry[] = [];

  if (next.lastQuery && next.lastQuery !== current.lastQuery) {
    entries.push({
      id: `${next.id}-${timestamp}-query`,
      kind: 'query',
      title: 'Issued query',
      detail: next.lastQuery,
      timestamp,
    });
  }

  if (next.state !== current.state) {
    if (next.state === 'success') {
      entries.push({
        id: `${next.id}-${timestamp}-success`,
        kind: 'success',
        title: 'Resolved search',
        detail: next.lastResultRank != null
          ? `Found a relevant result at rank #${next.lastResultRank}.`
          : 'Found a relevant result in the candidate set.',
        timestamp,
      });
    } else if (next.state === 'partial') {
      entries.push({
        id: `${next.id}-${timestamp}-partial`,
        kind: 'partial',
        title: 'Partial match',
        detail: next.lastResultRank != null
          ? `Recovered a partial hit at rank #${next.lastResultRank}.`
          : 'Recovered a partial hit, but not the strongest answer.',
        timestamp,
      });
    } else if (next.state === 'failure') {
      entries.push({
        id: `${next.id}-${timestamp}-failure`,
        kind: 'failure',
        title: 'Missed intent',
        detail: 'No relevant result reached the top of the ranking.',
        timestamp,
      });
    } else if (next.state === 'reacting') {
      entries.push({
        id: `${next.id}-${timestamp}-reacting`,
        kind: 'reacting',
        title: 'Re-scoring profile',
        detail: 'Re-evaluating the latest profile change against this persona.',
        timestamp,
      });
    } else if (next.state === 'searching' && entries.length === 0) {
      entries.push({
        id: `${next.id}-${timestamp}-searching`,
        kind: 'query',
        title: 'Search in flight',
        detail: 'Query dispatched to the index core.',
        timestamp,
      });
    }
  }

  return entries;
}

interface AppState {
  // Connection
  connectionSummary: ConnectionSummary | null;
  connectionId: string | null;

  // Run
  runSnapshot: RunSnapshot | null;
  runId: string | null;

  // Report
  report: ReportPayload | null;

  // Socket
  socketStatus: 'connected' | 'disconnected' | 'reconnecting' | 'dead' | 'idle';

  // UI Selection
  selectedPersonaId: string | null;
  hoveredPersonaId: string | null;
  personaActivityById: Record<string, PersonaActivityEntry[]>;

  // Latest experiment for live display
  latestExperiment: ExperimentRecord | null;

  // UI: Explainer panel
  showExplainer: boolean;

  // Actions
  toggleExplainer: () => void;
  setConnection: (connectionId: string, summary: ConnectionSummary) => void;
  setRunId: (runId: string) => void;
  loadSnapshot: (snapshot: RunSnapshot) => void;
  mergeExperiment: (experiment: ExperimentRecord) => void;
  mergePersonaBatch: (personas: PersonaRuntime[]) => void;
  mergeMetrics: (metrics: HeroMetrics) => void;
  mergeCompression: (compression: CompressionSummary) => void;
  setStage: (stage: RunStage) => void;
  setReport: (report: ReportPayload) => void;
  setSocketStatus: (status: AppState['socketStatus']) => void;
  setSelectedPersona: (id: string | null) => void;
  setHoveredPersona: (id: string | null) => void;
  reset: () => void;
}

export const useAppStore = create<AppState>((set) => ({
  connectionSummary: null,
  connectionId: null,
  runSnapshot: null,
  runId: null,
  report: null,
  socketStatus: 'idle',
  selectedPersonaId: null,
  hoveredPersonaId: null,
  personaActivityById: {},
  latestExperiment: null,
  showExplainer: false,

  toggleExplainer: () => set((state) => ({ showExplainer: !state.showExplainer })),

  setConnection: (connectionId, summary) =>
    set({ connectionId, connectionSummary: summary }),

  setRunId: (runId) => set({ runId }),

  loadSnapshot: (snapshot) =>
    set({
      runSnapshot: snapshot,
      personaActivityById: Object.fromEntries(
        snapshot.personas.map(persona => [persona.id, []])
      ),
      latestExperiment: snapshot.experiments.length > 0
        ? snapshot.experiments[snapshot.experiments.length - 1]
        : null,
    }),

  mergeExperiment: (experiment) =>
    set((state) => {
      if (!state.runSnapshot) return {};
      return {
        latestExperiment: experiment,
        runSnapshot: {
          ...state.runSnapshot,
          experiments: [...state.runSnapshot.experiments, experiment],
        },
      };
    }),

  mergePersonaBatch: (personas) =>
    set((state) => {
      if (!state.runSnapshot) return {};
      const patchById = new Map(personas.map(p => [p.id, p]));
      let changed = false;
      let activityChanged = false;
      const timestamp = new Date().toISOString();
      const nextActivityById = { ...state.personaActivityById };
      const nextPersonas = state.runSnapshot.personas.map(p => {
        const patch = patchById.get(p.id);
        if (!patch || !hasPersonaRuntimeChanges(p, patch)) {
          return p;
        }
        changed = true;
        const entries = buildPersonaActivityEntries(p, patch, timestamp);
        if (entries.length > 0) {
          nextActivityById[p.id] = [
            ...entries.slice().reverse(),
            ...(state.personaActivityById[p.id] ?? []),
          ].slice(0, MAX_PERSONA_ACTIVITY);
          activityChanged = true;
        }
        return { ...p, ...patch };
      });
      if (!changed && !activityChanged) return {};
      return {
        ...(activityChanged ? { personaActivityById: nextActivityById } : {}),
        runSnapshot: {
          ...state.runSnapshot,
          personas: nextPersonas,
        },
      };
    }),

  mergeMetrics: (metrics) =>
    set((state) => {
      if (!state.runSnapshot) return {};
      return {
        runSnapshot: { ...state.runSnapshot, metrics },
      };
    }),

  mergeCompression: (compression) =>
    set((state) => {
      if (!state.runSnapshot) return {};
      return {
        runSnapshot: { ...state.runSnapshot, compression },
      };
    }),

  setStage: (stage) =>
    set((state) => {
      if (!state.runSnapshot) return {};
      return {
        runSnapshot: { ...state.runSnapshot, stage },
      };
    }),

  setReport: (report) => set({ report }),

  setSocketStatus: (socketStatus) => set({ socketStatus }),

  setSelectedPersona: (selectedPersonaId) => set({ selectedPersonaId }),

  setHoveredPersona: (hoveredPersonaId) => set({ hoveredPersonaId }),

  reset: () => set({
    connectionSummary: null,
    connectionId: null,
    runSnapshot: null,
    runId: null,
    report: null,
    socketStatus: 'idle',
    selectedPersonaId: null,
    hoveredPersonaId: null,
    personaActivityById: {},
    latestExperiment: null,
    showExplainer: false,
  }),
}));
