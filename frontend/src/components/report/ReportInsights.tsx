import React from 'react';
import type {
  ReportChangeNarrative,
  ReportNarrativeSection,
  ReportPersonaSummary,
  ReportValidationNote,
} from '@/types/contracts';
import { PANEL_BORDER } from '@/lib/theme';

interface ReportInsightsProps {
  narrative?: ReportNarrativeSection[] | null;
  personaSummary?: ReportPersonaSummary | null;
  changeNarratives?: ReportChangeNarrative[] | null;
  validationNotes?: ReportValidationNote[];
  confidence?: number | null;
  personaCount?: number | null;
}

function confidenceLabel(value?: number | null): string {
  if (value == null || Number.isNaN(value)) return 'Confidence not provided';
  const normalized = value <= 1 ? value * 100 : value;
  return `${Math.max(0, Math.min(100, Math.round(normalized)))}% confidence`;
}

function confidenceTone(value?: number | null): string {
  if (value == null || Number.isNaN(value)) return '#9AA4B2';
  const normalized = value <= 1 ? value * 100 : value;
  if (normalized >= 85) return '#4ADE80';
  if (normalized >= 65) return '#FBBF24';
  return '#FB7185';
}

function noteColor(severity: ReportValidationNote['severity']): { border: string; bg: string; text: string } {
  switch (severity) {
    case 'success':
      return { border: 'rgba(74,222,128,0.24)', bg: 'rgba(74,222,128,0.05)', text: '#4ADE80' };
    case 'warning':
      return { border: 'rgba(251,191,36,0.24)', bg: 'rgba(251,191,36,0.05)', text: '#FBBF24' };
    default:
      return { border: 'rgba(77,163,255,0.24)', bg: 'rgba(77,163,255,0.05)', text: '#4DA3FF' };
  }
}

