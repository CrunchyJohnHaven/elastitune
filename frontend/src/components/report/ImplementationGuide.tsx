import React from 'react';
import type {
  ReportCodeSnippet,
  ReportImplementationGuide as ReportImplementationGuideType,
  ReportSnippetLine,
} from '@/types/contracts';
import { PANEL_BORDER } from '@/lib/theme';

interface ImplementationGuideProps {
  guide?: ReportImplementationGuideType | null;
}

function SnippetBlock({
  lines,
  target,
  summary,
  tone,
}: {
  lines: ReportSnippetLine[];
  target: string;
  summary: string;
  tone: 'before' | 'after';
}) {
  const borderColor =
    tone === 'before' ? 'rgba(251,113,133,0.18)' : 'rgba(74,222,128,0.18)';
  const background =
    tone === 'before' ? 'rgba(251,113,133,0.04)' : 'rgba(74,222,128,0.04)';
  const titleColor = tone === 'before' ? '#FB7185' : '#4ADE80';

  return (
    <div
      style={{
        border: `1px solid ${borderColor}`,
        background,
        borderRadius: 10,
        padding: '10px 12px',
        minWidth: 0,
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          gap: 10,
          alignItems: 'baseline',
          marginBottom: 8,
          flexWrap: 'wrap',
        }}
      >
        <div
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 10,
            color: titleColor,
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
          }}
        >
          {tone === 'before' ? 'Before' : 'After'}
        </div>
        <div
          style={{
            fontFamily: 'Inter, sans-serif',
            fontSize: 11,
            color: '#9AA4B2',
          }}
        >
          {summary || target}
        </div>
      </div>

      <div
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 11,
          color: '#EEF3FF',
          lineHeight: 1.6,
          display: 'grid',
          gap: 4,
        }}
      >
        {lines.length > 0 ? (
          lines.map((line) => (
            <div
              key={`${tone}-${line.lineNumber}-${line.content}`}
              style={{
                display: 'grid',
                gridTemplateColumns: '52px 1fr',
                gap: 10,
                alignItems: 'start',
              }}
            >
              <div
                style={{
                  color: '#6B7480',
                  textAlign: 'right',
                  paddingRight: 4,
                  userSelect: 'none',
                }}
              >
                {line.lineNumber}
              </div>
              <div
                style={{
                  color: line.changed ? titleColor : '#D7DEE8',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  background: line.changed
                    ? 'rgba(255,255,255,0.03)'
                    : 'transparent',
                }}
              >
                {line.content || ' '}
                {line.explanation && (
                  <div
                    style={{
                      marginTop: 4,
                      fontFamily: 'Inter, sans-serif',
                      fontSize: 10,
                      lineHeight: 1.45,
                      color: '#9AA4B2',
                    }}
                  >
                    {line.explanation}
                  </div>
                )}
              </div>
            </div>
          ))
        ) : (
          <div
            style={{
              color: '#6B7480',
              fontFamily: 'Inter, sans-serif',
              fontSize: 11,
            }}
          >
            No snippet lines were supplied.
          </div>
        )}
      </div>
    </div>
  );
}

export default function ImplementationGuide({ guide }: ImplementationGuideProps) {
  const snippets = guide?.snippets ?? [];
  if (!guide || snippets.length === 0) return null;

  return (
    <div style={{ marginBottom: 32 }}>
      <h2
        style={{
          fontFamily: 'Inter, sans-serif',
          fontWeight: 600,
          fontSize: 17,
          color: '#EEF3FF',
          marginBottom: 10,
        }}
      >
        Implementation Guide
      </h2>

      <div
        style={{
          padding: '14px 16px',
          borderRadius: 12,
          border: `1px solid ${PANEL_BORDER}`,
          background: 'rgba(255,255,255,0.025)',
          marginBottom: 14,
          fontFamily: 'Inter, sans-serif',
          fontSize: 13,
          lineHeight: 1.6,
          color: '#C5CDD8',
        }}
      >
        {guide.summary}
      </div>

      {guide.representativeQuery && (
        <div
          style={{
            marginBottom: 12,
            fontFamily: 'Inter, sans-serif',
            fontSize: 12,
            lineHeight: 1.6,
            color: '#9AA4B2',
          }}
        >
          Representative query:{' '}
          <span style={{ color: '#EEF3FF' }}>{guide.representativeQuery}</span>
        </div>
      )}

      {guide.applyInstructions.length > 0 && (
        <div
          style={{
            marginBottom: 14,
            display: 'grid',
            gap: 8,
          }}
        >
          {guide.applyInstructions.map((instruction, index) => (
            <div
              key={`${index}-${instruction}`}
              style={{
                display: 'grid',
                gridTemplateColumns: '22px 1fr',
                gap: 8,
                alignItems: 'start',
                fontFamily: 'Inter, sans-serif',
                fontSize: 12,
                lineHeight: 1.55,
                color: '#C5CDD8',
              }}
            >
              <div
                style={{
                  color: '#4DA3FF',
                  fontFamily: 'JetBrains Mono, monospace',
                }}
              >
                {index + 1}.
              </div>
              <div>{instruction}</div>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: 'grid', gap: 14 }}>
        {snippets.map((snippet: ReportCodeSnippet) => (
          <div
            key={`${snippet.target}-${snippet.title}`}
            style={{
              padding: '16px 18px',
              borderRadius: 12,
              border: `1px solid ${PANEL_BORDER}`,
              background: 'rgba(255,255,255,0.025)',
            }}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                gap: 14,
                alignItems: 'flex-start',
                flexWrap: 'wrap',
                marginBottom: 10,
              }}
            >
              <div style={{ minWidth: 0, flex: '1 1 360px' }}>
                <div
                  style={{
                    fontFamily: 'Inter, sans-serif',
                    fontSize: 12,
                    fontWeight: 700,
                    color: '#EEF3FF',
                    marginBottom: 4,
                  }}
                >
                  {snippet.title}
                </div>
                <div
                  style={{
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: 11,
                    color: '#7CE7FF',
                    wordBreak: 'break-word',
                  }}
                >
                  {snippet.target}
                </div>
              </div>
            </div>

            <div
              style={{
                fontFamily: 'Inter, sans-serif',
                fontSize: 13,
                lineHeight: 1.6,
                color: '#C5CDD8',
                marginBottom: 12,
              }}
            >
              {snippet.summary}
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
                gap: 12,
              }}
            >
              <SnippetBlock
                lines={snippet.beforeLines}
                target={snippet.target}
                summary={snippet.summary}
                tone="before"
              />
              <SnippetBlock
                lines={snippet.afterLines}
                target={snippet.target}
                summary={snippet.summary}
                tone="after"
              />
            </div>
          </div>
        ))}
      </div>

      {guide.note && (
        <div
          style={{
            marginTop: 14,
            fontFamily: 'Inter, sans-serif',
            fontSize: 11,
            lineHeight: 1.55,
            color: '#9AA4B2',
          }}
        >
          {guide.note}
        </div>
      )}
    </div>
  );
}
