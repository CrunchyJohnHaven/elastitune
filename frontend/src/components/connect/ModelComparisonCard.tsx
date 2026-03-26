import React from 'react';
import type { ModelComparisonResult } from '@/types/contracts';

interface ModelComparisonCardProps {
  result: ModelComparisonResult;
}

export default function ModelComparisonCard({ result }: ModelComparisonCardProps) {
  const { entries, recommendedModel, comparisonNote } = result;

  if (!entries.length) {
    return (
      <div
        style={{
          marginTop: 14,
          padding: '14px 16px',
          background: 'rgba(255,255,255,0.02)',
          border: '1px solid rgba(255,255,255,0.08)',
          borderRadius: 8,
          fontFamily: 'Inter, sans-serif',
          fontSize: 12,
          color: '#9AA4B2',
        }}
      >
        No comparison results available.
      </div>
    );
  }

  const maxBestScore = Math.max(...entries.map(e => e.bestScore), 0.001);

  return (
    <div
      style={{
        marginTop: 14,
        background: 'rgba(5,7,11,0.7)',
        border: '1px solid rgba(255,255,255,0.08)',
        borderRadius: 10,
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '12px 16px',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 8,
        }}
      >
        <span
          style={{
            fontFamily: 'Inter, sans-serif',
            fontWeight: 600,
            fontSize: 12,
            color: '#EEF3FF',
          }}
        >
          Model Comparison Results
        </span>
        {recommendedModel && (
          <span
            style={{
              fontFamily: 'Inter, sans-serif',
              fontSize: 10,
              fontWeight: 500,
              color: '#4ADE80',
              background: 'rgba(74,222,128,0.1)',
              border: '1px solid rgba(74,222,128,0.2)',
              borderRadius: 20,
              padding: '2px 9px',
              whiteSpace: 'nowrap',
            }}
          >
            Best: {recommendedModel}
          </span>
        )}
      </div>

      {/* Entry rows */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
        {entries.map((entry, idx) => {
          const isRecommended = entry.modelId === recommendedModel;
          const barPct = Math.min(100, (entry.bestScore / maxBestScore) * 100);

          return (
            <div
              key={entry.modelId}
              style={{
                padding: '12px 16px',
                borderBottom:
                  idx < entries.length - 1
                    ? '1px solid rgba(255,255,255,0.05)'
                    : undefined,
                background: isRecommended
                  ? 'rgba(74,222,128,0.04)'
                  : 'transparent',
              }}
            >
              {/* Model ID row */}
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: 8,
                  gap: 8,
                  flexWrap: 'wrap',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                  <span
                    style={{
                      fontFamily: 'JetBrains Mono, monospace',
                      fontSize: 12,
                      fontWeight: 600,
                      color: isRecommended ? '#4ADE80' : '#EEF3FF',
                    }}
                  >
                    {entry.modelId}
                  </span>
                  {isRecommended && (
                    <span
                      style={{
                        fontFamily: 'Inter, sans-serif',
                        fontSize: 9,
                        fontWeight: 700,
                        letterSpacing: '0.07em',
                        color: '#4ADE80',
                        background: 'rgba(74,222,128,0.15)',
                        border: '1px solid rgba(74,222,128,0.3)',
                        borderRadius: 4,
                        padding: '1px 6px',
                        textTransform: 'uppercase',
                      }}
                    >
                      Recommended
                    </span>
                  )}
                </div>

                {/* Scores */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    flexShrink: 0,
                  }}
                >
                  <div style={{ textAlign: 'right' }}>
                    <div
                      style={{
                        fontFamily: 'JetBrains Mono, monospace',
                        fontSize: 9,
                        color: '#6B7480',
                        marginBottom: 1,
                      }}
                    >
                      baseline
                    </div>
                    <div
                      style={{
                        fontFamily: 'JetBrains Mono, monospace',
                        fontSize: 12,
                        color: '#9AA4B2',
                      }}
                    >
                      {entry.baselineScore.toFixed(3)}
                    </div>
                  </div>
                  <div
                    style={{
                      fontFamily: 'JetBrains Mono, monospace',
                      fontSize: 11,
                      color: '#4B5563',
                    }}
                  >
                    →
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div
                      style={{
                        fontFamily: 'JetBrains Mono, monospace',
                        fontSize: 9,
                        color: '#6B7480',
                        marginBottom: 1,
                      }}
                    >
                      best
                    </div>
                    <div
                      style={{
                        fontFamily: 'JetBrains Mono, monospace',
                        fontSize: 12,
                        fontWeight: 600,
                        color: isRecommended ? '#4ADE80' : '#EEF3FF',
                      }}
                    >
                      {entry.bestScore.toFixed(3)}
                    </div>
                  </div>
                  <div
                    style={{
                      fontFamily: 'JetBrains Mono, monospace',
                      fontSize: 11,
                      fontWeight: 600,
                      color: entry.improvementPct >= 0 ? '#4ADE80' : '#FB7185',
                      minWidth: 48,
                      textAlign: 'right',
                    }}
                  >
                    {entry.improvementPct >= 0 ? '+' : ''}
                    {entry.improvementPct.toFixed(1)}%
                  </div>
                </div>
              </div>

              {/* Score bar */}
              <div
                style={{
                  height: 4,
                  background: 'rgba(255,255,255,0.06)',
                  borderRadius: 2,
                  overflow: 'hidden',
                  marginBottom: entry.topChanges.length ? 8 : 0,
                }}
              >
                <div
                  style={{
                    height: '100%',
                    width: `${barPct}%`,
                    background: isRecommended
                      ? 'linear-gradient(90deg, #4ADE80, #22D3EE)'
                      : 'rgba(77,163,255,0.5)',
                    borderRadius: 2,
                    transition: 'width 0.4s ease',
                  }}
                />
              </div>

              {/* Top changes */}
              {entry.topChanges.length > 0 && (
                <div
                  style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: 4,
                    marginTop: 4,
                  }}
                >
                  {entry.topChanges.slice(0, 3).map((change, ci) => (
                    <span
                      key={ci}
                      style={{
                        fontFamily: 'Inter, sans-serif',
                        fontSize: 9,
                        color: '#6B7480',
                        background: 'rgba(255,255,255,0.04)',
                        border: '1px solid rgba(255,255,255,0.06)',
                        borderRadius: 4,
                        padding: '2px 6px',
                      }}
                    >
                      {change}
                    </span>
                  ))}
                  <span
                    style={{
                      fontFamily: 'Inter, sans-serif',
                      fontSize: 9,
                      color: '#4B5563',
                      padding: '2px 0',
                    }}
                  >
                    {entry.experimentsRun} exp · {entry.improvementsKept} kept
                  </span>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Comparison note */}
      {comparisonNote && (
        <div
          style={{
            padding: '10px 16px',
            borderTop: '1px solid rgba(255,255,255,0.06)',
            fontFamily: 'Inter, sans-serif',
            fontSize: 11,
            color: '#9AA4B2',
            lineHeight: 1.5,
          }}
        >
          {comparisonNote}
        </div>
      )}
    </div>
  );
}
