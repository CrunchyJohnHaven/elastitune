import React from 'react';
import { formatScore, initials, truncate } from '@/lib/format';
import { ACCENT_BLUE, PANEL_BORDER } from '@/lib/theme';
import { useCommitteeStore } from '@/store/useCommitteeStore';
import type { CommitteePersonaView } from '@/types/committee';

function sentimentColor(sentiment: string): string {
  switch (sentiment) {
    case 'supportive':
      return '#4ADE80';
    case 'cautiously_interested':
      return '#9AE66E';
    case 'neutral':
      return '#FBBF24';
    case 'skeptical':
      return '#FB8B5F';
    case 'opposed':
      return '#FB7185';
    default:
      return '#9AA4B2';
  }
}

function sentimentLabel(sentiment: string): string {
  switch (sentiment) {
    case 'supportive':
      return 'supportive';
    case 'cautiously_interested':
      return 'cautiously interested';
    case 'neutral':
      return 'neutral';
    case 'skeptical':
      return 'skeptical';
    case 'opposed':
      return 'opposed';
    default:
      return 'neutral';
  }
}

function stableHash(value: string): number {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = ((hash << 5) - hash + value.charCodeAt(index)) | 0;
  }
  return Math.abs(hash);
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function quoteSnippet(persona: CommitteePersonaView): string {
  const source = persona.topObjection || persona.reactionQuote || persona.concerns[0] || '';
  if (!source) return '';
  return truncate(`"${source.replace(/\s+/g, ' ').trim()}"`, 42);
}

