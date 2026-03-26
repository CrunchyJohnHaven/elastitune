import React from 'react';
import { useCommitteeStore } from '@/store/useCommitteeStore';
import { formatPercent, formatScore } from '@/lib/format';
import { PANEL_BG, PANEL_BORDER } from '@/lib/theme';

/* ──────────────────────────────────────────────────────────
   Committee Right Rail — executive-briefing quality.

   Sections:
   1. Document meta (name, sections, personas, mode)
   2. Score timeline + sparkline bar chart
   3. Persona selector list (left-border sentiment color)
   4. Selected persona deep-dive (objection, risks, missing,
      per-section breakdown)
   ────────────────────────────────────────────────────────── */

function sentimentColor(sentiment: string): string {
  switch (sentiment) {
    case 'supportive':            return '#4ADE80';
    case 'cautiously_interested': return '#9AE66E';
    case 'neutral':               return '#FBBF24';
    case 'skeptical':             return '#FB8B5F';
    case 'opposed':               return '#FB7185';
    default:                      return '#9AA4B2';
  }
}

function sentimentLabel(sentiment: string): string {
  switch (sentiment) {
    case 'supportive':            return 'Supportive';
    case 'cautiously_interested': return 'Cautious';
    case 'neutral':               return 'Neutral';
    case 'skeptical':             return 'Skeptical';
    case 'opposed':               return 'Opposed';
    default:                      return sentiment;
  }
}

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      padding: '9px 14px',
      borderBottom: `1px solid ${PANEL_BORDER}`,
      flexShrink: 0,
    }}>
      <span style={{
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: 9,
        fontWeight: 700,
        letterSpacing: '0.16em',
        color: '#4B5563',
        textTransform: 'uppercase',
      }}>
        {children}
      </span>
    </div>
  );
}

function ScoreBadge({ value, baseline }: { value: number; baseline?: number }) {
  const delta = baseline != null ? value - baseline : null;
  const positive = delta != null && delta >= 0;
  return (
    <div style={{ display: 'flex', alignItems: 'baseline', gap: 5 }}>
      <span style={{
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: 13,
        fontWeight: 700,
        color: '#EEF3FF',
      }}>
        {formatScore(value)}
      </span>
      {delta != null && Math.abs(delta) > 0.001 && (
        <span style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 9,
          color: positive ? '#4ADE80' : '#FB7185',
        }}>
          {positive ? '+' : ''}{formatPercent(delta)}
        </span>
      )}
    </div>
  );
}

