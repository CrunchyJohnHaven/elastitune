import React from 'react';
import type { CompressionSummary as CompressionSummaryType } from '@/types/contracts';
import { formatBytes, formatDollars } from '@/lib/format';
import { PANEL_BORDER } from '@/lib/theme';

interface CompressionSummaryProps {
  compression: CompressionSummaryType;
}

const METHOD_LABELS: Record<string, string> = {
  float32: 'float32 (baseline)',
  int8: 'INT8',
  int4: 'INT4',
  rotated_int4: 'Rotated INT4',
};

export default function CompressionSummary({ compression }: CompressionSummaryProps) {
  if (!compression.available || compression.methods.length === 0) {
    return (
      <div style={{ marginBottom: 32 }}>
        <h2
          style={{
            fontFamily: 'Inter, sans-serif',
            fontWeight: 600,
            fontSize: 17,
            color: '#EEF3FF',
            marginBottom: 12,
          }}
        >
          Vector Compression
        </h2>
        <div
          style={{
            padding: '14px',
            fontFamily: 'Inter, sans-serif',
            fontSize: 13,
            color: '#6B7480',
            fontStyle: 'italic',
            background: 'rgba(255,255,255,0.02)',
            borderRadius: 7,
            border: `1px solid ${PANEL_BORDER}`,
          }}
        >
          No vector field available — compression analysis skipped.
        </div>
      </div>
    );
  }

  const best = compression.bestRecommendation;

  const thStyle: React.CSSProperties = {
    fontFamily: 'Inter, sans-serif',
    fontSize: 10,
    fontWeight: 600,
    color: '#6B7480',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    padding: '8px 14px',
    textAlign: 'left',
    borderBottom: `1px solid ${PANEL_BORDER}`,
    background: 'rgba(255,255,255,0.02)',
  };

  const tdStyle: React.CSSProperties = {
    fontFamily: 'JetBrains Mono, monospace',
    fontSize: 11,
    color: '#9AA4B2',
    padding: '9px 14px',
    borderBottom: `1px solid ${PANEL_BORDER}`,
    verticalAlign: 'middle',
  };

  return (
    <div style={{ marginBottom: 32 }}>
      <h2
        style={{
          fontFamily: 'Inter, sans-serif',
          fontWeight: 600,
          fontSize: 17,
          color: '#EEF3FF',
          marginBottom: 16,
        }}
      >
        Vector Compression Analysis
      </h2>

      <div
        style={{
          border: `1px solid ${PANEL_BORDER}`,
          borderRadius: 8,
          overflow: 'hidden',
          marginBottom: 14,
        }}
      >
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={thStyle}>Method</th>
              <th style={{ ...thStyle, textAlign: 'right' }}>Size</th>
              <th style={{ ...thStyle, textAlign: 'right' }}>Reduction</th>
              <th style={{ ...thStyle, textAlign: 'right' }}>Recall@10</th>
              <th style={{ ...thStyle, textAlign: 'right' }}>Est. Monthly</th>
            </tr>
          </thead>
          <tbody>
            {compression.methods.map(m => {
              const isBest = m.method === best;
              const recallColor =
                m.recallAt10 >= 0.95
                  ? '#4ADE80'
                  : m.recallAt10 >= 0.9
                  ? '#FBBF24'
                  : '#FB7185';

              return (
                <tr
                  key={m.method}
                  style={{
                    background: isBest
                      ? 'rgba(74,222,128,0.04)'
                      : 'transparent',
                    borderLeft: isBest
                      ? '3px solid rgba(74,222,128,0.4)'
                      : '3px solid transparent',
                  }}
                >
                  <td
                    style={{
                      ...tdStyle,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 8,
                    }}
                  >
                    <span style={{ color: isBest ? '#4ADE80' : '#9AA4B2' }}>
                      {METHOD_LABELS[m.method] ?? m.method}
                    </span>
                    {isBest && (
                      <span
                        style={{
                          fontFamily: 'Inter, sans-serif',
                          fontSize: 9,
                          fontWeight: 700,
                          color: '#4ADE80',
                          background: 'rgba(74,222,128,0.1)',
                          border: '1px solid rgba(74,222,128,0.25)',
                          padding: '1px 5px',
                          borderRadius: 3,
                        }}
                      >
                        BEST
                      </span>
                    )}
                  </td>
                  <td style={{ ...tdStyle, textAlign: 'right' }}>
                    {m.status === 'done' ? formatBytes(m.sizeBytes) : '—'}
                  </td>
                  <td
                    style={{
                      ...tdStyle,
                      textAlign: 'right',
                      color:
                        m.sizeReductionPct > 0 ? '#4ADE80' : '#9AA4B2',
                    }}
                  >
                    {m.status === 'done'
                      ? `${m.sizeReductionPct.toFixed(0)}%`
                      : m.status}
                  </td>
                  <td
                    style={{
                      ...tdStyle,
                      textAlign: 'right',
                      color: m.status === 'done' ? recallColor : '#4B5563',
                    }}
                  >
                    {m.status === 'done'
                      ? `${(m.recallAt10 * 100).toFixed(1)}%`
                      : '—'}
                  </td>
                  <td style={{ ...tdStyle, textAlign: 'right' }}>
                    {m.status === 'done'
                      ? formatDollars(m.estimatedMonthlyCostUsd)
                      : '—'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Footer: projected savings */}
      {compression.projectedMonthlySavingsUsd != null &&
        compression.projectedMonthlySavingsUsd > 0 && (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'flex-end',
              gap: 10,
              padding: '10px 14px',
              background: 'rgba(74,222,128,0.04)',
              border: `1px solid rgba(74,222,128,0.15)`,
              borderRadius: 8,
            }}
          >
            <span
              style={{
                fontFamily: 'Inter, sans-serif',
                fontSize: 12,
                color: '#6B7480',
              }}
            >
              Projected monthly savings by switching to{' '}
              <strong style={{ color: '#4ADE80' }}>
                {METHOD_LABELS[best ?? ''] ?? best}
              </strong>
              :
            </span>
            <span
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 18,
                fontWeight: 700,
                color: '#4ADE80',
              }}
            >
              {formatDollars(compression.projectedMonthlySavingsUsd)}/mo
            </span>
          </div>
        )}
    </div>
  );
}
