import React, { useState } from 'react';
import { Copy, Loader2 } from 'lucide-react';
import { api } from '@/lib/api';
import type { QueryBreakdownRow, QueryPreviewPayload } from '@/types/contracts';
import { PANEL_BORDER } from '@/lib/theme';

interface QueryBreakdownProps {
  runId: string;
  rows: QueryBreakdownRow[];
}

function difficultyColor(d: string): string {
  if (d === 'easy') return '#4ADE80';
  if (d === 'hard') return '#FB7185';
  return '#FBBF24';
}

function scoreColor(score: number): string {
  if (score >= 0.8) return '#4ADE80';
  if (score >= 0.5) return '#FBBF24';
  return '#FB7185';
}

function ResultCard({
  label,
  results,
}: {
  label: string;
  results: NonNullable<QueryBreakdownRow['bestTopResults']>;
}) {
  return (
    <div
      style={{
        background: 'rgba(255,255,255,0.02)',
        border: `1px solid ${PANEL_BORDER}`,
        borderRadius: 8,
        padding: '10px 12px',
      }}
    >
      <div
        style={{
          fontFamily: 'Inter, sans-serif',
          fontSize: 11,
          fontWeight: 600,
          color: '#EEF3FF',
          marginBottom: 8,
        }}
      >
        {label}
      </div>
      {results.length === 0 ? (
        <div
          style={{
            fontFamily: 'Inter, sans-serif',
            fontSize: 11,
            color: '#6B7480',
          }}
        >
          No results in the top five.
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {results.map((result, index) => (
            <div key={`${label}-${result.docId}-${index}`}>
              <div
                style={{
                  fontFamily: 'Inter, sans-serif',
                  fontSize: 11,
                  fontWeight: 600,
                  color: '#EEF3FF',
                  marginBottom: 2,
                }}
              >
                #{index + 1} {result.title}
              </div>
              <div
                style={{
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: 9,
                  color: '#4B5563',
                  marginBottom: result.excerpt ? 2 : 0,
                }}
              >
                {result.docId} · score {result.score.toFixed(3)}
              </div>
              {result.excerpt && (
                <div
                  style={{
                    fontFamily: 'Inter, sans-serif',
                    fontSize: 10,
                    color: '#9AA4B2',
                    lineHeight: 1.45,
                  }}
                >
                  {result.excerpt}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function QueryBreakdown({ runId, rows }: QueryBreakdownProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [previewCache, setPreviewCache] = useState<Record<string, QueryPreviewPayload>>({});
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  if (!rows || rows.length === 0) return null;

  const handleToggle = async (queryId: string) => {
    if (expandedId === queryId) {
      setExpandedId(null);
      return;
    }
    setExpandedId(queryId);
    if (previewCache[queryId]) {
      return;
    }
    setLoadingId(queryId);
    try {
      const preview = await api.previewQuery(runId, queryId);
      setPreviewCache(current => ({ ...current, [queryId]: preview }));
    } catch {
      // Fall back to report-embedded data.
    } finally {
      setLoadingId(current => (current === queryId ? null : current));
    }
  };

  const handleCopyQuery = async (queryId: string) => {
    const preview = previewCache[queryId];
    const row = rows.find(item => item.queryId === queryId);
    const payload = preview?.optimizedQueryDsl ?? {
      size: 5,
      query: {
        multi_match: {
          query: row?.query ?? 'example query',
          fields: [],
          type: 'best_fields',
          minimum_should_match: '75%',
        },
      },
    };
    await navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
    setCopiedId(queryId);
    setTimeout(() => setCopiedId(current => (current === queryId ? null : current)), 1500);
  };

  return (
    <div style={{ marginBottom: 32 }}>
      <h2
        style={{
          fontFamily: 'Inter, sans-serif',
          fontWeight: 600,
          fontSize: 17,
          color: '#EEF3FF',
          marginBottom: 6,
        }}
      >
        Per-Query Breakdown
      </h2>
      <p
        style={{
          fontFamily: 'Inter, sans-serif',
          fontSize: 12,
          color: '#6B7480',
          marginBottom: 14,
          lineHeight: 1.5,
        }}
      >
        Expand any query to compare the top five results before and after optimization.
      </p>

      <div
        style={{
          border: `1px solid ${PANEL_BORDER}`,
          borderRadius: 8,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: '1fr 70px 90px 90px 90px',
            gap: 8,
            padding: '8px 14px',
            background: 'rgba(255,255,255,0.03)',
            borderBottom: `1px solid ${PANEL_BORDER}`,
          }}
        >
          {['Query', 'Difficulty', 'Before', 'After', 'Change'].map((heading, index) => (
            <span
              key={heading}
              style={{
                fontFamily: 'Inter, sans-serif',
                fontSize: 10,
                fontWeight: 600,
                color: '#6B7480',
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                textAlign: index >= 2 ? 'right' : 'left',
              }}
            >
              {heading}
            </span>
          ))}
        </div>

        {rows.map((row) => {
          const improved = row.deltaPct > 1;
          const degraded = row.deltaPct < -1;
          const expanded = expandedId === row.queryId;
          return (
            <div key={row.queryId}>
              <button
                type="button"
                onClick={() => {
                  void handleToggle(row.queryId);
                }}
                style={{
                  width: '100%',
                  display: 'grid',
                  gridTemplateColumns: '1fr 70px 90px 90px 90px',
                  gap: 8,
                  padding: '10px 14px',
                  border: 'none',
                  borderBottom: `1px solid ${PANEL_BORDER}`,
                  background: expanded ? 'rgba(77,163,255,0.04)' : 'transparent',
                  textAlign: 'left',
                  cursor: 'pointer',
                  alignItems: 'center',
                }}
              >
                <div>
                  <div
                    style={{
                      fontFamily: 'Inter, sans-serif',
                      fontSize: 12,
                      color: '#EEF3FF',
                      marginBottom: 2,
                    }}
                  >
                    {row.query}
                  </div>
                  {row.topRelevantDocIds.length > 0 && (
                    <div
                      style={{
                        fontFamily: 'JetBrains Mono, monospace',
                        fontSize: 9,
                        color: '#4B5563',
                      }}
                    >
                      Expected docs: {row.topRelevantDocIds.slice(0, 3).join(', ')}
                    </div>
                  )}
                  {row.failureReason && (
                    <div
                      style={{
                        marginTop: 4,
                        fontFamily: 'Inter, sans-serif',
                        fontSize: 10,
                        color: '#FBBF24',
                        lineHeight: 1.45,
                      }}
                    >
                      {row.failureReason}
                    </div>
                  )}
                </div>

                <span
                  style={{
                    fontFamily: 'Inter, sans-serif',
                    fontSize: 10,
                    fontWeight: 500,
                    color: difficultyColor(row.difficulty),
                    textTransform: 'capitalize',
                  }}
                >
                  {row.difficulty}
                </span>

                <span
                  style={{
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: 12,
                    color: scoreColor(row.baselineScore),
                    textAlign: 'right',
                  }}
                >
                  {row.baselineScore.toFixed(3)}
                </span>

                <span
                  style={{
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: 12,
                    color: scoreColor(row.bestScore),
                    textAlign: 'right',
                    fontWeight: improved ? 600 : 400,
                  }}
                >
                  {row.bestScore.toFixed(3)}
                </span>

                <span
                  style={{
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: 11,
                    fontWeight: 600,
                    textAlign: 'right',
                    color: improved ? '#4ADE80' : degraded ? '#FB7185' : '#6B7480',
                  }}
                >
                  {row.deltaPct > 0 ? '+' : ''}
                  {row.deltaPct.toFixed(1)}%
                </span>
              </button>

              {expanded && (
                <div
                  style={{
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 12,
                    padding: '12px 14px 14px',
                    borderBottom: `1px solid ${PANEL_BORDER}`,
                    background: 'rgba(255,255,255,0.015)',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
                    <div
                      style={{
                        fontFamily: 'Inter, sans-serif',
                        fontSize: 11,
                        color: '#9AA4B2',
                      }}
                    >
                      {loadingId === row.queryId ? 'Loading live preview…' : 'Showing before/after top results for this query.'}
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        void handleCopyQuery(row.queryId);
                      }}
                      style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 6,
                        padding: '6px 10px',
                        borderRadius: 7,
                        border: `1px solid ${PANEL_BORDER}`,
                        background: 'transparent',
                        color: copiedId === row.queryId ? '#4ADE80' : '#9AA4B2',
                        fontFamily: 'Inter, sans-serif',
                        fontSize: 11,
                        cursor: 'pointer',
                      }}
                    >
                      <Copy size={12} />
                      {copiedId === row.queryId ? 'Copied query' : 'Copy ES query'}
                    </button>
                  </div>

                  {loadingId === row.queryId && !previewCache[row.queryId] ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: '#6B7480', fontFamily: 'Inter, sans-serif', fontSize: 11 }}>
                      <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />
                      Fetching live preview…
                    </div>
                  ) : (
                    <div
                      style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
                        gap: 12,
                      }}
                    >
                      <ResultCard label="Before" results={previewCache[row.queryId]?.baselineResults ?? row.baselineTopResults ?? []} />
                      <ResultCard label="After" results={previewCache[row.queryId]?.optimizedResults ?? row.bestTopResults ?? []} />
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