export default function CommitteeRightRail() {
  const snapshot         = useCommitteeStore(state => state.snapshot);
  const selectedPersonaId = useCommitteeStore(state => state.selectedPersonaId);
  const setSelectedPersona = useCommitteeStore(state => state.setSelectedPersona);

  if (!snapshot) return null;

  const selectedPersona =
    snapshot.personas.find(p => p.id === selectedPersonaId) ??
    snapshot.personas[0] ??
    null;

  const baselineScore = snapshot.metrics.baselineScore;
  const currentScore  = snapshot.metrics.currentScore;
  const gain          = snapshot.metrics.improvementPct;
  const gainPositive  = gain >= 0;

  const timeline = snapshot.metrics.scoreTimeline.slice(-30);
  const tlMin = timeline.length ? Math.min(...timeline.map(p => p.score)) : 0;
  const tlMax = timeline.length ? Math.max(...timeline.map(p => p.score)) : 1;

  return (
    <div style={{
      width: 380,
      flexShrink: 0,
      background: PANEL_BG,
      borderLeft: `1px solid ${PANEL_BORDER}`,
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      overflowY: 'auto',
      overflowX: 'hidden',
      scrollbarWidth: 'thin',
      scrollbarColor: 'rgba(255,255,255,0.06) transparent',
    }}>

      {/* ── 1. Document Info ── */}
      <div style={{ flexShrink: 0 }}>
        <SectionHeader>Document Info</SectionHeader>
        <div style={{ padding: '12px 14px', borderBottom: `1px solid ${PANEL_BORDER}` }}>
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr auto',
            rowGap: 6,
            columnGap: 10,
            fontFamily: 'Inter, sans-serif',
            fontSize: 12,
          }}>
            <span style={{ color: '#6B7480' }}>Document</span>
            <span style={{ color: '#EEF3FF', textAlign: 'right', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {snapshot.summary.documentName}
            </span>
            <span style={{ color: '#6B7480' }}>Sections</span>
            <span style={{ color: '#EEF3FF', textAlign: 'right' }}>{snapshot.summary.sectionsCount}</span>
            <span style={{ color: '#6B7480' }}>Committee size</span>
            <span style={{ color: '#EEF3FF', textAlign: 'right' }}>{snapshot.summary.personasCount} personas</span>
            <span style={{ color: '#6B7480' }}>Mode</span>
            <span style={{ color: '#4DA3FF', textAlign: 'right', fontFamily: 'JetBrains Mono, monospace', fontSize: 10, letterSpacing: '0.06em' }}>
              {snapshot.evaluationMode.replace(/_/g, ' ').toUpperCase()}
            </span>
            <span style={{ color: '#6B7480' }}>Industry</span>
            <span style={{ color: '#EEF3FF', textAlign: 'right' }}>{snapshot.summary.industryLabel}</span>
            <span style={{ color: '#6B7480' }}>AI coverage</span>
            <span style={{ color: '#EEF3FF', textAlign: 'right' }}>{snapshot.metrics.llmCoveragePct.toFixed(0)}%</span>
          </div>
        </div>
      </div>

      {/* ── 2. Score Timeline ── */}
      <div style={{ flexShrink: 0 }}>
        <SectionHeader>Score Timeline</SectionHeader>
        <div style={{ padding: '12px 14px', borderBottom: `1px solid ${PANEL_BORDER}` }}>
          {/* KPI row */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginBottom: 12 }}>
            {[
              { label: 'Current', value: formatScore(currentScore), color: '#4DA3FF' },
              { label: 'Baseline', value: formatScore(baselineScore), color: '#9AA4B2' },
              { label: 'Gain', value: `${gainPositive ? '+' : ''}${formatPercent(gain)}`, color: gainPositive ? '#4ADE80' : '#FB7185' },
            ].map(({ label, value, color }) => (
              <div key={label} style={{
                padding: '8px 10px',
                borderRadius: 8,
                background: 'rgba(255,255,255,0.025)',
                border: `1px solid rgba(255,255,255,0.05)`,
                textAlign: 'center',
              }}>
                <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: '#6B7480', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 4 }}>
                  {label}
                </div>
                <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 14, fontWeight: 700, color }}>
                  {value}
                </div>
              </div>
            ))}
          </div>

          {/* Sparkline */}
          {timeline.length > 0 && (
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 2, height: 44 }}>
              {timeline.map((point, i) => {
                const h = tlMax === tlMin
                  ? 20
                  : 8 + ((point.score - tlMin) / (tlMax - tlMin)) * 36;
                const isLast = i === timeline.length - 1;
                return (
                  <div key={`${point.t}-${i}`} style={{
                    flex: 1,
                    height: h,
                    borderRadius: 2,
                    background: isLast
                      ? 'linear-gradient(180deg, #4DA3FF 0%, rgba(77,163,255,0.3) 100%)'
                      : 'linear-gradient(180deg, rgba(77,163,255,0.55) 0%, rgba(77,163,255,0.1) 100%)',
                    transition: 'height 0.4s ease',
                  }} />
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* ── 3. Persona List ── */}
      <div style={{ flexShrink: 0 }}>
        <SectionHeader>Personas ({snapshot.personas.length})</SectionHeader>
        <div style={{ borderBottom: `1px solid ${PANEL_BORDER}` }}>
          {snapshot.personas.map(persona => {
            const color = sentimentColor(persona.sentiment);
            const isSelected = selectedPersona?.id === persona.id;
            return (
              <button
                key={persona.id}
                onClick={() => setSelectedPersona(persona.id)}
                style={{
                  width: '100%',
                  textAlign: 'left',
                  background: isSelected ? 'rgba(77,163,255,0.05)' : 'transparent',
                  border: 'none',
                  borderBottom: `1px solid ${PANEL_BORDER}`,
                  borderLeft: `3px solid ${isSelected ? '#4DA3FF' : color}`,
                  padding: '9px 12px',
                  cursor: 'pointer',
                  transition: 'background 0.15s',
                }}
                onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = 'rgba(255,255,255,0.02)'; }}
                onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = 'transparent'; }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  {/* Sentiment dot with glow */}
                  <div style={{
                    width: 9, height: 9, borderRadius: '50%',
                    background: color,
                    boxShadow: `0 0 8px ${color}`,
                    flexShrink: 0,
                  }} />

                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontFamily: 'Inter, sans-serif',
                      fontSize: 12, fontWeight: 600,
                      color: isSelected ? '#EEF3FF' : '#C5CDD8',
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>
                      {persona.name}
                    </div>
                    <div style={{
                      fontFamily: 'Inter, sans-serif',
                      fontSize: 10, color: '#6B7480',
                      overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                    }}>
                      {persona.title}
                    </div>
                  </div>

                  <div style={{ textAlign: 'right', flexShrink: 0 }}>
                    <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, color: '#EEF3FF' }}>
                      {formatScore(persona.currentScore)}
                    </div>
                    <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color, marginTop: 1, letterSpacing: '0.06em' }}>
                      {sentimentLabel(persona.sentiment).toUpperCase()}
                    </div>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── 4. Persona Detail ── */}
      <div style={{ flexShrink: 0 }}>
        <SectionHeader>Persona Detail</SectionHeader>

        {selectedPersona ? (
          <div style={{ padding: '14px 14px 18px' }}>

            {/* Header: name + role + score */}
            <div style={{
              display: 'flex',
              alignItems: 'flex-start',
              gap: 12,
              marginBottom: 14,
              paddingBottom: 12,
              borderBottom: `1px solid ${PANEL_BORDER}`,
            }}>
              {/* Avatar circle */}
              <div style={{
                width: 40, height: 40, borderRadius: '50%', flexShrink: 0,
                background: sentimentColor(selectedPersona.sentiment),
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: 14, color: '#05070B',
                boxShadow: `0 0 16px ${sentimentColor(selectedPersona.sentiment)}60`,
              }}>
                {selectedPersona.name.split(' ').map((w: string) => w[0]).join('').slice(0, 2).toUpperCase()}
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 14, fontWeight: 700, color: '#EEF3FF' }}>
                  {selectedPersona.name}
                </div>
                <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 11, color: '#9AA4B2', marginTop: 1 }}>
                  {selectedPersona.title ?? 'Committee Persona'}
                </div>
                <div style={{
                  fontFamily: 'JetBrains Mono, monospace', fontSize: 9,
                  color: sentimentColor(selectedPersona.sentiment),
                  letterSpacing: '0.08em', marginTop: 3,
                }}>
                  {sentimentLabel(selectedPersona.sentiment).toUpperCase()}
                  {selectedPersona.roleInDecision ? ` · ${selectedPersona.roleInDecision}` : ''}
                </div>
                <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: '#6B7480', marginTop: 4, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                  {selectedPersona.evaluationSource === 'llm' ? 'Scored by AI' : selectedPersona.evaluationSource === 'mixed' ? 'Mixed AI + heuristic scoring' : 'Heuristic estimate'}
                </div>
              </div>
              <ScoreBadge value={selectedPersona.currentScore} baseline={baselineScore} />
            </div>

            {/* Top objection — highlighted */}
            {(selectedPersona.topObjection || selectedPersona.reactionQuote) && (
              <div style={{
                padding: '10px 12px',
                borderRadius: 10,
                background: 'rgba(251,113,133,0.05)',
                border: `1px solid rgba(251,113,133,0.18)`,
                borderLeft: `3px solid #FB7185`,
                marginBottom: 12,
              }}>
                <div style={{
                  fontFamily: 'JetBrains Mono, monospace', fontSize: 8,
                  color: '#FB7185', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 5,
                }}>
                  Top Objection
                </div>
                <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 12, color: '#EEF3FF', lineHeight: 1.5 }}>
                  {selectedPersona.topObjection ?? selectedPersona.reactionQuote}
                </div>
              </div>
            )}

            {/* Risk flags */}
            {selectedPersona.riskFlags.length > 0 && (
              <div style={{ marginBottom: 12 }}>
                <div style={{
                  fontFamily: 'JetBrains Mono, monospace', fontSize: 8,
                  color: '#6B7480', letterSpacing: '0.12em', textTransform: 'uppercase',
                  marginBottom: 6,
                }}>
                  Risk Flags
                </div>
                <div style={{ display: 'grid', gap: 5 }}>
                  {selectedPersona.riskFlags.slice(0, 4).map((flag: string) => (
                    <div key={flag} style={{
                      display: 'flex', alignItems: 'flex-start', gap: 7,
                      fontFamily: 'Inter, sans-serif', fontSize: 11,
                      color: '#FCA5A5', padding: '7px 10px',
                      background: 'rgba(251,113,133,0.06)', borderRadius: 7,
                      borderLeft: '2px solid rgba(251,113,133,0.3)',
                    }}>
                      <span style={{ flexShrink: 0, marginTop: 0 }}>⚠</span>
                      <span>{flag}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Missing info */}
            {selectedPersona.missing.length > 0 && (
              <div style={{ marginBottom: 14 }}>
                <div style={{
                  fontFamily: 'JetBrains Mono, monospace', fontSize: 8,
                  color: '#6B7480', letterSpacing: '0.12em', textTransform: 'uppercase',
                  marginBottom: 6,
                }}>
                  Missing Information
                </div>
                <div style={{ display: 'grid', gap: 5 }}>
                  {selectedPersona.missing.slice(0, 4).map((item: string) => (
                    <div key={item} style={{
                      display: 'flex', alignItems: 'flex-start', gap: 7,
                      fontFamily: 'Inter, sans-serif', fontSize: 11,
                      color: '#FCD34D', padding: '7px 10px',
                      background: 'rgba(251,191,36,0.06)', borderRadius: 7,
                      borderLeft: '2px solid rgba(251,191,36,0.3)',
                    }}>
                      <span style={{ flexShrink: 0 }}>○</span>
                      <span>{item}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Per-section breakdown */}
            {selectedPersona.perSection.length > 0 && (
              <div>
                <div style={{
                  fontFamily: 'JetBrains Mono, monospace', fontSize: 8,
                  color: '#6B7480', letterSpacing: '0.12em', textTransform: 'uppercase',
                  marginBottom: 8,
                }}>
                  Section Breakdown
                </div>
                <div style={{ display: 'grid', gap: 6 }}>
                  {selectedPersona.perSection.map((section) => {
                    const pct = Math.round(section.compositeScore * 100);
                    const barColor = pct >= 65 ? '#4ADE80' : pct >= 45 ? '#FBBF24' : '#FB7185';
                    return (
                      <div key={section.sectionId} style={{
                        padding: '9px 11px',
                        borderRadius: 9,
                        border: `1px solid ${PANEL_BORDER}`,
                        background: 'rgba(255,255,255,0.02)',
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 8, marginBottom: 4 }}>
                          <span style={{
                            fontFamily: 'Inter, sans-serif', fontSize: 11, fontWeight: 600,
                            color: '#C5CDD8', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                          }}>
                            {section.sectionTitle}
                          </span>
                          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: barColor, flexShrink: 0 }}>
                            {formatScore(section.compositeScore)}
                          </span>
                        </div>
                        {/* Score bar */}
                        <div style={{ height: 2, background: 'rgba(255,255,255,0.06)', borderRadius: 1, marginBottom: 5 }}>
                          <div style={{ height: '100%', width: `${Math.max(0, Math.min(100, pct))}%`, background: barColor, borderRadius: 1, transition: 'width 0.6s ease' }} />
                        </div>
                        <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 10, color: '#9AA4B2', lineHeight: 1.4 }}>
                          {section.reactionQuote}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div style={{ padding: '20px 14px', fontFamily: 'Inter, sans-serif', fontSize: 12, color: '#4B5563', fontStyle: 'italic' }}>
            Select a persona to inspect details.
          </div>
        )}
      </div>
    </div>
  );
}
