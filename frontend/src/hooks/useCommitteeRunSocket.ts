import { useEffect, useRef } from 'react';
import { RunSocket } from '@/lib/socket';
import { useCommitteeStore } from '@/store/useCommitteeStore';
import type { CommitteeRunSocketEvent } from '@/types/committee';

export function useCommitteeRunSocket(runId: string | null) {
  const socketRef = useRef<RunSocket<CommitteeRunSocketEvent> | null>(null);
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

    const unsubStatus = socket.onStatus((status) => {
      setSocketStatus(status);
    });

    const unsubEvent = socket.onEvent((event) => {
      switch (event.type) {
        case 'snapshot':
          loadSnapshot(event.payload);
          break;
        case 'run.stage':
          setStage(event.payload.stage);
          break;
        case 'rewrite.completed':
          mergeRewrite(event.payload);
          break;
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
