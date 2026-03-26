import { create } from 'zustand';
import type {
  CommitteeMetrics,
  CommitteePersonaView,
  CommitteeReport,
  CommitteeSnapshot,
  RewriteAttempt,
} from '@/types/committee';

interface CommitteeState {
  connectionId: string | null;
  runId: string | null;
  snapshot: CommitteeSnapshot | null;
  report: CommitteeReport | null;
  selectedPersonaId: string | null;
  socketStatus: 'connected' | 'disconnected' | 'reconnecting' | 'dead' | 'idle';
  latestRewrite: RewriteAttempt | null;
  setConnectionId: (id: string | null) => void;
  setRunId: (id: string | null) => void;
  loadSnapshot: (snapshot: CommitteeSnapshot) => void;
  mergeRewrite: (rewrite: RewriteAttempt) => void;
  mergePersonas: (personas: CommitteePersonaView[]) => void;
  mergeMetrics: (metrics: CommitteeMetrics) => void;
  setStage: (stage: CommitteeSnapshot['stage']) => void;
  setReport: (report: CommitteeReport) => void;
  setSelectedPersona: (id: string | null) => void;
  setSocketStatus: (status: CommitteeState['socketStatus']) => void;
  reset: () => void;
}

export const useCommitteeStore = create<CommitteeState>((set) => ({
  connectionId: null,
  runId: null,
  snapshot: null,
  report: null,
  selectedPersonaId: null,
  socketStatus: 'idle',
  latestRewrite: null,
  setConnectionId: (connectionId) => set({ connectionId }),
  setRunId: (runId) => set({ runId }),
  loadSnapshot: (snapshot) => set({
    snapshot,
    latestRewrite: snapshot.rewrites[snapshot.rewrites.length - 1] ?? null,
  }),
  mergeRewrite: (rewrite) => set((state) => {
    if (!state.snapshot) return {};
    return {
      latestRewrite: rewrite,
      snapshot: {
        ...state.snapshot,
        rewrites: [...state.snapshot.rewrites, rewrite],
      },
    };
  }),
  mergePersonas: (personas) => set((state) => {
    if (!state.snapshot) return {};
    return { snapshot: { ...state.snapshot, personas } };
  }),
  mergeMetrics: (metrics) => set((state) => {
    if (!state.snapshot) return {};
    return { snapshot: { ...state.snapshot, metrics } };
  }),
  setStage: (stage) => set((state) => {
    if (!state.snapshot) return {};
    return { snapshot: { ...state.snapshot, stage } };
  }),
  setReport: (report) => set({ report }),
  setSelectedPersona: (selectedPersonaId) => set({ selectedPersonaId }),
  setSocketStatus: (socketStatus) => set({ socketStatus }),
  reset: () => set({
    connectionId: null,
    runId: null,
    snapshot: null,
    report: null,
    selectedPersonaId: null,
    socketStatus: 'idle',
    latestRewrite: null,
  }),
}));
