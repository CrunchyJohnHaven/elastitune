import React, { memo, useEffect, useRef } from 'react';
import type { ExperimentRecord } from '@/types/contracts';
import { formatScore, formatPercent, formatTimestamp, truncate } from '@/lib/format';
import { PANEL_BORDER } from '@/lib/theme';

interface ExperimentFeedProps {
  experiments: ExperimentRecord[];
}

function DecisionBadge({ decision }: { decision: 'kept' | 'reverted' }) {
  const isKept = decision === 'kept';
  return (
    <span
      style={{
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: 9,
        fontWeight: 700,
        letterSpacing: '0.08em',
        padding: '2px 6px',
        borderRadius: 3,
        background: isKept ? 'rgba(74,222,128,0.12)' : 'rgba(251,113,133,0.12)',
        color: isKept ? '#4ADE80' : '#FB7185',
        border: `1px solid ${isKept ? 'rgba(74,222,128,0.25)' : 'rgba(251,113,133,0.25)'}`,
        flexShrink: 0,
      }}
    >
      {isKept ? 'KEPT' : 'REVERTED'}
    </span>
  );
}

const MAX_FEED_ITEMS = 24;

const ExperimentRow = memo(function ExperimentRow({ experiment }: { experiment: ExperimentRecord }) {
  const isKept = experiment.decision === 'kept';
  const deltaPositive = experiment.deltaAbsolute >= 0;
  const time = formatTimestamp(experiment.timestamp);

  return (
    <div
      style={{
        padding: '8px 12px',
        borderBottom: `1px solid ${PANEL_BORDER}`,
        borderLeft: `2px solid ${isKept ? 'rgba(74,222,128,0.4)' : 'rgba(251,113,133,0.3)'}`,
        background: isKept
          ? 'rgba(74,222,128,0.025)'
          : 'rgba(251,113,133,0.02)',
        cursor: 'default',
        transition: 'background 0.2s',
      }}
    >
      {/* Row 1: ID + time + label */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          marginBottom: 3,
          flexWrap: 'nowrap',
          overflow: 'hidden',
        }}
      >
        <span
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 10,
            color: '#6B7480',
            flexShrink: 0,
          }}
        >
          #{experiment.experimentId}
        </span>
        <span
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 10,
            color: '#6B7480',
            flexShrink: 0,
          }}
        >
          {time}
        </span>
        <span
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 10,
            color: '#9AA4B2',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            flex: 1,
          }}
        >
          {experiment.change.label}
        </span>
      </div>

      {/* Row 2: hypothesis */}
      <div
        style={{
          fontFamily: 'Inter, sans-serif',
          fontSize: 11,
          color: '#7A8494',
          marginBottom: 5,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          fontStyle: 'italic',
        }}
      >
        {truncate(experiment.hypothesis, 72)}
      </div>

      {/* Row 3: scores + badge */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          flexWrap: 'nowrap',
        }}
      >
        <span
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 11,
            color: '#9AA4B2',
          }}
        >
          {formatScore(experiment.baselineScore)}
        </span>
        <span style={{ color: '#4B5563', fontSize: 9 }}>→</span>
        <span
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 11,
            color: isKept ? '#4ADE80' : '#EEF3FF',
          }}
        >
          {formatScore(experiment.candidateScore)}
        </span>
        <span
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 10,
            color: deltaPositive ? '#4ADE80' : '#FB7185',
            marginLeft: 2,
          }}
        >
          {formatPercent(experiment.deltaPercent)}
        </span>
        <div style={{ flex: 1 }} />
        <DecisionBadge decision={experiment.decision} />
      </div>
    </div>
  );
});

export default function ExperimentFeed({ experiments }: ExperimentFeedProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const prevLengthRef = useRef(0);

  // Auto-scroll to top when new experiments arrive (newest is at top)
  useEffect(() => {
    if (experiments.length > prevLengthRef.current) {
      const el = scrollRef.current;
      if (el) {
        el.scrollTop = 0;
      }
    }
    prevLengthRef.current = experiments.length;
  }, [experiments.length]);

  const reversed = experiments.slice(-MAX_FEED_ITEMS).reverse();

  return (
    <div
      ref={scrollRef}
      style={{
        flex: 1,
        overflowY: 'auto',
        overflowX: 'hidden',
        scrollbarWidth: 'thin',
        scrollbarColor: 'rgba(255,255,255,0.08) transparent',
      }}
    >
      {experiments.length === 0 ? (
        <div
          style={{
            padding: '24px 16px',
            textAlign: 'center',
            fontFamily: 'Inter, sans-serif',
            fontSize: 12,
            color: '#4B5563',
            fontStyle: 'italic',
          }}
        >
          Waiting for first experiment...
        </div>
      ) : (
        reversed.map(exp => (
          <ExperimentRow key={exp.experimentId} experiment={exp} />
        ))
      )}
    </div>
  );
}
