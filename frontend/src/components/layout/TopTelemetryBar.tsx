import React, { useEffect, useState } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { formatScore, formatPercent, formatDuration, formatDollars, truncate } from '@/lib/format';
import { PANEL_BORDER, ACCENT_BLUE, TEXT_SECONDARY, TEXT_DIM } from '@/lib/theme';

function formatQueriesTested(evalCaseCount: number, experimentsRun: number, baselineScore: number) {
  if (evalCaseCount <= 0) return '—';
  const completedPasses = experimentsRun + (baselineScore > 0 ? 1 : 0);
  return Intl.NumberFormat('en-US').format(evalCaseCount * Math.max(completedPasses, 1));
}

function HowItWorksButton() {
  const showExplainer = useAppStore(state => state.showExplainer);
  const toggleExplainer = useAppStore(state => state.toggleExplainer);
  const [hovered, setHovered] = useState(false);

  return (
    <button
      onClick={toggleExplainer}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      title="How does this work?"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        padding: '6px 12px',
        marginRight: 8,
        background: showExplainer
          ? `${ACCENT_BLUE}20`
          : hovered
          ? 'rgba(255,255,255,0.08)'
          : 'rgba(255,255,255,0.04)',
        border: `1px solid ${showExplainer ? `${ACCENT_BLUE}50` : PANEL_BORDER}`,
        borderRadius: 6,
        cursor: 'pointer',
        transition: 'all 0.2s',
        flexShrink: 0,
      }}
    >
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: 18,
          height: 18,
          borderRadius: '50%',
          background: showExplainer ? `${ACCENT_BLUE}30` : 'rgba(255,255,255,0.08)',
          border: `1px solid ${showExplainer ? ACCENT_BLUE : 'rgba(255,255,255,0.15)'}`,
          fontFamily: 'Inter, sans-serif',
          fontSize: 11,
          fontWeight: 700,
          color: showExplainer ? ACCENT_BLUE : '#9AA4B2',
          transition: 'all 0.2s',
        }}
      >
        ?
      </span>
      <span
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 9,
          fontWeight: 600,
          letterSpacing: '0.06em',
          color: showExplainer ? ACCENT_BLUE : '#9AA4B2',
          transition: 'color 0.2s',
        }}
      >
        {showExplainer ? 'BACK' : 'HOW IT WORKS'}
      </span>
    </button>
  );
}

function TelemetryBlock({
  label,
  value,
  valueStyle,
  dimmed,
}: {
  label: string;
  value: string;
  valueStyle?: React.CSSProperties;
  dimmed?: boolean;
}) {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-start',
        justifyContent: 'center',
        padding: '0 16px',
        borderRight: `1px solid ${PANEL_BORDER}`,
        minWidth: 80,
        gap: 2,
      }}
    >
      <span
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 9,
          fontWeight: 600,
          letterSpacing: '0.12em',
          textTransform: 'uppercase',
          color: TEXT_DIM,
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 16,
          fontWeight: 500,
          color: dimmed ? TEXT_DIM : '#EEF3FF',
          lineHeight: 1,
          ...valueStyle,
        }}
      >
        {value}
      </span>
    </div>
  );
}

function SocketStatusDot({ status }: { status: 'connected' | 'disconnected' | 'reconnecting' | 'dead' | 'idle' }) {
  const colorMap = {
    connected: '#4ADE80',
    reconnecting: '#FBBF24',
    disconnected: '#FB7185',
    dead: '#FB7185',
    idle: '#6B7480',
  };
  const color = colorMap[status];
  const isPulsing = status === 'connected' || status === 'reconnecting';

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        padding: '0 16px',
      }}
    >
      <div style={{ position: 'relative', width: 8, height: 8 }}>
        {isPulsing && (
          <div
            style={{
              position: 'absolute',
              inset: -3,
              borderRadius: '50%',
              background: color,
              opacity: 0.3,
              animation: 'pulse 2s ease-in-out infinite',
            }}
          />
        )}
        <div
          style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: color,
            position: 'relative',
            zIndex: 1,
          }}
        />
      </div>
      <span
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 9,
          color: color,
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
        }}
      >
        {status}
      </span>
    </div>
  );
}

