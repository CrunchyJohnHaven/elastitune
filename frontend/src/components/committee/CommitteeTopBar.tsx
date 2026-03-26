import React, { useEffect, useState } from 'react';
import { useCommitteeStore } from '@/store/useCommitteeStore';
import { formatDuration, formatPercent, formatScore, truncate } from '@/lib/format';
import { ACCENT_BLUE, PANEL_BORDER, TEXT_DIM } from '@/lib/theme';

function Block({
  label,
  value,
  color,
  wide,
}: {
  label: string;
  value: string;
  color?: string;
  wide?: boolean;
}) {
  return (
    <div
      style={{
        padding: '0 14px',
        borderRight: `1px solid ${PANEL_BORDER}`,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        gap: 3,
        minWidth: wide ? 240 : 92,
        maxWidth: wide ? 360 : 120,
        overflow: 'hidden',
      }}
    >
      <span
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 9,
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          color: TEXT_DIM,
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 15,
          color: color ?? '#EEF3FF',
          whiteSpace: 'nowrap',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
        }}
      >
        {value}
      </span>
    </div>
  );
}

export default function CommitteeTopBar() {
  const snapshot = useCommitteeStore(state => state.snapshot);
  const socketStatus = useCommitteeStore(state => state.socketStatus);
  const [, forceUpdate] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => forceUpdate(value => value + 1), 1000);
    return () => clearInterval(timer);
  }, []);

  const metrics = snapshot?.metrics;
  const summary = snapshot?.summary;
  const liveElapsedSeconds = (() => {
    if (!snapshot || !metrics) return undefined;
    if (snapshot.stage !== 'running' && snapshot.stage !== 'starting') return metrics.elapsedSeconds;
    if (!snapshot.startedAt) return metrics.elapsedSeconds;
    const started = new Date(snapshot.startedAt).getTime();
    if (Number.isNaN(started)) return metrics.elapsedSeconds;
    return Math.max(metrics.elapsedSeconds, (Date.now() - started) / 1000);
  })();

  return (
    <div
      style={{
        height: 72,
        display: 'flex',
        alignItems: 'stretch',
        background: 'linear-gradient(180deg, rgba(12,17,24,0.98) 0%, rgba(9,13,19,0.94) 100%)',
        borderBottom: `1px solid ${PANEL_BORDER}`,
        overflow: 'hidden',
        flexShrink: 0,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          padding: '0 18px',
          borderRight: `1px solid ${PANEL_BORDER}`,
          gap: 10,
          minWidth: 250,
        }}
      >
        <div
          style={{
            width: 24,
            height: 24,
            borderRadius: '50%',
            background: `radial-gradient(circle, ${ACCENT_BLUE} 0%, rgba(77,163,255,0.35) 65%, transparent 100%)`,
            boxShadow: `0 0 12px ${ACCENT_BLUE}`,
          }}
        />
        <div>
          <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: 14, color: '#EEF3FF' }}>
            Buying Committee Simulator
          </div>
          <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#9AA4B2' }}>
            LIVE REVIEW MODE
          </div>
        </div>
      </div>

      <Block label="Document" value={summary?.documentName ? truncate(summary.documentName, 34) : '—'} color="#EEF3FF" wide />
      <Block label="Sections" value={String(summary?.sectionsCount ?? '—')} />
      <Block label="Consensus" value={metrics ? formatScore(metrics.currentScore) : '—'} color={ACCENT_BLUE} />
      <Block
        label="Rewrites"
        value={metrics ? `${metrics.acceptedRewrites}/${metrics.rewritesTested}` : '—'}
        color="#4ADE80"
      />
      <Block
        label="Delta"
        value={metrics ? formatPercent(metrics.improvementPct) : '—'}
        color={metrics && metrics.improvementPct >= 0 ? '#4ADE80' : '#FB7185'}
      />
      <Block label="Elapsed" value={liveElapsedSeconds != null ? formatDuration(liveElapsedSeconds) : '—'} />
      <div style={{ flex: 1 }} />
      <div style={{ display: 'flex', alignItems: 'center', padding: '0 18px', gap: 8 }}>
        <div
          style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background:
              socketStatus === 'connected'
                ? '#4ADE80'
                : socketStatus === 'reconnecting'
                ? '#FBBF24'
                : socketStatus === 'dead'
                ? '#FB7185'
                : socketStatus === 'disconnected'
                ? '#FB7185'
                : '#6B7480',
          }}
        />
        <span
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 10,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            color: '#9AA4B2',
          }}
        >
          {socketStatus}
        </span>
      </div>
    </div>
  );
}
