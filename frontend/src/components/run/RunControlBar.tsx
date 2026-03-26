import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { RefreshCw, RotateCcw } from 'lucide-react';
import type { RunStage, ReportPayload } from '@/types/contracts';
import { PANEL_BORDER } from '@/lib/theme';
import { useAppStore } from '@/store/useAppStore';
import { useToast } from '@/components/ui/ToastProvider';
import { api } from '@/lib/api';
import { formatScore, formatPercent } from '@/lib/format';
import ConfirmDialog from '@/components/ui/ConfirmDialog';

interface RunControlBarProps {
  stage: RunStage;
  runId: string;
  onStop: () => void;
}

const STAGE_LABELS: Record<RunStage, string> = {
  idle: 'IDLE',
  analyzing: 'ANALYZING',
  ready: 'READY',
  starting: 'STARTING',
  running: 'RUNNING',
  stopping: 'STOPPING',
  completed: 'COMPLETED',
  error: 'ERROR',
};

const STAGE_COLORS: Record<RunStage, string> = {
  idle: '#6B7480',
  analyzing: '#4DA3FF',
  ready: '#FBBF24',
  starting: '#4DA3FF',
  running: '#4ADE80',
  stopping: '#FBBF24',
  completed: '#4ADE80',
  error: '#FB7185',
};