export default function ReportInsights({
  narrative,
  personaSummary,
  changeNarratives,
  validationNotes,
  confidence,
  personaCount,
}: ReportInsightsProps) {
  const sections = narrative ?? [];
  const leadSection = sections[0];
  const supportingSections = sections.slice(1);
  const effectivePersonaCount = personaSummary?.personaCount ?? personaCount ?? 0;
  const archetypeEntries = Object.entries(personaSummary?.archetypeCounts ?? {});
  const renderedChangeNarratives = changeNarratives ?? [];

  const hasMetadata = confidence != null || personaCount != null;

  if (!leadSection && sections.length === 0 && !personaSummary && (!validationNotes || validationNotes.length === 0) && renderedChangeNarratives.length === 0 && !hasMetadata) {
    return null;
  }
  const confidenceValue = leadSection?.confidence ?? confidence ?? null;

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
        Plain-English Summary
      </h2>

      <div
        style={{
          padding: '18px 20px',
          borderRadius: 12,
          background: 'linear-gradient(180deg, rgba(77,163,255,0.07), rgba(255,255,255,0.02))',
          border: '1px solid rgba(77,163,255,0.15)',
          marginBottom: 14,
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 12,
            flexWrap: 'wrap',
            marginBottom: 10,
          }}
        >
          <div
            style={{
              fontFamily: 'Inter, sans-serif',
              fontSize: 12,
              fontWeight: 700,
              color: '#EEF3FF',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
            }}
          >
            What this run means
          </div>
          <div
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 11,
              color: confidenceTone(confidenceValue),
            }}
          >
            {confidenceLabel(confidenceValue)}
            {effectivePersonaCount > 0 ? ` · ${effectivePersonaCount} personas` : ''}
          </div>
        </div>
        <div
          style={{
            fontFamily: 'Inter, sans-serif',
            fontSize: 14,
            lineHeight: 1.7,
            color: '#D7DEE8',
          }}
        >
          {leadSection?.body || (hasMetadata
            ? 'This run includes confidence or persona metadata, but the backend did not send the full narrative text yet. The metrics and technical sections below still show what happened.'
            : 'No narrative was provided for this run, so the summary below falls back to the raw report metrics.')}
        </div>
      </div>

      {supportingSections.length > 0 && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: 12,
            marginBottom: 14,
          }}
        >
          {supportingSections.map((section) => (
            <div
              key={section.key}
              style={{
                padding: '14px 16px',
                borderRadius: 10,
                border: `1px solid ${PANEL_BORDER}`,
                background:
                  section.audience === 'technical'
                    ? 'rgba(77,163,255,0.04)'
                    : section.audience === 'operator'
                    ? 'rgba(74,222,128,0.03)'
                    : 'rgba(255,255,255,0.025)',
              }}
            >
              <div
                style={{
                  fontFamily: 'Inter, sans-serif',
                  fontSize: 12,
                  fontWeight: 700,
                  color: '#EEF3FF',
                  marginBottom: 8,
                }}
              >
                {section.title}
              </div>
              <div
                style={{
                  fontFamily: 'Inter, sans-serif',
                  fontSize: 13,
                  lineHeight: 1.6,
                  color: '#C5CDD8',
                  whiteSpace: 'pre-wrap',
                }}
              >
                {section.body}
              </div>
            </div>
          ))}
        </div>
      )}

      {(personaSummary || renderedChangeNarratives.length > 0 || (validationNotes && validationNotes.length > 0)) && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: 14,
          }}
        >
          {personaSummary && (
            <div
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
                  alignItems: 'baseline',
                  justifyContent: 'space-between',
                  gap: 12,
                  marginBottom: 8,
                }}
              >
                <div
                  style={{
                    fontFamily: 'Inter, sans-serif',
                    fontSize: 12,
                    fontWeight: 700,
                    color: '#EEF3FF',
                    textTransform: 'uppercase',
                    letterSpacing: '0.08em',
                  }}
                >
                  Personas used
                </div>
                <div
                  style={{
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: 11,
                    color: '#7CE7FF',
                  }}
                >
                  {effectivePersonaCount} total
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
                {personaSummary.explanation}
              </div>
              {personaSummary.topRoles.length > 0 && (
                <div
                  style={{
                    padding: '10px 12px',
                    borderRadius: 8,
                    background: 'rgba(77,163,255,0.06)',
                    border: '1px solid rgba(77,163,255,0.12)',
                    color: '#CFE9FF',
                    fontFamily: 'Inter, sans-serif',
                    fontSize: 12,
                    lineHeight: 1.5,
                    marginBottom: 12,
                  }}
                >
                  Top roles represented: {personaSummary.topRoles.join(', ')}
                </div>
              )}
              <div style={{ display: 'grid', gap: 10 }}>
                {archetypeEntries.length > 0 ? archetypeEntries.map(([archetype, count]) => (
                  <div
                    key={archetype}
                    style={{
                      padding: '10px 12px',
                      borderRadius: 8,
                      background: 'rgba(255,255,255,0.02)',
                      border: `1px solid ${PANEL_BORDER}`,
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'baseline',
                        justifyContent: 'space-between',
                        gap: 10,
                        marginBottom: 4,
                      }}
                    >
                      <div
                        style={{
                          fontFamily: 'Inter, sans-serif',
                          fontSize: 12,
                          fontWeight: 600,
                          color: '#EEF3FF',
                        }}
                      >
                        {archetype}
                      </div>
                      <div
                        style={{
                          fontFamily: 'JetBrains Mono, monospace',
                          fontSize: 10,
                          color: '#9AA4B2',
                        }}
                      >
                        {count}
                      </div>
                    </div>
                    <div
                      style={{
                        fontFamily: 'Inter, sans-serif',
                        fontSize: 11,
                        lineHeight: 1.5,
                        color: '#9AA4B2',
                      }}
                    >
                      Simulated personas in this archetype were used to test whether the tuned profile helps more than one style of search behavior.
                    </div>
                  </div>
                )) : (
                  <div
                    style={{
                      fontFamily: 'Inter, sans-serif',
                      fontSize: 11,
                      lineHeight: 1.5,
                      color: '#9AA4B2',
                    }}
                  >
                    Detailed persona category counts were not provided for this run.
                  </div>
                )}
              </div>
            </div>
          )}

          {renderedChangeNarratives.length > 0 && (
            <div
              style={{
                padding: '16px 18px',
                borderRadius: 12,
                border: `1px solid ${PANEL_BORDER}`,
                background: 'rgba(255,255,255,0.025)',
              }}
            >
              <div
                style={{
                  fontFamily: 'Inter, sans-serif',
                  fontSize: 12,
                  fontWeight: 700,
                  color: '#EEF3FF',
                  textTransform: 'uppercase',
                  letterSpacing: '0.08em',
                  marginBottom: 10,
                }}
              >
                What changed and why
              </div>
              <div style={{ display: 'grid', gap: 10 }}>
                {renderedChangeNarratives.map((change) => (
                  <div
                    key={change.path}
                    style={{
                      padding: '10px 12px',
                      borderRadius: 8,
                      border: `1px solid ${PANEL_BORDER}`,
                      background: 'rgba(255,255,255,0.02)',
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        gap: 10,
                        alignItems: 'baseline',
                        marginBottom: 6,
                      }}
                    >
                      <div
                        style={{
                          fontFamily: 'Inter, sans-serif',
                          fontSize: 12,
                          fontWeight: 600,
                          color: '#EEF3FF',
                        }}
                      >
                        {change.title}
                      </div>
                      {change.confidence != null && (
                        <div
                          style={{
                            fontFamily: 'JetBrains Mono, monospace',
                            fontSize: 10,
                            color: confidenceTone(change.confidence),
                          }}
                        >
                          {confidenceLabel(change.confidence)}
                        </div>
                      )}
                    </div>
                    <div
                      style={{
                        fontFamily: 'Inter, sans-serif',
                        fontSize: 11,
                        lineHeight: 1.55,
                        color: '#C5CDD8',
                        marginBottom: 6,
                      }}
                    >
                      {change.plainEnglish}
                    </div>
                    <div
                      style={{
                        fontFamily: 'Inter, sans-serif',
                        fontSize: 11,
                        lineHeight: 1.55,
                        color: '#9AA4B2',
                        marginBottom: 6,
                      }}
                    >
                      {change.expectedEffect}
                    </div>
                    <div
                      style={{
                        fontFamily: 'Inter, sans-serif',
                        fontSize: 11,
                        lineHeight: 1.55,
                        color: '#7CE7FF',
                      }}
                    >
                      {change.whyItHelped}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {validationNotes && validationNotes.length > 0 && (
            <div
              style={{
                padding: '16px 18px',
                borderRadius: 12,
                border: `1px solid ${PANEL_BORDER}`,
                background: 'rgba(255,255,255,0.025)',
              }}
            >
              <div
                style={{
                  fontFamily: 'Inter, sans-serif',
                  fontSize: 12,
                  fontWeight: 700,
                  color: '#EEF3FF',
                  textTransform: 'uppercase',
                  letterSpacing: '0.08em',
                  marginBottom: 10,
                }}
              >
                Validation notes
              </div>
              <div style={{ display: 'grid', gap: 10 }}>
                {validationNotes.map((note) => {
                  const colors = noteColor(note.severity);
                  return (
                    <div
                      key={`${note.title}-${note.severity}`}
                      style={{
                        padding: '10px 12px',
                        borderRadius: 8,
                        border: `1px solid ${colors.border}`,
                        background: colors.bg,
                      }}
                    >
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          gap: 10,
                          alignItems: 'baseline',
                          marginBottom: 4,
                        }}
                      >
                        <div
                          style={{
                            fontFamily: 'Inter, sans-serif',
                            fontSize: 12,
                            fontWeight: 600,
                          color: '#EEF3FF',
                        }}
                      >
                          {note.title}
                        </div>
                        <div
                          style={{
                            fontFamily: 'JetBrains Mono, monospace',
                            fontSize: 10,
                            color: colors.text,
                            textTransform: 'uppercase',
                            letterSpacing: '0.1em',
                          }}
                        >
                          {note.severity}
                        </div>
                      </div>
                      <div
                        style={{
                          fontFamily: 'Inter, sans-serif',
                          fontSize: 11,
                          lineHeight: 1.5,
                          color: '#C5CDD8',
                        }}
                      >
                        {note.body}
                      </div>
                      {note.confidence != null && (
                        <div
                          style={{
                            marginTop: 6,
                            fontFamily: 'JetBrains Mono, monospace',
                            fontSize: 10,
                            color: colors.text,
                          }}
                        >
                          {confidenceLabel(note.confidence)}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