export default function TopTelemetryBar() {
  const metrics = useAppStore(state => state.runSnapshot?.metrics);
  const summary = useAppStore(state => state.runSnapshot?.summary);
  const mode = useAppStore(state => state.runSnapshot?.mode ?? 'demo');
  const socketStatus = useAppStore(state => state.socketStatus);
  const [, forceUpdate] = useState(0);

  // Update elapsed time display every second
  useEffect(() => {
    const timer = setInterval(() => forceUpdate(n => n + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  const ndcgValue = metrics ? formatScore(metrics.currentScore) : '—';
  const keptRun = metrics
    ? `${metrics.improvementsKept} / ${metrics.experimentsRun}`
    : '— / —';
  const winPct = metrics
    ? `${(metrics.personaSuccessRate * 100).toFixed(0)}%`
    : '—';
  const savings =
    metrics?.projectedMonthlySavingsUsd != null
      ? formatDollars(metrics.projectedMonthlySavingsUsd)
      : '—';
  const elapsed = metrics ? formatDuration(metrics.elapsedSeconds) : '—';
  const queriesTested = summary && metrics
    ? formatQueriesTested(summary.baselineEvalCount, metrics.experimentsRun, metrics.baselineScore)
    : '—';
  const clusterName = summary?.clusterName ? truncate(summary.clusterName, 18) : '—';

  return (
    <>
      <style>{`
        @keyframes pulse {
          0%, 100% { transform: scale(1); opacity: 0.3; }
          50% { transform: scale(1.6); opacity: 0.1; }
        }
      `}</style>
      <div
        style={{
          height: 64,
          flexShrink: 0,
          display: 'flex',
          alignItems: 'stretch',
          background: 'rgba(11,15,21,0.95)',
          borderBottom: `1px solid ${PANEL_BORDER}`,
          backdropFilter: 'blur(12px)',
          zIndex: 100,
          overflow: 'hidden',
        }}
      >
        {/* Logo block */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            padding: '0 20px',
            borderRight: `1px solid ${PANEL_BORDER}`,
            gap: 6,
            flexShrink: 0,
          }}
        >
          <div
            style={{
              width: 24,
              height: 24,
              borderRadius: '50%',
              background: `radial-gradient(circle, ${ACCENT_BLUE} 0%, rgba(77,163,255,0.3) 60%, transparent 100%)`,
              boxShadow: `0 0 12px ${ACCENT_BLUE}`,
            }}
          />
          <span
            style={{
              fontFamily: 'Inter, sans-serif',
              fontWeight: 700,
              fontSize: 13,
              color: '#EEF3FF',
              letterSpacing: '-0.01em',
            }}
          >
            ElastiTune
          </span>
        </div>

        <TelemetryBlock
          label="MODE"
          value={mode.toUpperCase()}
          valueStyle={{ color: mode === 'demo' ? '#FBBF24' : '#4ADE80', fontSize: 13 }}
        />
        <TelemetryBlock label="CLUSTER" value={clusterName} />
        <TelemetryBlock label="QUERIES TESTED" value={queriesTested} />
        <TelemetryBlock
          label="nDCG@10"
          value={ndcgValue}
          valueStyle={{
            color: ACCENT_BLUE,
            textShadow: `0 0 8px ${ACCENT_BLUE}`,
            fontSize: 18,
          }}
        />
        <TelemetryBlock label="KEPT / RUN" value={keptRun} />
        <TelemetryBlock label="PERSONA WIN%" value={winPct} />
        <TelemetryBlock
          label="SAVINGS"
          value={savings}
          valueStyle={
            savings !== '—'
              ? { color: '#4ADE80' }
              : { color: TEXT_DIM }
          }
          dimmed={savings === '—'}
        />
        <TelemetryBlock label="ELAPSED" value={elapsed} />

        <div style={{ flex: 1 }} />

        <HowItWorksButton />
        <SocketStatusDot status={socketStatus} />
      </div>
    </>
  );
}
