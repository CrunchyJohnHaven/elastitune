import React from 'react';
import type { CommitteeExportPayload, CommitteeReport } from '@/types/committee';
import { PANEL_BORDER } from '@/lib/theme';

interface CommitteeReportNarrativeProps {
  report: CommitteeReport;
  exportPayload?: CommitteeExportPayload | null;
}

function confidenceLabel(value?: number | null): string | null {
  if (value == null || Number.isNaN(value)) return null;
  const normalized = value <= 1 ? value * 100 : value;
  return `${Math.max(0, Math.min(100, Math.round(normalized)))}% confidence`;
}

function confidenceTone(value?: number | null): string {
  if (value == null || Number.isNaN(value)) return '#9AA4B2';
  const normalized = value <= 1 ? value * 100 : value;
  if (normalized >= 80) return '#4ADE80';
  if (normalized >= 60) return '#FBBF24';
  return '#FB7185';
}

function severityColor(severity: 'success' | 'info' | 'warning') {
  if (severity === 'success') {
    return { border: 'rgba(74,222,128,0.24)', bg: 'rgba(74,222,128,0.05)', text: '#4ADE80' };
  }
  if (severity === 'warning') {
    return { border: 'rgba(251,191,36,0.24)', bg: 'rgba(251,191,36,0.05)', text: '#FBBF24' };
  }
  return { border: 'rgba(77,163,255,0.24)', bg: 'rgba(77,163,255,0.05)', text: '#4DA3FF' };
}

