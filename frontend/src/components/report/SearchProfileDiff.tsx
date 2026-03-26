import React, { useState } from 'react';
import type { SearchProfile, SearchProfileChange } from '@/types/contracts';
import { PANEL_BORDER } from '@/lib/theme';

interface SearchProfileDiffProps {
  before: SearchProfile;
  after: SearchProfile;
  diff: SearchProfileChange[];
}

function formatValue(val: unknown): string {
  if (val === null || val === undefined) return '—';
  if (typeof val === 'object') return JSON.stringify(val);
  return String(val);
}

function DiffRow({ change }: { change: SearchProfileChange }) {
  const improved =
    typeof change.after === 'number' &&
    typeof change.before === 'number'
      ? change.after > change.before
      : change.after !== change.before;

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '200px 1fr auto 1fr',
        alignItems: 'center',
        gap: 12,
        padding: '8px 14px',
        borderBottom: `1px solid ${PANEL_BORDER}`,
      }}
    >
      <span
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 11,
          color: '#9AA4B2',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}
      >
        {change.path}
      </span>
      <span
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 12,
          color: '#FB7185',
          background: 'rgba(251,113,133,0.06)',
          padding: '3px 8px',
          borderRadius: 4,
          textAlign: 'right',
        }}
      >
        {formatValue(change.before)}
      </span>
      <span
        style={{
          color: '#4B5563',
          fontSize: 11,
        }}
      >
        →
      </span>
      <span
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 12,
          color: improved ? '#4ADE80' : '#FBBF24',
          background: improved
            ? 'rgba(74,222,128,0.06)'
            : 'rgba(251,191,36,0.06)',
          padding: '3px 8px',
          borderRadius: 4,
        }}
      >
        {formatValue(change.after)}
      </span>
    </div>
  );
}

export default function SearchProfileDiff({ before, after, diff }: SearchProfileDiffProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(JSON.stringify(after, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
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
        Search Profile Changes
      </h2>

      {diff.length === 0 ? (
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
          No changes from baseline — current profile already optimal.
        </div>
      ) : (
        <div
          style={{
            border: `1px solid ${PANEL_BORDER}`,
            borderRadius: 8,
            overflow: 'hidden',
            marginBottom: 20,
          }}
        >
          {/* Header */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '200px 1fr auto 1fr',
              gap: 12,
              padding: '8px 14px',
              background: 'rgba(255,255,255,0.03)',
              borderBottom: `1px solid ${PANEL_BORDER}`,
            }}
          >
            {['Parameter', 'Before', '', 'After'].map((h, i) => (
              <span
                key={i}
                style={{
                  fontFamily: 'Inter, sans-serif',
                  fontSize: 10,
                  fontWeight: 600,
                  color: '#6B7480',
                  textTransform: 'uppercase',
                  letterSpacing: '0.08em',
                  textAlign: i === 1 ? 'right' : 'left',
                }}
              >
                {h}
              </span>
            ))}
          </div>
          {diff.map(change => (
            <DiffRow key={change.path} change={change} />
          ))}
        </div>
      )}

      {/* Full recommended profile */}
      <div>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 12,
            marginBottom: 10,
          }}
        >
          <h3
            style={{
              fontFamily: 'Inter, sans-serif',
              fontWeight: 500,
              fontSize: 13,
              color: '#9AA4B2',
              margin: 0,
              minWidth: 0,
              flexShrink: 1,
            }}
          >
            Recommended Profile (copy to use)
          </h3>
          <button
            onClick={handleCopy}
            style={{
              fontFamily: 'Inter, sans-serif',
              fontSize: 11,
              fontWeight: 500,
              padding: '5px 12px',
              background: 'rgba(77,163,255,0.08)',
              border: '1px solid rgba(77,163,255,0.2)',
              borderRadius: 6,
              color: copied ? '#4ADE80' : '#4DA3FF',
              cursor: 'pointer',
              transition: 'color 0.2s',
              flexShrink: 0,
              whiteSpace: 'nowrap',
            }}
          >
            {copied ? 'Copied!' : 'Copy JSON'}
          </button>
        </div>
        <pre
          style={{
            margin: 0,
            padding: '16px',
            background: 'rgba(5,7,11,0.7)',
            border: `1px solid ${PANEL_BORDER}`,
            borderRadius: 8,
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 11,
            color: '#9AA4B2',
            overflowX: 'auto',
            lineHeight: 1.6,
          }}
        >
          {JSON.stringify(after, null, 2)}
        </pre>
      </div>
    </div>
  );
}
