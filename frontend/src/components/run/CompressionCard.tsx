import React, { memo } from 'react';
import type { CompressionSummary, CompressionMethodResult } from '@/types/contracts';
import { formatBytes, formatDollars, formatPercent } from '@/lib/format';
import { PANEL_BORDER } from '@/lib/theme';

interface CompressionCardProps {
  compression: CompressionSummary;
}

const METHOD_LABELS: Record<string, string> = {
  float32: 'float32',
  int8: 'INT8',
  int4: 'INT4',
  rotated_int4: 'Rotated INT4',
};

function MethodRow({
  method,
  isBest,
}: {
  method: CompressionMethodResult;
  isBest: boolean;
}) {
  const barWidth = Math.min(100, method.sizeReductionPct);
  const recallColor =
    method.recallAt10 >= 0.95
      ? '#4ADE80'
      : method.recallAt10 >= 0.90
      ? '#FBBF24'
      : '#FB7185';

  if (method.status === 'skipped' || method.status === 'error') {
    return (
      <div
        style={{
          padding: '7px 10px',
          borderBottom: `1px solid ${PANEL_BORDER}`,
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          opacity: 0.45,
        }}
      >
        <span
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 10,
            color: '#9AA4B2',
            minWidth: 90,
          }}
        >
          {METHOD_LABELS[method.method] ?? method.method}
        </span>
        <span
          style={{
            fontFamily: 'Inter, sans-serif',
            fontSize: 10,
            color: '#4B5563',
            fontStyle: 'italic',
          }}
        >
          {method.status}
        </span>
      </div>
    );
  }

  return (
    <div
      style={{
        padding: '8px 10px',
        borderBottom: `1px solid ${PANEL_BORDER}`,
        background: isBest ? 'rgba(74,222,128,0.04)' : 'transparent',
        borderLeft: isBest
          ? '2px solid rgba(74,222,128,0.4)'
          : '2px solid transparent',
        transition: 'background 0.2s',
      }}
    >
      {/* Method header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: 5,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 10,
              fontWeight: 600,
              color: isBest ? '#4ADE80' : '#9AA4B2',
              padding: '1px 5px',
              borderRadius: 3,
              background: isBest
                ? 'rgba(74,222,128,0.1)'
                : 'rgba(255,255,255,0.05)',
              border: `1px solid ${isBest ? 'rgba(74,222,128,0.25)' : 'rgba(255,255,255,0.08)'}`,
            }}
          >
            {METHOD_LABELS[method.method] ?? method.method}
          </span>
          {isBest && (
            <span
              style={{
                fontFamily: 'Inter, sans-serif',
                fontSize: 9,
                color: '#4ADE80',
                fontWeight: 600,
              }}
            >
              ✓ BEST
            </span>
          )}
        </div>
        <span
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 10,
            color: '#6B7480',
          }}
        >
          {formatBytes(method.sizeBytes)}
        </span>
      </div>

      {/* Savings bar */}
      <div
        style={{
          height: 3,
          background: 'rgba(255,255,255,0.06)',
          borderRadius: 2,
          overflow: 'hidden',
          marginBottom: 5,
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${barWidth}%`,
            background: isBest
              ? '#4ADE80'
              : 'rgba(77,163,255,0.7)',
            borderRadius: 2,
            transition: 'width 0.8s ease',
          }}
        />
      </div>

      {/* Stats row */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          justifyContent: 'space-between',
        }}
      >
        <span
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 9,
            color: '#6B7480',
          }}
        >
          {method.sizeReductionPct.toFixed(0)}% smaller
        </span>
        <span
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 9,
            color: recallColor,
          }}
        >
          {(method.recallAt10 * 100).toFixed(1)}% recall
        </span>
        <span
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 9,
            color: '#9AA4B2',
          }}
        >
          {formatDollars(method.estimatedMonthlyCostUsd)}/mo
        </span>
      </div>
    </div>
  );
}

function CompressionCard({ compression }: CompressionCardProps) {
  if (!compression.available) {
    return (
      <div
        style={{
          padding: '14px 12px',
          fontFamily: 'Inter, sans-serif',
          fontSize: 11,
          color: '#4B5563',
          fontStyle: 'italic',
          textAlign: 'center',
        }}
      >
        No retrievable vector field detected
      </div>
    );
  }

  const bestMethod = compression.bestRecommendation;

  return (
    <div>
      {/* Methods list */}
      {compression.methods.map(m => (
        <MethodRow
          key={m.method}
          method={m}
          isBest={m.method === bestMethod}
        />
      ))}

      {/* Footer: projected savings */}
      {compression.projectedMonthlySavingsUsd != null &&
        compression.projectedMonthlySavingsUsd > 0 && (
          <div
            style={{
              padding: '8px 12px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              borderTop: `1px solid ${PANEL_BORDER}`,
            }}
          >
            <span
              style={{
                fontFamily: 'Inter, sans-serif',
                fontSize: 10,
                color: '#6B7480',
              }}
            >
              Projected savings
            </span>
            <span
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 13,
                fontWeight: 600,
                color: '#4ADE80',
                textShadow: '0 0 8px rgba(74,222,128,0.4)',
              }}
            >
              {formatDollars(compression.projectedMonthlySavingsUsd)}/mo
            </span>
          </div>
        )}

      {/* If still running */}
      {compression.status === 'running' && (
        <div
          style={{
            padding: '6px 12px',
            fontFamily: 'Inter, sans-serif',
            fontSize: 10,
            color: '#4DA3FF',
            fontStyle: 'italic',
          }}
        >
          Benchmarking in progress…
        </div>
      )}
    </div>
  );
}

export default memo(CompressionCard);