export default function CommitteeReportNarrative({
  report,
  exportPayload,
}: CommitteeReportNarrativeProps) {
  const lead = report.narrative?.[0];
  const supportingSections = report.narrative?.slice(1) ?? [];
  const confidenceText =
    confidenceLabel(lead?.confidence ?? report.summary.confidenceScore) ??
    'Confidence not provided';

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
          borderRadius: 14,
          border: '1px solid rgba(77,163,255,0.15)',
          background:
            'linear-gradient(180deg, rgba(77,163,255,0.07), rgba(255,255,255,0.025))',
          marginBottom: 14,
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            gap: 12,
            alignItems: 'center',
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
            What this committee run means
          </div>
          <div
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 11,
              color: confidenceTone(lead?.confidence ?? report.summary.confidenceScore),
            }}
          >
            {confidenceText}
            {report.summary.personasCount > 0
              ? ` · ${report.summary.personasCount} personas`
              : ''}
            {exportPayload?.committeeSummary.evaluationMode
              ? ` · ${exportPayload.committeeSummary.evaluationMode.replace(/_/g, ' ')}`
              : ''}
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
          {lead?.body || report.summary.overview}
        </div>
      </div>

      {supportingSections.length > 0 && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
            gap: 12,
            marginBottom: 14,
          }}
        >
          {supportingSections.map((section) => (
            <div
              key={section.key}
              style={{
                padding: '14px 16px',
                borderRadius: 12,
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

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: 14,
          marginBottom: 14,
        }}
      >
        {report.personaSummary && (
          <div
            style={{
              padding: '16px 18px',
              borderRadius: 14,
              background: 'rgba(10,14,20,0.76)',
              border: `1px solid ${PANEL_BORDER}`,
            }}
          >
            <HeaderLabel label="Committee Reaction" />
            <div
              style={{
                fontFamily: 'Inter, sans-serif',
                fontSize: 13,
                lineHeight: 1.6,
                color: '#C5CDD8',
                marginBottom: 12,
              }}
            >
              {report.personaSummary.explanation}
            </div>
            <div style={{ display: 'grid', gap: 8 }}>
              <MiniMetric label="Supportive" value={String(report.personaSummary.supportiveCount)} />
              <MiniMetric label="Mixed / neutral" value={String(report.personaSummary.cautiousCount)} />
              <MiniMetric label="Skeptical" value={String(report.personaSummary.skepticalCount)} />
              {report.personaSummary.topSupporter && (
                <MiniMetric label="Top supporter" value={report.personaSummary.topSupporter} />
              )}
              {report.personaSummary.topBlocker && (
                <MiniMetric label="Top blocker" value={report.personaSummary.topBlocker} />
              )}
            </div>
          </div>
        )}

        {report.validationNotes?.length > 0 && (
          <div
            style={{
              padding: '16px 18px',
              borderRadius: 14,
              background: 'rgba(10,14,20,0.76)',
              border: `1px solid ${PANEL_BORDER}`,
            }}
          >
            <HeaderLabel label="Validation Notes" />
            <div style={{ display: 'grid', gap: 10 }}>
              {report.validationNotes.map((note) => {
                const colors = severityColor(note.severity);
                return (
                  <div
                    key={`${note.title}-${note.severity}`}
                    style={{
                      padding: '10px 12px',
                      borderRadius: 10,
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
                          textTransform: 'uppercase',
                          letterSpacing: '0.1em',
                          color: colors.text,
                        }}
                      >
                        {note.severity}
                      </div>
                    </div>
                    <div
                      style={{
                        fontFamily: 'Inter, sans-serif',
                        fontSize: 11,
                        lineHeight: 1.55,
                        color: '#C5CDD8',
                      }}
                    >
                      {note.body}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {report.changeNarratives?.length > 0 && (
        <div
          style={{
            padding: '16px 18px',
            borderRadius: 14,
            background: 'rgba(10,14,20,0.76)',
            border: `1px solid ${PANEL_BORDER}`,
            marginBottom: 14,
          }}
        >
          <HeaderLabel label="Accepted Rewrites Explained" />
          <div style={{ display: 'grid', gap: 10 }}>
            {report.changeNarratives.map((change) => (
              <div
                key={`${change.experimentId}-${change.sectionId}`}
                style={{
                  padding: '12px 14px',
                  borderRadius: 10,
                  background: 'rgba(255,255,255,0.02)',
                  border: `1px solid ${PANEL_BORDER}`,
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    gap: 12,
                    alignItems: 'baseline',
                    flexWrap: 'wrap',
                    marginBottom: 6,
                  }}
                >
                  <div
                    style={{
                      fontFamily: 'Inter, sans-serif',
                      fontWeight: 600,
                      fontSize: 12,
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
                    fontSize: 12,
                    color: '#C5CDD8',
                    lineHeight: 1.55,
                    marginBottom: 6,
                  }}
                >
                  {change.plainEnglish}
                </div>
                <div
                  style={{
                    fontFamily: 'Inter, sans-serif',
                    fontSize: 11,
                    color: '#9AA4B2',
                    lineHeight: 1.55,
                    marginBottom: 6,
                  }}
                >
                  {change.expectedEffect}
                </div>
                <div
                  style={{
                    fontFamily: 'Inter, sans-serif',
                    fontSize: 11,
                    color: '#7CE7FF',
                    lineHeight: 1.55,
                    marginBottom: change.evidence.length ? 8 : 0,
                  }}
                >
                  {change.whyItHelped}
                </div>
                {change.evidence.length > 0 && (
                  <div style={{ display: 'grid', gap: 4 }}>
                    {change.evidence.map((item, index) => (
                      <div
                        key={`${index}-${item}`}
                        style={{
                          fontFamily: 'Inter, sans-serif',
                          fontSize: 10,
                          color: '#9AA4B2',
                          lineHeight: 1.5,
                        }}
                      >
                        {item}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {report.summary.nextSteps?.length > 0 && (
        <div
          style={{
            padding: '16px 18px',
            borderRadius: 14,
            background: 'rgba(10,14,20,0.76)',
            border: `1px solid ${PANEL_BORDER}`,
          }}
        >
          <HeaderLabel label="Recommended Next Steps" />
          <div style={{ display: 'grid', gap: 8 }}>
            {report.summary.nextSteps.map((step, index) => (
              <div
                key={`${index}-${step}`}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '22px 1fr',
                  gap: 8,
                  alignItems: 'start',
                }}
              >
                <div
                  style={{
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: 11,
                    color: '#4DA3FF',
                  }}
                >
                  {index + 1}.
                </div>
                <div
                  style={{
                    fontFamily: 'Inter, sans-serif',
                    fontSize: 12,
                    color: '#C5CDD8',
                    lineHeight: 1.55,
                  }}
                >
                  {step}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function HeaderLabel({ label }: { label: string }) {
  return (
    <div
      style={{
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: 9,
        color: '#6B7480',
        letterSpacing: '0.14em',
        textTransform: 'uppercase',
        marginBottom: 14,
      }}
    >
      {label}
    </div>
  );
}

function MiniMetric({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        gap: 10,
        alignItems: 'center',
        padding: '10px 12px',
        borderRadius: 10,
        background: 'rgba(255,255,255,0.02)',
        border: `1px solid ${PANEL_BORDER}`,
        fontFamily: 'Inter, sans-serif',
        fontSize: 12,
        color: '#C5CDD8',
      }}
    >
      <span>{label}</span>
      <strong style={{ color: '#EEF3FF' }}>{value}</strong>
    </div>
  );
}
