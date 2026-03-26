import React from 'react';
import type {
  CommitteeChangeNarrative,
  CommitteeExportPayload,
  CommitteePersonaSummary,
  CommitteeReport,
  CommitteeValidationNote,
} from '@/types/committee';
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

function derivePersonaSummary(report: CommitteeReport): CommitteePersonaSummary {
  const archetypeCounts: Record<string, number> = {};
  const titleCounts: Record<string, number> = {};

  for (const persona of report.personas) {
    const title = persona.title || persona.roleInDecision || 'Committee persona';
    titleCounts[title] = (titleCounts[title] ?? 0) + 1;

    const sentiment = persona.sentiment || 'neutral';
    archetypeCounts[sentiment] = (archetypeCounts[sentiment] ?? 0) + 1;
  }

  const topRoles = Object.entries(titleCounts)
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .slice(0, 3)
    .map(([role]) => role);

  return {
    personaCount: report.personas.length,
    archetypeCounts,
    topRoles,
    explanation:
      report.personas.length > 0
        ? `The document was pressure-tested by ${report.personas.length} committee personas. The most visible roles were ${topRoles.length > 0 ? topRoles.join(', ') : 'the core buying committee'}; that matters because the report is only useful if the rewrite works for the people who actually approve or block the decision.`
        : 'This committee run did not include persona detail, so the report is based on the rewrite log and the document-level scores alone.',
  };
}

function deriveChangeNarratives(report: CommitteeReport): CommitteeChangeNarrative[] {
  if (report.changeNarratives && report.changeNarratives.length > 0) {
    return report.changeNarratives;
  }

  return report.rewrites
    .slice()
    .sort((a, b) => b.deltaPercent - a.deltaPercent)
    .slice(0, 6)
    .map(rewrite => ({
      sectionId: rewrite.sectionId,
      sectionTitle: rewrite.sectionTitle,
      title: `${rewrite.sectionTitle}: ${rewrite.parameterName}`,
      plainEnglish: rewrite.description,
      before: rewrite.oldValue,
      after: rewrite.newValue,
      expectedEffect:
        rewrite.decision === 'kept'
          ? 'This change was accepted because the committee score moved up without causing obvious harm to the other personas.'
          : 'This change was tested, but the committee decided it did not help enough to keep.',
      whyItHelped:
        rewrite.decision === 'kept'
          ? 'The accepted change helped the document address objections more directly.'
          : 'The rejected change did not improve the overall committee response enough to justify the tradeoff.',
      confidence: Math.max(0.35, Math.min(0.95, 0.55 + Math.abs(rewrite.deltaPercent) / 100)),
      evidence: [
        `Experiment #${rewrite.experimentId} ${rewrite.decision === 'kept' ? 'was kept' : 'was reverted'} after scoring ${rewrite.deltaPercent >= 0 ? '+' : ''}${rewrite.deltaPercent.toFixed(1)}%.`,
      ],
    }));
}

function deriveValidationNotes(
  report: CommitteeReport,
  exportPayload?: CommitteeExportPayload | null,
): CommitteeValidationNote[] {
  const notes: CommitteeValidationNote[] = [];
  const coverage = Number(exportPayload?.committeeSummary.llmCoveragePct ?? 0);

  if (report.warnings.length > 0) {
    notes.push({
      title: 'Run warnings',
      body: report.warnings.slice(0, 3).join(' '),
      severity: 'warning',
    });
  }

  if (coverage > 0) {
    notes.push({
      title: 'AI coverage',
      body: `LLM-assisted evaluation covered ${coverage.toFixed(0)}% of the committee scoring path.`,
      severity: coverage >= 60 ? 'success' : 'info',
      confidence: Math.max(0.35, Math.min(0.95, coverage / 100)),
    });
  }

  notes.push({
    title: 'Rewrite count',
    body: `${report.summary.acceptedRewrites} rewrites were accepted out of ${report.summary.rewritesTested} tested.`,
    severity: report.summary.acceptedRewrites > 0 ? 'success' : 'info',
  });

  return notes;
}

