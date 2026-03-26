import { useEffect, useRef } from 'react';
import { RunSocket } from '@/lib/socket';
import { useAppStore } from '@/store/useAppStore';
import { useToast } from '@/components/ui/ToastProvider';
import { formatScore, formatPercent } from '@/lib/format';
import type { RunSocketEvent } from '@/types/contracts';

export function useRunSocket(runId: string | null) {
  const socketRef = useRef<RunSocket | null>(null);
  const bestScoreRef = useRef<number>(0);
  const toast = useToast();

  const {
    loadSnapshot,
    mergeExperiment,
    mergePersonaBatch,
    mergeMetrics,
    mergeCompression,
    setStage,
    setReport,
    setSocketStatus,
  } = useAppStore();

  useEffect(() => {
    if (!runId) return;

    const socket = new RunSocket(runId);
    socketRef.current = socket;
    bestScoreRef.current = 0;

    const unsubStatus = socket.onStatus((status) => {
      setSocketStatus(status);
      if (status === 'disconnected') {
        toast.warning('Connection lost. Attempting to reconnect\u2026');
      }
    });

    const unsubEvent = socket.onEvent((event: RunSocketEvent) => {
      switch (event.type) {
        case 'snapshot':
          loadSnapshot(event.payload);
          bestScoreRef.current = event.payload.metrics?.bestScore ?? 0;
          break;
        case 'run.stage':
          setStage(event.payload.stage);
          if (event.payload.stage === 'completed') {
            toast.success('Optimization complete \u2014 View Report');
          }
          break;
        case 'experiment.completed': {
          mergeExperiment(event.payload);
          // Toast on new best score
          const metrics = useAppStore.getState().runSnapshot?.metrics;
          if (metrics && metrics.bestScore > bestScoreRef.current + 0.001) {
            bestScoreRef.current = metrics.bestScore;
            toast.success(`New best: ${formatScore(metrics.bestScore)} (${formatPercent(metrics.improvementPct)})`);
          }
          break;
        }
        case 'persona.batch':
          mergePersonaBatch(event.payload.personas);
          break;
        case 'metrics.tick':
          mergeMetrics(event.payload);
          break;
        case 'compression.updated':
          mergeCompression(event.payload);
          break;
        case 'report.ready':
          setReport(event.payload);
          break;
        case 'error':
          toast.error(event.payload?.message ?? 'An error occurred during the run');
          console.error('Run error:', event.payload);
          break;
      }
    });

    socket.connect();

    return () => {
      unsubStatus();
      unsubEvent();
      socket.destroy();
    };
  }, [runId]);
}