export default function RunControlBar({ stage, runId, onStop }: RunControlBarProps) {
  const navigate = useNavigate();
  const toast = useToast();
  const [showStopConfirm, setShowStopConfirm] = useState(false);
  const [continuing, setContinuing] = useState(false);
  const metrics = useAppStore(s => s.runSnapshot?.metrics);
  const runConfig = useAppStore(s => s.runSnapshot?.runConfig);
  const connectionId = useAppStore(s => s.connectionId);
  const setRunId = useAppStore(s => s.setRunId);
  const setReport = useAppStore(s => s.setReport);
  const isRunning = stage === 'running' || stage === 'starting';
  const isCompleted = stage === 'completed';
  const isStopping = stage === 'stopping';
  const stageColor = STAGE_COLORS[stage];
  const etaLabel = React.useMemo(() => {
    if (!metrics || !runConfig || !isRunning) return null;
    const remainingExperiments = Math.max(0, runConfig.maxExperiments - metrics.experimentsRun);
    if (metrics.experimentsRun <= 0 || remainingExperiments <= 0) return null;
    const avgExperimentSeconds = metrics.elapsedSeconds / metrics.experimentsRun;
    const remainingSeconds = Math.max(0, Math.round(avgExperimentSeconds * remainingExperiments));
    if (remainingSeconds < 60) return `~${remainingSeconds}s left`;
    return `~${Math.ceil(remainingSeconds / 60)}m left`;
  }, [isRunning, metrics, runConfig]);

  const handleStopConfirm = () => {
    setShowStopConfirm(false);
    onStop();
  };

  const handleContinue = async () => {
    if (!connectionId) {
      toast.error('Connection expired. Return home to start a new run.');
      return;
    }
    setContinuing(true);
    try {
      const resp = await api.startRun(connectionId, {
        durationMinutes: runConfig?.durationMinutes ?? 30,
        maxExperiments: runConfig?.maxExperiments ?? 200,
        personaCount: 36,
        autoStopOnPlateau: true,
        previousRunId: runId,
      });
      setRunId(resp.runId);
      setReport(null as unknown as ReportPayload);
      toast.info('Continuing optimization from best profile\u2026');
      // Use replace to ensure clean navigation to the new run
      navigate(`/run/${resp.runId}`, { replace: true });
    } catch (err) {
      toast.error('Failed to continue. Check your connection.');
      console.error('Continue failed:', err);
    } finally {
      setContinuing(false);
    }
  };

  const handleStartFresh = async () => {
    if (!connectionId) {
      toast.error('Connection expired. Return home to start a new run.');
      return;
    }
    setContinuing(true);
    try {
      const resp = await api.startRun(connectionId, {
        durationMinutes: runConfig?.durationMinutes ?? 30,
        maxExperiments: runConfig?.maxExperiments ?? 200,
        personaCount: 36,
        autoStopOnPlateau: true,
      });
      setRunId(resp.runId);
      setReport(null as unknown as ReportPayload);
      toast.info('Starting fresh optimization\u2026');
      navigate(`/run/${resp.runId}`, { replace: true });
    } catch (err) {
      toast.error('Failed to start fresh. Check your connection.');
      console.error('Start fresh failed:', err);
    } finally {
      setContinuing(false);
    }
  };

  const stopDescription = metrics
    ? `Current score: ${formatScore(metrics.currentScore)} (${formatPercent(metrics.improvementPct)} from baseline). ${metrics.experimentsRun} experiments completed. You can still view the report with results so far.`
    : 'The run will stop and you can view results collected so far.';

  return (
    <>
      <div
        style={{
          position: 'absolute',
          bottom: 20,
          left: '50%',
          transform: 'translateX(-50%)',
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          padding: '10px 18px',
          background: 'rgba(10,14,20,0.88)',
          border: `1px solid ${PANEL_BORDER}`,
          borderRadius: 10,
          backdropFilter: 'blur(16px)',
          boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
          zIndex: 50,
          pointerEvents: 'auto',
        }}
      >
        {/* Stage badge */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: '50%',
              background: stageColor,
              boxShadow: `0 0 6px ${stageColor}`,
              animation:
                isRunning || stage === 'analyzing'
                  ? 'runBarPulse 1.5s ease-in-out infinite'
                  : 'none',
            }}
          />
          <span
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 11,
              fontWeight: 600,
              letterSpacing: '0.1em',
              color: stageColor,
            }}
          >
            {STAGE_LABELS[stage]}
          </span>
        </div>

        {/* Progress indicator */}
        {isRunning && metrics && (
          <>
            <div style={{ width: 1, height: 20, background: PANEL_BORDER }} />
            <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <span
                style={{
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: 10,
                  color: '#6B7480',
                }}
              >
                {metrics.experimentsRun} exp
              </span>
              {etaLabel && (
                <span
                  style={{
                    fontFamily: 'Inter, sans-serif',
                    fontSize: 10,
                    color: '#9AA4B2',
                  }}
                >
                  {etaLabel}
                </span>
              )}
            </div>
          </>
        )}

        {/* Divider */}
        {(isRunning || isCompleted) && (
          <div style={{ width: 1, height: 20, background: PANEL_BORDER }} />
        )}

        {/* Stop Run — opens confirmation dialog */}
        {isRunning && (
          <button
            onClick={() => setShowStopConfirm(true)}
            style={{
              fontFamily: 'Inter, sans-serif',
              fontWeight: 500,
              fontSize: 12,
              color: '#FB7185',
              background: 'rgba(251,113,133,0.08)',
              border: '1px solid rgba(251,113,133,0.2)',
              borderRadius: 6,
              padding: '5px 12px',
              cursor: 'pointer',
              transition: 'background 0.15s, border-color 0.15s',
            }}
            onMouseEnter={e => {
              (e.currentTarget as HTMLButtonElement).style.background = 'rgba(251,113,133,0.15)';
            }}
            onMouseLeave={e => {
              (e.currentTarget as HTMLButtonElement).style.background = 'rgba(251,113,133,0.08)';
            }}
          >
            Stop Run
          </button>
        )}

        {/* Stopping indicator */}
        {isStopping && (
          <span
            style={{
              fontFamily: 'Inter, sans-serif',
              fontSize: 11,
              color: '#FBBF24',
              fontStyle: 'italic',
            }}
          >
            Stopping\u2026
          </span>
        )}

        {/* Completed actions */}
        {isCompleted && (
          <>
            <button
              onClick={handleContinue}
              disabled={continuing || !connectionId}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 5,
                fontFamily: 'Inter, sans-serif',
                fontWeight: 600,
                fontSize: 12,
                color: '#fff',
                background: continuing
                  ? 'rgba(34,197,94,0.3)'
                  : 'linear-gradient(135deg, #22C55E, #16A34A)',
                border: 'none',
                borderRadius: 6,
                padding: '6px 14px',
                cursor: continuing || !connectionId ? 'not-allowed' : 'pointer',
                boxShadow: continuing ? 'none' : '0 0 14px rgba(34,197,94,0.3)',
                transition: 'box-shadow 0.2s, transform 0.1s',
                opacity: continuing || !connectionId ? 0.6 : 1,
              }}
              onMouseEnter={e => {
                if (!continuing && connectionId) {
                  (e.currentTarget as HTMLButtonElement).style.boxShadow =
                    '0 0 22px rgba(34,197,94,0.5)';
                  (e.currentTarget as HTMLButtonElement).style.transform = 'translateY(-1px)';
                }
              }}
              onMouseLeave={e => {
                if (!continuing && connectionId) {
                  (e.currentTarget as HTMLButtonElement).style.boxShadow =
                    '0 0 14px rgba(34,197,94,0.3)';
                  (e.currentTarget as HTMLButtonElement).style.transform = 'translateY(0)';
                }
              }}
            >
              <RefreshCw size={12} />
              {continuing ? 'Starting\u2026' : 'Continue'}
            </button>

            <button
              onClick={handleStartFresh}
              disabled={continuing || !connectionId}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 4,
                fontFamily: 'Inter, sans-serif',
                fontWeight: 500,
                fontSize: 11,
                color: '#9AA4B2',
                background: 'rgba(255,255,255,0.04)',
                border: `1px solid ${PANEL_BORDER}`,
                borderRadius: 6,
                padding: '5px 10px',
                cursor: continuing || !connectionId ? 'not-allowed' : 'pointer',
                transition: 'color 0.15s, border-color 0.15s',
                opacity: continuing || !connectionId ? 0.5 : 1,
              }}
              onMouseEnter={e => {
                if (!continuing && connectionId) {
                  (e.currentTarget as HTMLButtonElement).style.color = '#EEF3FF';
                  (e.currentTarget as HTMLButtonElement).style.borderColor = 'rgba(255,255,255,0.2)';
                }
              }}
              onMouseLeave={e => {
                if (!continuing && connectionId) {
                  (e.currentTarget as HTMLButtonElement).style.color = '#9AA4B2';
                  (e.currentTarget as HTMLButtonElement).style.borderColor = PANEL_BORDER;
                }
              }}
            >
              <RotateCcw size={10} />
              Fresh
            </button>

            <button
              onClick={() => navigate(`/report/${runId}`)}
              style={{
                fontFamily: 'Inter, sans-serif',
                fontWeight: 600,
                fontSize: 12,
                color: '#EEF3FF',
                background: 'linear-gradient(135deg, #4DA3FF, #3D8BFF)',
                border: 'none',
                borderRadius: 6,
                padding: '6px 16px',
                cursor: 'pointer',
                boxShadow: '0 0 16px rgba(77,163,255,0.35)',
                transition: 'box-shadow 0.2s, transform 0.1s',
              }}
              onMouseEnter={e => {
                (e.currentTarget as HTMLButtonElement).style.boxShadow =
                  '0 0 24px rgba(77,163,255,0.55)';
                (e.currentTarget as HTMLButtonElement).style.transform = 'translateY(-1px)';
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLButtonElement).style.boxShadow =
                  '0 0 16px rgba(77,163,255,0.35)';
                (e.currentTarget as HTMLButtonElement).style.transform = 'translateY(0)';
              }}
            >
              View Report {'\u2192'}
            </button>
          </>
        )}

        <style>{`
          @keyframes runBarPulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
          }
        `}</style>
      </div>

      <ConfirmDialog
        open={showStopConfirm}
        title="Stop this optimization?"
        description={stopDescription}
        confirmLabel="Stop Run"
        confirmColor="#FB7185"
        cancelLabel="Keep Running"
        onConfirm={handleStopConfirm}
        onCancel={() => setShowStopConfirm(false)}
      />
    </>
  );
}
