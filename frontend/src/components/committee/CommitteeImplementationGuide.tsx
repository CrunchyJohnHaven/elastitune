import React from 'react';
import type {
  CommitteeCodeLine,
  CommitteeCodeSnippet,
  CommitteeExportPayload,
  CommitteeImplementationGuide as CommitteeImplementationGuideType,
} from '@/types/committee';
import { PANEL_BORDER } from '@/lib/theme';

interface CommitteeImplementationGuideProps {
  guide?: CommitteeImplementationGuideType | null;
  sections: CommitteeExportPayload['sections'];
  actionableFeedback?: CommitteeExportPayload['llmHandoff']['actionableSectionFeedback'];
}

function splitLines(text: string): CommitteeCodeLine[] {
  return text.split(/\r?\n/).map((content, index) => ({
    lineNumber: index + 1,
    content,
    changed: false,
  }));
}

function buildLineDiff(before: string, after: string) {
  const beforeLines = splitLines(before);
  const afterLines = splitLines(after);

  let start = 0;
  while (
    start < beforeLines.length &&
    start < afterLines.length &&
    beforeLines[start].content === afterLines[start].content
  ) {
    start += 1;
  }

  let beforeEnd = beforeLines.length - 1;
  let afterEnd = afterLines.length - 1;
  while (
    beforeEnd >= start &&
    afterEnd >= start &&
    beforeLines[beforeEnd].content === afterLines[afterEnd].content
  ) {
    beforeEnd -= 1;
    afterEnd -= 1;
  }

  return {
    before: beforeLines.map((line, index) => ({
      ...line,
      changed: index >= start && index <= beforeEnd,
      explanation:
        index >= start && index <= beforeEnd
          ? 'This line was replaced or removed in the accepted rewrite.'
          : undefined,
    })),
    after: afterLines.map((line, index) => ({
      ...line,
      changed: index >= start && index <= afterEnd,
      explanation:
        index >= start && index <= afterEnd
          ? 'This line appears in the accepted rewrite.'
          : undefined,
    })),
  };
}

function SnippetBlock({
  lines,
  tone,
  summary,
}: {
  lines: CommitteeCodeLine[];
  tone: 'before' | 'after';
  summary: string;
}) {
  const borderColor =
    tone === 'before' ? 'rgba(251,113,133,0.18)' : 'rgba(74,222,128,0.18)';
  const background =
    tone === 'before' ? 'rgba(251,113,133,0.04)' : 'rgba(74,222,128,0.04)';
  const accent = tone === 'before' ? '#FB7185' : '#4ADE80';

  return (
    <div
      style={{
        border: `1px solid ${borderColor}`,
        background,
        borderRadius: 10,
        padding: '10px 12px',
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
            color: accent,
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
          }}
        >
          {tone === 'before' ? 'Before' : 'After'}
        </div>
        <div
          style={{ fontFamily: 'Inter, sans-serif', fontSize: 11, color: '#9AA4B2' }}
        >
          {summary}
        </div>
      </div>

      <div
        style={{
          display: 'grid',
          gap: 4,
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 11,
          lineHeight: 1.6,
          color: '#EEF3FF',
        }}
      >
        {lines.length > 0 ? (
          lines.map((line) => (
            <div
              key={`${tone}-${line.lineNumber}-${line.content}`}
              style={{
                display: 'grid',
                gridTemplateColumns: '46px 1fr',
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
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  color: line.changed ? accent : '#D7DEE8',
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

export default function CommitteeImplementationGuide({
  guide,
  sections,
  actionableFeedback = [],
}: CommitteeImplementationGuideProps) {
  const snippets: CommitteeCodeSnippet[] =
    guide?.snippets && guide.snippets.length > 0
      ? guide.snippets
      : sections.map((section) => {
          const diff = buildLineDiff(section.originalContent, section.optimizedContent);
          return {
            title: section.title,
            target: `Section ${section.sectionId}`,
            format: 'text',
            summary: 'A line-numbered before/after view of the rewritten section.',
            beforeLines: diff.before,
            afterLines: diff.after,
          };
        });

  if (snippets.length === 0) return null;

  const highlightMap = new Map(
    actionableFeedback
      .filter((item) => typeof item.sectionId === 'number')
      .map((item) => [item.sectionId as number, item]),
  );

  const orderedSnippets = snippets
    .slice()
    .sort((a, b) => {
      const aId = Number(a.target.replace(/[^0-9]/g, ''));
      const bId = Number(b.target.replace(/[^0-9]/g, ''));
      const aNumeric = Number.isFinite(aId);
      const bNumeric = Number.isFinite(bId);
      const aHit = aNumeric && highlightMap.has(aId) ? 1 : 0;
      const bHit = bNumeric && highlightMap.has(bId) ? 1 : 0;
      if (aHit !== bHit) return bHit - aHit;
      if (aNumeric && bNumeric) return aId - bId;
      return 0;
    })
    .slice(0, 6);

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
        Rewrite Guide
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
        {guide?.summary ||
          'This section shows the most important before/after document changes in a line-numbered format so a reader can quickly see what changed and how to apply it.'}
      </div>

      {guide?.applyInstructions && guide.applyInstructions.length > 0 && (
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
        {orderedSnippets.map((snippet) => (
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
                summary={snippet.summary}
                tone="before"
              />
              <SnippetBlock
                lines={snippet.afterLines}
                summary={snippet.summary}
                tone="after"
              />
            </div>
          </div>
        ))}
      </div>

      {guide?.note && (
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
