import React, { memo, useEffect, useState } from 'react';
import type { ConnectionSummary, HeroMetrics, SearchProfile } from '@/types/contracts';
import { formatDocCount, formatDuration, truncate, getDisplayElapsedSeconds } from '@/lib/format';
import { PANEL_BORDER } from '@/lib/theme';

interface IndexSummaryMiniCardProps {
  summary: ConnectionSummary;
  metrics: HeroMetrics;
  mode: 'demo' | 'live';
  profile: SearchProfile;
  stage?: string;
  startedAt?: string | null;
  completedAt?: string | null;
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        gap: 8,
        padding: '4px 0',
        borderBottom: `1px solid rgba(255,255,255,0.03)`,
      }}
    >
      <span
        style={{
          fontFamily: 'Inter, sans-serif',
          fontSize: 10,
          color: '#6B7480',
          flexShrink: 0,
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 10,
          color: '#9AA4B2',
          textAlign: 'right',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          maxWidth: 160,
        }}
      >
        {value}
      </span>
    </div>
  );
}

function IndexSummaryMiniCard({
  summary,
  metrics,
  mode,
  profile,
  stage,
  startedAt,
  completedAt,
}: IndexSummaryMiniCardProps) {
  const [, forceUpdate] = useState(0);
  useEffect(() => {
    const t = setInterval(() => forceUpdate(n => n + 1), 1000);
    return () => clearInterval(t);
  }, []);

  const searchMode = profile.useVector
    ? 'Hybrid (Lexical + Vector)'
    : 'Lexical Only';

  const textFields = summary.primaryTextFields.join(', ') || '—';
  const vectorField = summary.vectorField
    ? `${summary.vectorField}${summary.vectorDims ? ` (${summary.vectorDims}d)` : ''}`
    : 'None';

  return (
    <div style={{ padding: '10px 12px' }}>
      {/* Cluster name / mode */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 8,
        }}
      >
        <span
          style={{
            fontFamily: 'Inter, sans-serif',
            fontWeight: 600,
            fontSize: 12,
            color: '#EEF3FF',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {mode === 'demo' ? 'Demo Mode' : truncate(summary.clusterName, 22)}
        </span>
        <span
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 9,
            fontWeight: 600,
            padding: '2px 6px',
            borderRadius: 3,
            background:
              mode === 'demo'
                ? 'rgba(251,191,36,0.12)'
                : 'rgba(74,222,128,0.1)',
            color: mode === 'demo' ? '#FBBF24' : '#4ADE80',
            border: `1px solid ${mode === 'demo' ? 'rgba(251,191,36,0.25)' : 'rgba(74,222,128,0.2)'}`,
            flexShrink: 0,
          }}
        >
          {mode.toUpperCase()}
        </span>
      </div>

      <InfoRow label="Index" value={truncate(summary.indexName, 22)} />
      <InfoRow label="Docs" value={formatDocCount(summary.docCount)} />
      <InfoRow label="Text fields" value={truncate(textFields, 24)} />
      <InfoRow label="Vector field" value={vectorField} />
      <InfoRow
        label="Elapsed"
        value={formatDuration(
          getDisplayElapsedSeconds({
            metricsElapsedSeconds: metrics.elapsedSeconds,
            startedAt,
            completedAt,
            stage,
          })
        )}
      />
      <InfoRow label="Search mode" value={searchMode} />
    </div>
  );
}

export default memo(IndexSummaryMiniCard);
