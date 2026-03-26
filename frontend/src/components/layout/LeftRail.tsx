import React from 'react';
import { useAppStore } from '@/store/useAppStore';
import ExperimentFeed from '@/components/run/ExperimentFeed';
import { PANEL_BORDER, PANEL_BG } from '@/lib/theme';

const EMPTY_EXPERIMENTS: never[] = [];

function PanelHeader({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        padding: '10px 14px',
        borderBottom: `1px solid ${PANEL_BORDER}`,
        flexShrink: 0,
      }}
    >
      <span
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 10,
          fontWeight: 600,
          letterSpacing: '0.14em',
          textTransform: 'uppercase',
          color: '#6B7480',
        }}
      >
        {children}
      </span>
    </div>
  );
}

function QuickStat({ label, value, color }: { label: string; value: string | number; color?: string }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 9,
          color: '#4B5563',
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          marginBottom: 2,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 15,
          fontWeight: 600,
          color: color ?? '#9AA4B2',
        }}
      >
        {value}
      </div>
    </div>
  );
}

export default function LeftRail() {
  const experiments = useAppStore(state => state.runSnapshot?.experiments) ?? EMPTY_EXPERIMENTS;
  const improvementPct = useAppStore(state => state.runSnapshot?.metrics?.improvementPct);

  const kept = experiments.filter(e => e.decision === 'kept').length;
  const reverted = experiments.filter(e => e.decision === 'reverted').length;
  const total = experiments.length;
  const gainPct = improvementPct != null
    ? `+${improvementPct.toFixed(1)}%`
    : '—';

  return (
    <div
      style={{
        width: 320,
        flexShrink: 0,
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        background: PANEL_BG,
        borderRight: `1px solid ${PANEL_BORDER}`,
        backdropFilter: 'blur(12px)',
        overflow: 'hidden',
      }}
    >
      <PanelHeader>Experiment Stream</PanelHeader>

      {/* Quick stats row */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          padding: '10px 12px',
          borderBottom: `1px solid ${PANEL_BORDER}`,
          gap: 4,
          flexShrink: 0,
        }}
      >
        <QuickStat label="Run" value={total} />
        <QuickStat label="Kept" value={kept} color="#4ADE80" />
        <QuickStat label="Rev." value={reverted} color="#FB7185" />
        <QuickStat label="Gain" value={gainPct} color="#4DA3FF" />
      </div>

      {/* Feed */}
      <ExperimentFeed experiments={experiments} />
    </div>
  );
}