export default function CommitteeReportNarrative({
  report,
  exportPayload,
}: CommitteeReportNarrativeProps) {
  const summaryConfidence = report.summary.confidenceScore ?? null;
  const personaSummary = report.personaSummary ?? derivePersonaSummary(report);
  const narrative = report.narrative ?? [];
  const lead = narrative[0];
  const supportingSections = narrative.slice(1);
  const changeNarratives = deriveChangeNarratives(report);
  const validationNotes = report.validationNotes ?? deriveValidationNotes(report, exportPayload);
  const derivedConfidence =
    summaryConfidence ??
    (personaSummary.personaCount > 0 ? Math.min(0.95, 0.45 + report.personas.length / 30) : null);
  const confidenceText =
    confidenceLabel(derivedConfidence) ?? 'Confidence not provided';

  const rewriteGoals = exportPayload?.llmHandoff.rewriteGoals ?? [];
  const task = exportPayload?.llmHandoff.task ?? 'Rewrite the document for the committee while preserving factual integrity.';
  const suggestedPrompt = exportPayload?.llmHandoff.suggestedPrompt ?? null;
  const topAudience = exportPayload?.llmHandoff.targetAudience ?? [];

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
          background: 'linear-gradient(180deg, rgba(77,163,255,0.07), rgba(255,255,255,0.025))',
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
              color: confidenceTone(derivedConfidence),
            }}
          >
            {confidenceText}
            {personaSummary.personaCount > 0 ? ` · ${personaSummary.personaCount} personas` : ''}
            {exportPayload?.committeeSummary.evaluationMode ? ` · ${exportPayload.committeeSummary.evaluationMode.replace(/_/g, ' ')}` : ''}
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
          {lead?.body ||
            `The document improved from ${report.summary.baselineScore.toFixed(4)} to ${report.summary.bestScore.toFixed(4)} across ${report.summary.rewritesTested} rewrite attempts. In plain English, the committee found a version that reads more convincingly to the people it needs to persuade.`}
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
          {supportingSections.map(section => (
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
        <div
          style={{
            padding: '16px 18px',
            borderRadius: 14,
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
            Buying committee
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
                borderRadius: 10,
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
            {Object.entries(personaSummary.archetypeCounts).map(([archetype, count]) => (
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
                    justifyContent: 'space-between',
                    gap: 10,
                    alignItems: 'baseline',
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
              </div>
            ))}
          </div>
        </div>

        <div
          style={{
            padding: '16px 18px',
            borderRadius: 14,
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
            {validationNotes.map(note => {
              const color =
                note.severity === 'success'
                  ? '#4ADE80'
                  : note.severity === 'warning'
                    ? '#FBBF24'
                    : '#4DA3FF';
              const bg =
                note.severity === 'success'
                  ? 'rgba(74,222,128,0.05)'
                  : note.severity === 'warning'
                    ? 'rgba(251,191,36,0.05)'
                    : 'rgba(77,163,255,0.05)';

              return (
                <div
                  key={`${note.title}-${note.severity}`}
                  style={{
                    padding: '10px 12px',
                    borderRadius: 8,
                    border: `1px solid ${color}40`,
                    background: bg,
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
                        color,
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
                        color,
                      }}
                    >
                      {confidenceLabel(note.confidence) ?? 'Confidence not provided'}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div
        style={{
          padding: '16px 18px',
          borderRadius: 14,
          border: `1px solid ${PANEL_BORDER}`,
          background: 'rgba(255,255,255,0.025)',
          marginBottom: 14,
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
          {changeNarratives.map(change => (
            <div
              key={`${change.sectionId ?? change.title}-${change.title}`}
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
                Before: {change.before} · After: {change.after}
              </div>
              <div
                style={{
                  fontFamily: 'Inter, sans-serif',
                  fontSize: 11,
                  lineHeight: 1.55,
                  color: '#7CE7FF',
                  marginBottom: change.evidence.length > 0 ? 6 : 0,
                }}
              >
                {change.expectedEffect}
              </div>
              <div
                style={{
                  fontFamily: 'Inter, sans-serif',
                  fontSize: 11,
                  lineHeight: 1.55,
                  color: '#C5CDD8',
                }}
              >
                {change.whyItHelped}
              </div>
              {change.evidence.length > 0 && (
                <div
                  style={{
                    marginTop: 8,
                    fontFamily: 'Inter, sans-serif',
                    fontSize: 10,
                    lineHeight: 1.55,
                    color: '#6B7480',
                  }}
                >
                  {change.evidence.map(evidence => (
                    <div key={evidence}>{evidence}</div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      <div
        style={{
          padding: '16px 18px',
          borderRadius: 14,
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
          Export handoff
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
          {task}
        </div>
        {rewriteGoals.length > 0 && (
          <div style={{ marginBottom: 12 }}>
            <div
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 9,
                color: '#6B7480',
                letterSpacing: '0.14em',
                textTransform: 'uppercase',
                marginBottom: 8,
              }}
            >
              Rewrite goals
            </div>
            <div style={{ display: 'grid', gap: 6 }}>
              {rewriteGoals.slice(0, 4).map(goal => (
                <div
                  key={goal}
                  style={{
                    padding: '9px 10px',
                    borderRadius: 8,
                    background: 'rgba(77,163,255,0.05)',
                    border: '1px solid rgba(77,163,255,0.12)',
                    fontFamily: 'Inter, sans-serif',
                    fontSize: 11,
                    lineHeight: 1.5,
                    color: '#D7DEE8',
                  }}
                >
                  {goal}
                </div>
              ))}
            </div>
          </div>
        )}
        {topAudience.length > 0 && (
          <div style={{ marginBottom: 12 }}>
            <div
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 9,
                color: '#6B7480',
                letterSpacing: '0.14em',
                textTransform: 'uppercase',
                marginBottom: 8,
              }}
            >
              Top audience members
            </div>
            <div style={{ display: 'grid', gap: 8 }}>
              {topAudience.slice(0, 4).map((persona, index) => {
                const typedPersona = persona as {
                  name?: unknown;
                  title?: unknown;
                  score?: unknown;
                };
                const scoreValue =
                  typeof typedPersona.score === 'number'
                    ? typedPersona.score.toFixed(2)
                    : null;

                return (
                <div
                  key={`${String(typedPersona.name ?? 'persona')}-${index}`}
                  style={{
                    padding: '9px 10px',
                    borderRadius: 8,
                    background: 'rgba(255,255,255,0.02)',
                    border: `1px solid ${PANEL_BORDER}`,
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      gap: 8,
                      marginBottom: 4,
                    }}
                  >
                    <div
                      style={{
                        fontFamily: 'Inter, sans-serif',
                        fontSize: 11,
                        fontWeight: 600,
                        color: '#EEF3FF',
                      }}
                    >
                      {String(typedPersona.name ?? 'Committee member')}
                    </div>
                    {scoreValue && (
                      <div
                        style={{
                          fontFamily: 'JetBrains Mono, monospace',
                          fontSize: 10,
                          color: '#7CE7FF',
                        }}
                      >
                        {scoreValue}
                      </div>
                    )}
                  </div>
                  <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 10, color: '#9AA4B2', lineHeight: 1.45 }}>
                    {String(typedPersona.title ?? 'Committee persona')}
                  </div>
                </div>
                );
              })}
            </div>
          </div>
        )}
        {suggestedPrompt && (
          <div
            style={{
              fontFamily: 'Inter, sans-serif',
              fontSize: 11,
              lineHeight: 1.55,
              color: '#9AA4B2',
            }}
          >
            Suggested prompt: {suggestedPrompt}
          </div>
        )}
      </div>
    </div>
  );
}
