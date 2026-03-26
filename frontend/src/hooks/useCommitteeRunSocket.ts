import { useEffect, useRef } from 'react';
import { RunSocket } from '@/lib/socket';
import { useCommitteeStore } from '@/store/useCommitteeStore';
import { useToast } from '@/components/ui/ToastProvider';
import { formatPercent, formatScore } from '@/lib/format';
import type { CommitteeRunSocketEvent } from '@/types/committee';

export function useCommitteeRunSocket(runId: string | null) {
  const socketRef = useRef<RunSocket<CommitteeRunSocketEvent> | null>(null);
  const bestScoreRef = useRef(0);
  const toast = useToast();
  const {
    loadSnapshot,
    mergeRewrite,
    mergePersonas,
    mergeMetrics,
    setStage,
    setReport,
    setSocketStatus,
  } = useCommitteeStore();

  useEffect(() => {
    if (!runId) return;

    const socket = new RunSocket<CommitteeRunSocketEvent>(runId);
    socketRef.current = socket;
    bestScoreRef.current = 0;

    const unsubStatus = socket.onStatus((status) => {
      setSocketStatus(status);
      if (status === 'disconnected') {
        toast.warning('Committee connection lost. Attempting to reconnect…');
      }
      if (status === 'dead') {
        toast.error('Committee connection lost. Refresh to reconnect.');
      }
    });

    const unsubEvent = socket.onEvent((event) => {
      switch (event.type) {
        case 'snapshot':
          loadSnapshot(event.payload);
          bestScoreRef.current = event.payload.metrics.bestScore ?? 0;
          break;
        case 'run.stage':
          setStage(event.payload.stage);
          if (event.payload.stage === 'completed') {
            toast.success('Committee run complete — View Report');
          }
          break;
        case 'rewrite.completed': {
          mergeRewrite(event.payload);
          const metrics = useCommitteeStore.getState().snapshot?.metrics;
          if (metrics && metrics.bestScore > bestScoreRef.current + 0.001) {
            bestScoreRef.current = metrics.bestScore;
            toast.success(`Consensus up: ${formatScore(metrics.bestScore)} (${formatPercent(metrics.improvementPct)})`);
          }
          break;
        }
        case 'committee.persona.batch':
          mergePersonas(event.payload.personas);
          break;
        case 'metrics.tick':
          mergeMetrics(event.payload);
          break;
        case 'committee.report.ready':
          setReport(event.payload);
          break;
        case 'error':
          toast.error(event.payload?.message ?? 'Committee run failed');
          console.error('Committee run error:', event.payload);
          break;
      }
    });

    socket.connect();

    return () => {
      unsubStatus();
      unsubEvent();
      socket.destroy();
    };
  }, [runId, loadSnapshot, mergeMetrics, mergePersonas, mergeRewrite, setReport, setSocketStatus, setStage]);
}