export default function CommitteeSpaceCanvas() {
  const snapshot = useCommitteeStore(state => state.snapshot);
  const selectedPersonaId = useCommitteeStore(state => state.selectedPersonaId);
  const setSelectedPersona = useCommitteeStore(state => state.setSelectedPersona);

  if (!snapshot) {
    return null;
  }

  const personas = snapshot.personas;
  const activeSectionId = snapshot.metrics.currentSectionId ?? snapshot.document.sections[0]?.id ?? null;
  const activeSection = snapshot.document.sections.find(section => section.id === activeSectionId) ?? snapshot.document.sections[0] ?? null;
  const orderedPersonas = [...personas].sort((left, right) => {
    if (right.authorityWeight !== left.authorityWeight) {
      return right.authorityWeight - left.authorityWeight;
    }
    return left.name.localeCompare(right.name);
  });

  const centerX = 50;
  const centerY = 50;
  const personaNodes = orderedPersonas.map((persona, index) => {
    const angleBase = (-Math.PI / 2) + ((index / Math.max(orderedPersonas.length, 1)) * Math.PI * 2);
    const angleJitter = ((stableHash(persona.id) % 19) - 9) * 0.018;
    const score = clamp(persona.currentScore || 0.5, 0.16, 0.94);
    const authorityPull = clamp((0.24 - persona.authorityWeight) * 18, -3, 7);
    const orbitRadius = clamp(34 - score * 11 + authorityPull, 23, 36);
    const x = centerX + Math.cos(angleBase + angleJitter) * orbitRadius;
    const y = centerY + Math.sin(angleBase + angleJitter) * orbitRadius * 0.76;
    const midX = centerX + (x - centerX) * 0.55;
    const midY = centerY + (y - centerY) * 0.55;
    const tangentialOffset = ((index % 2 === 0 ? 1 : -1) * (4 + (index % 3) * 1.8));
    const color = sentimentColor(persona.sentiment);

    return {
      persona,
      color,
      x,
      y,
      quoteX: midX + Math.cos(angleBase + Math.PI / 2) * tangentialOffset,
      quoteY: midY + Math.sin(angleBase + Math.PI / 2) * tangentialOffset,
      score,
    };
  });

  const sectionNodes = snapshot.document.sections.slice(0, 12).map((section, index, all) => {
    const span = 58;
    const left = 50 - span / 2 + (index * span) / Math.max(all.length - 1, 1);
    return {
      ...section,
      left,
      active: section.id === activeSectionId,
    };
  });

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', overflow: 'hidden' }}>
      <style>{`
        @keyframes committeePulse {
          0%, 100% { transform: scale(1); opacity: 0.9; }
          50% { transform: scale(1.08); opacity: 1; }
        }
        @keyframes committeeHalo {
          0%, 100% { transform: translate(-50%, -50%) scale(1); opacity: 0.16; }
          50% { transform: translate(-50%, -50%) scale(1.18); opacity: 0.28; }
        }
        @keyframes committeeFloat {
          0%, 100% { transform: translateY(0px); }
          50% { transform: translateY(-3px); }
        }
      `}</style>

      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'radial-gradient(circle at 50% 45%, rgba(77,163,255,0.12) 0%, rgba(11,16,23,0.96) 36%, rgba(5,7,11,1) 72%)',
        }}
      />

      {[20, 31, 42].map((radius) => (
        <div
          key={radius}
          style={{
            position: 'absolute',
            left: '50%',
            top: '50%',
            width: `${radius * 2}%`,
            height: `${radius * 2 * 0.76}%`,
            transform: 'translate(-50%, -50%)',
            borderRadius: '50%',
            border: '1px dashed rgba(255,255,255,0.06)',
            pointerEvents: 'none',
          }}
        />
      ))}

      <div
        style={{
          position: 'absolute',
          inset: 18,
          border: `1px solid ${PANEL_BORDER}`,
          borderRadius: 18,
          pointerEvents: 'none',
        }}
      />

      <div
        style={{
          position: 'absolute',
          left: 26,
          top: 22,
          zIndex: 3,
          padding: '12px 14px',
          maxWidth: 280,
          borderRadius: 14,
          background: 'rgba(8,12,18,0.82)',
          border: `1px solid ${PANEL_BORDER}`,
          boxShadow: '0 18px 48px rgba(0,0,0,0.26)',
          backdropFilter: 'blur(8px)',
        }}
      >
        <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, letterSpacing: '0.14em', color: '#6B7480', textTransform: 'uppercase', marginBottom: 6 }}>
          Now Testing
        </div>
        <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 14, fontWeight: 700, color: '#EEF3FF', marginBottom: 4 }}>
          Section {activeSection?.id ?? '—'}: {activeSection ? truncate(activeSection.title, 28) : 'Loading committee context'}
        </div>
        <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 11, lineHeight: 1.5, color: '#96A2B4' }}>
          The room re-scores this section, then the rewrite is kept only if consensus rises without harming any single stakeholder.
        </div>
      </div>

      <div
        style={{
          position: 'absolute',
          left: '50%',
          top: '50%',
          width: 164,
          height: 164,
          transform: 'translate(-50%, -50%)',
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(77,163,255,0.26) 0%, rgba(8,12,18,0.95) 62%, rgba(8,12,18,0.76) 100%)',
          border: '1px solid rgba(77,163,255,0.26)',
          boxShadow: '0 0 50px rgba(77,163,255,0.16)',
          zIndex: 2,
        }}
      >
        <div
          style={{
            position: 'absolute',
            left: '50%',
            top: '50%',
            width: 88,
            height: 88,
            transform: 'translate(-50%, -50%)',
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(255,255,255,0.92) 0%, rgba(176,222,255,0.9) 32%, rgba(77,163,255,0.34) 72%, rgba(77,163,255,0.04) 100%)',
            boxShadow: `0 0 30px ${ACCENT_BLUE}`,
          }}
        />
        <div
          style={{
            position: 'absolute',
            left: '50%',
            top: '50%',
            transform: 'translate(-50%, -50%)',
            width: 118,
            textAlign: 'center',
          }}
        >
          <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: 14, color: '#EEF3FF', marginBottom: 4 }}>
            {truncate(snapshot.summary.documentName, 28)}
          </div>
          <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#7CE7FF', letterSpacing: '0.08em' }}>
            LIVE DOCUMENT
          </div>
        </div>
      </div>

      <svg
        style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 1 }}
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
      >
        {personaNodes.map(({ persona, color, x, y }) => {
          const selected = selectedPersonaId === persona.id;
          return (
            <g key={`beam-${persona.id}`}>
              <line
                x1={centerX}
                y1={centerY}
                x2={x}
                y2={y}
                stroke={color}
                strokeWidth={selected ? '0.38' : '0.24'}
                strokeOpacity={selected ? 0.48 : 0.22}
                strokeDasharray={persona.sentiment === 'supportive' ? '0' : '2.2 2.8'}
              />
            </g>
          );
        })}
      </svg>

      {personaNodes.map(({ persona, color, x, y, quoteX, quoteY }) => {
        const selected = selectedPersonaId === persona.id;
        const quote = quoteSnippet(persona);
        return (
          <React.Fragment key={persona.id}>
            <div
              style={{
                position: 'absolute',
                left: `${x}%`,
                top: `${y}%`,
                width: 32,
                height: 32,
                transform: 'translate(-50%, -50%)',
                borderRadius: '50%',
                background: `rgba(${hexToRgb(color)}, 0.18)`,
                animation: 'committeeHalo 2.7s ease-in-out infinite',
                pointerEvents: 'none',
                zIndex: 2,
              }}
            />

            <button
              onClick={() => setSelectedPersona(selected ? null : persona.id)}
              title={`${persona.name} — ${persona.title}`}
              style={{
                position: 'absolute',
                left: `${x}%`,
                top: `${y}%`,
                transform: 'translate(-50%, -50%)',
                minWidth: 132,
                maxWidth: 208,
                padding: '10px 12px 10px 42px',
                borderRadius: 14,
                border: `1px solid ${selected ? `${color}80` : `${color}2E`}`,
                background: selected ? 'rgba(10,14,20,0.94)' : 'rgba(8,12,18,0.86)',
                boxShadow: selected ? `0 0 22px rgba(${hexToRgb(color)}, 0.22)` : `0 12px 28px rgba(${hexToRgb(color)}, 0.08)`,
                color: '#EEF3FF',
                cursor: 'pointer',
                textAlign: 'left',
                animation: 'committeeFloat 4s ease-in-out infinite',
                zIndex: 3,
              }}
            >
              <div
                style={{
                  position: 'absolute',
                  left: 11,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  width: 22,
                  height: 22,
                  borderRadius: '50%',
                  background: color,
                  boxShadow: `0 0 14px ${color}`,
                }}
              />
              <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 11, fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {persona.name}
              </div>
              <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 10, color: '#8C97A7', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', marginTop: 3 }}>
                {persona.title}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4 }}>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color, letterSpacing: '0.09em', textTransform: 'uppercase' }}>
                  {sentimentLabel(persona.sentiment)}
                </span>
                <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#EEF3FF' }}>
                  {formatScore(persona.currentScore)}
                </span>
              </div>
            </button>

            {quote && (
              <div
                style={{
                  position: 'absolute',
                  left: `${quoteX}%`,
                  top: `${quoteY}%`,
                  transform: 'translate(-50%, -50%)',
                  maxWidth: 190,
                  padding: '5px 9px',
                  borderRadius: 999,
                  background: 'rgba(8,12,18,0.84)',
                  border: `1px solid ${color}24`,
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: 10,
                  color,
                  whiteSpace: 'nowrap',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  pointerEvents: 'none',
                  zIndex: 2,
                }}
              >
                {quote}
              </div>
            )}
          </React.Fragment>
        );
      })}

      {sectionNodes.length > 0 && (
        <div
          style={{
            position: 'absolute',
            left: '50%',
            bottom: 26,
            transform: 'translateX(-50%)',
            width: '68%',
            zIndex: 3,
          }}
        >
          <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, letterSpacing: '0.12em', color: '#4B5563', textTransform: 'uppercase', marginBottom: 7 }}>
            Section Flow
          </div>
          <div style={{ position: 'relative', height: 20 }}>
            {sectionNodes.map((section) => (
              <div
                key={section.id}
                title={`Section ${section.id}: ${section.title}`}
                style={{
                  position: 'absolute',
                  left: `${section.left}%`,
                  top: '50%',
                  transform: 'translate(-50%, -50%)',
                  width: section.active ? 42 : 28,
                  height: section.active ? 12 : 8,
                  borderRadius: 999,
                  background: section.active
                    ? 'linear-gradient(90deg, rgba(124,231,255,0.95) 0%, rgba(77,163,255,0.95) 100%)'
                    : 'rgba(255,255,255,0.10)',
                  boxShadow: section.active ? '0 0 16px rgba(124,231,255,0.65)' : 'none',
                  animation: section.active ? 'committeePulse 1.6s ease-in-out infinite' : 'none',
                }}
              />
            ))}
          </div>
        </div>
      )}

      <div
        style={{
          position: 'absolute',
          right: 24,
          bottom: 24,
          width: 220,
          padding: '10px 12px',
          borderRadius: 12,
          background: 'rgba(8,12,18,0.78)',
          border: `1px solid ${PANEL_BORDER}`,
          zIndex: 3,
        }}
      >
        <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, letterSpacing: '0.12em', color: '#6B7480', textTransform: 'uppercase', marginBottom: 6 }}>
          Reading The Room
        </div>
        <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 11, lineHeight: 1.55, color: '#95A1B1' }}>
          The document sits at the center. Stronger supporters pull closer, objections surface as quote fragments, and the active section pulses as each rewrite is tested.
        </div>
      </div>

      <div
        style={{
          position: 'absolute',
          left: 24,
          bottom: 24,
          zIndex: 3,
          display: 'flex',
          gap: 8,
        }}
      >
        {[
          ['Document', '#7CE7FF'],
          ['Supportive', '#4ADE80'],
          ['Neutral', '#FBBF24'],
          ['Opposed', '#FB7185'],
        ].map(([label, color]) => (
          <div
            key={label}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '7px 9px',
              borderRadius: 999,
              background: 'rgba(8,12,18,0.74)',
              border: `1px solid ${PANEL_BORDER}`,
            }}
          >
            <div style={{ width: 7, height: 7, borderRadius: '50%', background: color, boxShadow: `0 0 8px ${color}` }} />
            <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#9AA4B2', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
              {label}
            </span>
          </div>
        ))}
      </div>

      {selectedPersonaId && (
        <div
          style={{
            position: 'absolute',
            left: '50%',
            top: '50%',
            transform: 'translate(-50%, 112px)',
            zIndex: 3,
            padding: '8px 12px',
            borderRadius: 999,
            background: 'rgba(8,12,18,0.84)',
            border: `1px solid ${PANEL_BORDER}`,
            fontFamily: 'Inter, sans-serif',
            fontSize: 11,
            color: '#9AA4B2',
          }}
        >
          Click a persona node to inspect objections and section scores in the right rail.
        </div>
      )}
    </div>
  );
}

function hexToRgb(hex: string): string {
  const match = hex.match(/^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i);
  if (!match) {
    return '154,164,178';
  }
  return `${parseInt(match[1], 16)},${parseInt(match[2], 16)},${parseInt(match[3], 16)}`;
}
