import React from 'react';
import { useCommitteeStore } from '@/store/useCommitteeStore';
import { formatPercent, formatScore, formatTimestamp, truncate } from '@/lib/format';
import { PANEL_BG, PANEL_BORDER } from '@/lib/theme';

export default function CommitteeLeftRail({ compact = false }: { compact?: boolean }) {
  const rewrites = useCommitteeStore(state => state.snapshot?.rewrites ?? []);
  const metrics = useCommitteeStore(state => state.snapshot?.metrics);
  const list = rewrites.slice(-24).reverse();

  return (
    <div
      style={{
        width: compact ? '100%' : 340,
        background: PANEL_BG,
        borderRight: compact ? 'none' : `1px solid ${PANEL_BORDER}`,
        borderTop: compact ? `1px solid ${PANEL_BORDER}` : 'none',
        display: 'flex',
        flexDirection: 'column',
        overflow: compact ? 'visible' : 'hidden',
      }}
    >
      <div style={{ padding: '12px 14px', borderBottom: `1px solid ${PANEL_BORDER}` }}>
        <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, letterSpacing: '0.14em', color: '#6B7480', textTransform: 'uppercase' }}>
          Rewrite Stream
        </div>
      </div>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(4, 1fr)',
          gap: 6,
          padding: '10px 12px',
          borderBottom: `1px solid ${PANEL_BORDER}`,
        }}
      >
        {[
          ['Run', String(metrics?.rewritesTested ?? 0), '#EEF3FF'],
          ['Kept', String(metrics?.acceptedRewrites ?? 0), '#4ADE80'],
          ['Rev.', String((metrics?.rewritesTested ?? 0) - (metrics?.acceptedRewrites ?? 0)), '#FB7185'],
          ['Gain', metrics ? formatPercent(metrics.improvementPct) : '—', '#4DA3FF'],
        ].map(([label, value, color]) => (
          <div key={label} style={{ textAlign: 'center' }}>
            <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#4B5563', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
              {label}
            </div>
            <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 15, color }}>{value}</div>
          </div>
        ))}
      </div>
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {list.length === 0 ? (
          <div style={{ padding: '18px', color: '#6B7480', fontStyle: 'italic', fontFamily: 'Inter, sans-serif', fontSize: 12 }}>
            Waiting for the first rewrite attempt...
          </div>
        ) : (
          list.map(rewrite => {
            const isKept = rewrite.decision === 'kept';
            return (
              <div
                key={rewrite.experimentId}
                style={{
                  padding: '10px 12px',
                  borderBottom: `1px solid ${PANEL_BORDER}`,
                  borderLeft: `2px solid ${isKept ? 'rgba(74,222,128,0.45)' : 'rgba(251,113,133,0.35)'}`,
                  background: isKept ? 'rgba(74,222,128,0.03)' : 'rgba(251,113,133,0.02)',
                }}
              >
                <div style={{ display: 'flex', gap: 6, marginBottom: 4, fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#6B7480' }}>
                  <span>#{rewrite.experimentId}</span>
                  <span>{formatTimestamp(rewrite.timestamp)}</span>
                </div>
                <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 12, color: '#EEF3FF', marginBottom: 4 }}>
                  Section {rewrite.sectionId}: {rewrite.sectionTitle}
                </div>
                <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 11, color: '#9AA4B2', marginBottom: 5 }}>
                  {truncate(rewrite.description, 90)}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: '#9AA4B2' }}>
                    {formatScore(rewrite.baselineScore)}
                  </span>
                  <span style={{ color: '#4B5563' }}>→</span>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: isKept ? '#4ADE80' : '#EEF3FF' }}>
                    {formatScore(rewrite.candidateScore)}
                  </span>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: rewrite.deltaPercent >= 0 ? '#4ADE80' : '#FB7185' }}>
                    {formatPercent(rewrite.deltaPercent)}
                  </span>
                  <div style={{ flex: 1 }} />
                  <span
                    style={{
                      fontFamily: 'JetBrains Mono, monospace',
                      fontSize: 9,
                      padding: '2px 6px',
                      borderRadius: 999,
                      color: isKept ? '#4ADE80' : '#FB7185',
                      border: `1px solid ${isKept ? 'rgba(74,222,128,0.25)' : 'rgba(251,113,133,0.25)'}`,
                    }}
                  >
                    {isKept ? 'KEPT' : 'REVERTED'}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
