import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { RunStage } from '@/types/contracts';
import { PANEL_BORDER } from '@/lib/theme';
import { useAppStore } from '@/store/useAppStore';
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
  const [showStopConfirm, setShowStopConfirm] = useState(false);
  const metrics = useAppStore(s => s.runSnapshot?.metrics);
  const isRunning = stage === 'running' || stage === 'starting';
  const isCompleted = stage === 'completed';
  const isStopping = stage === 'stopping';
  const stageColor = STAGE_COLORS[stage];

  const handleStopConfirm = () => {
    setShowStopConfirm(false);
    onStop();
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
            <span
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 10,
                color: '#6B7480',
              }}
            >
              {metrics.experimentsRun} exp
            </span>
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

        {/* View Report */}
        {isCompleted && (
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
            View Report \u2192
          </button>
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
