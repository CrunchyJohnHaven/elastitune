import React from 'react';
import type { ExperimentRecord } from '@/types/contracts';
import { formatScore, formatPercent, formatTimestamp, truncate } from '@/lib/format';
import { PANEL_BORDER } from '@/lib/theme';

interface ExperimentTableProps {
  experiments: ExperimentRecord[];
  title?: string;
  filterKept?: boolean;
}

export default function ExperimentTable({
  experiments,
  title = 'Experiments',
  filterKept,
}: ExperimentTableProps) {
  const safeExperiments = experiments ?? [];
  const rows = filterKept
    ? safeExperiments.filter(e => e.decision === 'kept')
    : safeExperiments;

  const thStyle: React.CSSProperties = {
    fontFamily: 'Inter, sans-serif',
    fontSize: 10,
    fontWeight: 600,
    color: '#6B7480',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    padding: '8px 12px',
    textAlign: 'left',
    borderBottom: `1px solid ${PANEL_BORDER}`,
    background: 'rgba(255,255,255,0.02)',
    whiteSpace: 'nowrap',
  };

  const tdBase: React.CSSProperties = {
    fontFamily: 'JetBrains Mono, monospace',
    fontSize: 11,
    color: '#9AA4B2',
    padding: '8px 12px',
    borderBottom: `1px solid ${PANEL_BORDER}`,
    verticalAlign: 'top',
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
        {title}
        {filterKept && (
          <span
            style={{
              fontFamily: 'Inter, sans-serif',
              fontWeight: 400,
              fontSize: 12,
              color: '#6B7480',
              marginLeft: 10,
            }}
          >
            ({rows.length} kept)
          </span>
        )}
      </h2>

      {rows.length === 0 ? (
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
          No experiments to display.
        </div>
      ) : (
        <div
          style={{
            border: `1px solid ${PANEL_BORDER}`,
            borderRadius: 8,
            overflow: 'hidden',
            overflowX: 'auto',
          }}
        >
          <table
            style={{ width: '100%', borderCollapse: 'collapse', minWidth: 680 }}
          >
            <thead>
              <tr>
                <th style={thStyle}>#</th>
                <th style={thStyle}>Time</th>
                <th style={thStyle}>Change</th>
                <th style={{ ...thStyle, maxWidth: 220 }}>Hypothesis</th>
                <th style={{ ...thStyle, textAlign: 'right' }}>Score</th>
                <th style={{ ...thStyle, textAlign: 'right' }}>Δ%</th>
                <th style={{ ...thStyle, textAlign: 'center' }}>Decision</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(exp => {
                const isKept = exp.decision === 'kept';
                const positive = exp.deltaAbsolute >= 0;

                return (
                  <tr
                    key={exp.experimentId}
                    style={{
                      background: isKept
                        ? 'rgba(74,222,128,0.025)'
                        : 'rgba(251,113,133,0.015)',
                      borderLeft: `3px solid ${
                        isKept
                          ? 'rgba(74,222,128,0.35)'
                          : 'rgba(251,113,133,0.25)'
                      }`,
                    }}
                  >
                    <td style={{ ...tdBase, color: '#4B5563' }}>
                      {exp.experimentId}
                    </td>
                    <td style={{ ...tdBase, whiteSpace: 'nowrap', color: '#4B5563' }}>
                      {formatTimestamp(exp.timestamp)}
                    </td>
                    <td
                      style={{
                        ...tdBase,
                        fontFamily: 'JetBrains Mono, monospace',
                        color: '#9AA4B2',
                        maxWidth: 200,
                      }}
                    >
                      <span
                        style={{
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          display: 'block',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {exp.change.label}
                      </span>
                    </td>
                    <td
                      style={{
                        ...tdBase,
                        fontFamily: 'Inter, sans-serif',
                        color: '#6B7480',
                        fontStyle: 'italic',
                        maxWidth: 220,
                      }}
                    >
                      <span
                        style={{
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          display: '-webkit-box',
                          WebkitLineClamp: 2,
                          WebkitBoxOrient: 'vertical',
                        }}
                      >
                        {truncate(exp.hypothesis, 80)}
                      </span>
                    </td>
                    <td
                      style={{
                        ...tdBase,
                        textAlign: 'right',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      <span style={{ color: '#6B7480' }}>
                        {formatScore(exp.beforeScore ?? exp.baselineScore ?? 0)}
                      </span>
                      <span style={{ color: '#4B5563', margin: '0 4px' }}>→</span>
                      <span style={{ color: isKept ? '#4ADE80' : '#EEF3FF' }}>
                        {formatScore(exp.candidateScore)}
                      </span>
                    </td>
                    <td
                      style={{
                        ...tdBase,
                        textAlign: 'right',
                        color: positive ? '#4ADE80' : '#FB7185',
                        fontWeight: 600,
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {formatPercent(exp.deltaPercent)}
                    </td>
                    <td style={{ ...tdBase, textAlign: 'center' }}>
                      <span
                        style={{
                          display: 'inline-block',
                          fontFamily: 'JetBrains Mono, monospace',
                          fontSize: 9,
                          fontWeight: 700,
                          letterSpacing: '0.08em',
                          padding: '2px 7px',
                          borderRadius: 3,
                          background: isKept
                            ? 'rgba(74,222,128,0.12)'
                            : 'rgba(251,113,133,0.12)',
                          color: isKept ? '#4ADE80' : '#FB7185',
                          border: `1px solid ${
                            isKept
                              ? 'rgba(74,222,128,0.25)'
                              : 'rgba(251,113,133,0.25)'
                          }`,
                        }}
                      >
                        {isKept ? 'KEPT' : 'REVERTED'}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
