import React, { memo } from 'react';
import type { PersonaActivityEntry, PersonaViewModel } from '@/types/contracts';
import { initials, truncate } from '@/lib/format';
import { personaColor, PANEL_BORDER, STATE_COLORS } from '@/lib/theme';

interface PersonaDetailCardProps {
  persona: PersonaViewModel | null;
  activity: PersonaActivityEntry[];
}

function DetailStat({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div
      style={{
        padding: '8px 10px',
        borderRadius: 8,
        border: `1px solid ${PANEL_BORDER}`,
        background: 'rgba(255,255,255,0.02)',
      }}
    >
      <div
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 9,
          color: '#6B7480',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          marginBottom: 4,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 14,
          fontWeight: 600,
          color: color ?? '#EEF3FF',
        }}
      >
        {value}
      </div>
    </div>
  );
}

function formatPersonaOutcome(persona: PersonaViewModel) {
  if (persona.lastResultRank != null) {
    return `Rank #${persona.lastResultRank}`;
  }
  if (persona.state === 'failure') return 'No relevant result';
  if (persona.state === 'searching') return 'Query in-flight';
  return 'No recent result';
}

function formatPersonaState(persona: PersonaViewModel) {
  switch (persona.state) {
    case 'success':
      return 'Resolved';
    case 'partial':
      return 'Partial';
    case 'failure':
      return 'Missed';
    case 'searching':
      return 'Searching';
    case 'reacting':
      return 'Reacting';
    default:
      return 'Standing By';
  }
}

function formatActivityAge(timestamp: string) {
  const deltaSeconds = Math.max(0, Math.floor((Date.now() - Date.parse(timestamp)) / 1000));
  if (deltaSeconds < 5) return 'now';
  if (deltaSeconds < 60) return `${deltaSeconds}s ago`;
  const minutes = Math.floor(deltaSeconds / 60);
  return `${minutes}m ago`;
}

function activityAccent(kind: PersonaActivityEntry['kind']) {
  switch (kind) {
    case 'success':
      return '#4ADE80';
    case 'partial':
      return '#FBBF24';
    case 'failure':
      return '#FB7185';
    case 'reacting':
      return '#EEF3FF';
    default:
      return '#4DA3FF';
  }
}

function PersonaDetailCard({ persona, activity }: PersonaDetailCardProps) {
  if (!persona) {
    return (
      <div style={{ padding: '12px' }}>
        <div
          style={{
            padding: '14px 12px',
            border: `1px dashed ${PANEL_BORDER}`,
            borderRadius: 10,
            color: '#6B7480',
            fontFamily: 'Inter, sans-serif',
            fontSize: 12,
            textAlign: 'center',
          }}
        >
          Select a persona to inspect its intent, recent query, and outcomes.
        </div>
      </div>
    );
  }

  const avatarColor = personaColor(persona.colorSeed);
  const successRate = `${Math.round(persona.successRate * 100)}%`;
  const lastOutcome = formatPersonaOutcome(persona);
  const stateLabel = formatPersonaState(persona);
  const stateColor = STATE_COLORS[persona.state];

  return (
    <div style={{ padding: '12px', display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div
        style={{
          border: `1px solid ${PANEL_BORDER}`,
          borderRadius: 12,
          background: 'rgba(255,255,255,0.02)',
          padding: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
          <div
            style={{
              width: 34,
              height: 34,
              borderRadius: '50%',
              background: avatarColor,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              fontFamily: 'Inter, sans-serif',
              fontWeight: 700,
              fontSize: 11,
              boxShadow: `0 0 14px ${avatarColor}`,
              flexShrink: 0,
            }}
          >
            {initials(persona.name)}
          </div>
          <div style={{ minWidth: 0, flex: 1 }}>
            <div
              style={{
                fontFamily: 'Inter, sans-serif',
                fontWeight: 600,
                fontSize: 14,
                color: '#EEF3FF',
                marginBottom: 2,
              }}
            >
              {persona.name}
            </div>
            <div
              style={{
                fontFamily: 'Inter, sans-serif',
                fontSize: 11,
                color: '#9AA4B2',
              }}
            >
              {persona.role} · {persona.department}
            </div>
          </div>
          <div
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 9,
              fontWeight: 700,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: stateColor,
              border: `1px solid ${stateColor.replace('0.9', '0.24').replace('0.7', '0.24')}`,
              background: stateColor.replace('0.9', '0.08').replace('0.7', '0.08'),
              borderRadius: 999,
              padding: '4px 8px',
              whiteSpace: 'nowrap',
            }}
          >
            {stateLabel}
          </div>
        </div>

        <div
          style={{
            fontFamily: 'Inter, sans-serif',
            fontSize: 11,
            color: '#6B7480',
            marginBottom: 4,
          }}
        >
          {persona.archetype} operator
        </div>
        <div
          style={{
            fontFamily: 'Inter, sans-serif',
            fontSize: 12,
            color: '#C5CDD8',
            lineHeight: 1.45,
          }}
        >
          {persona.goal}
        </div>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
          gap: 8,
        }}
      >
        <DetailStat label="Success Rate" value={successRate} color="#4ADE80" />
        <DetailStat label="Searches" value={String(persona.totalSearches)} />
        <DetailStat label="Resolved" value={String(persona.successes)} color="#4ADE80" />
        <DetailStat label="Misses" value={String(persona.failures)} color="#FB7185" />
      </div>

      <div
        style={{
          border: `1px solid ${PANEL_BORDER}`,
          borderRadius: 10,
          background: 'rgba(255,255,255,0.02)',
          padding: '10px 12px',
        }}
      >
        <div
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 9,
            color: '#6B7480',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            marginBottom: 8,
          }}
        >
          Recent Activity
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div>
            <div
              style={{
                fontFamily: 'Inter, sans-serif',
                fontSize: 10,
                color: '#6B7480',
                marginBottom: 3,
              }}
            >
              Last query
            </div>
            <div
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 11,
                color: '#EEF3FF',
                lineHeight: 1.45,
              }}
            >
              {persona.lastQuery ? truncate(persona.lastQuery, 72) : 'No query yet'}
            </div>
          </div>
          <div>
            <div
              style={{
                fontFamily: 'Inter, sans-serif',
                fontSize: 10,
                color: '#6B7480',
                marginBottom: 3,
              }}
            >
              Last outcome
            </div>
            <div
              style={{
                fontFamily: 'Inter, sans-serif',
                fontSize: 12,
                color: '#C5CDD8',
              }}
            >
              {lastOutcome}
            </div>
          </div>
        </div>
      </div>

      <div
        style={{
          border: `1px solid ${PANEL_BORDER}`,
          borderRadius: 10,
          background: 'rgba(255,255,255,0.02)',
          padding: '10px 12px',
        }}
      >
        <div
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 9,
            color: '#6B7480',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            marginBottom: 8,
          }}
        >
          Activity Trail
        </div>

        {activity.length === 0 ? (
          <div
            style={{
              padding: '8px 0',
              color: '#6B7480',
              fontFamily: 'Inter, sans-serif',
              fontSize: 12,
            }}
          >
            This persona has not emitted any search events yet.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 9 }}>
            {activity.map((entry) => {
              const accent = activityAccent(entry.kind);
              return (
                <div
                  key={entry.id}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '10px 1fr auto',
                    gap: 8,
                    alignItems: 'start',
                  }}
                >
                  <div
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      background: accent,
                      boxShadow: `0 0 10px ${accent}`,
                      marginTop: 4,
                    }}
                  />
                  <div style={{ minWidth: 0 }}>
                    <div
                      style={{
                        fontFamily: 'Inter, sans-serif',
                        fontSize: 12,
                        color: '#EEF3FF',
                        marginBottom: 2,
                      }}
                    >
                      {entry.title}
                    </div>
                    <div
                      style={{
                        fontFamily: 'JetBrains Mono, monospace',
                        fontSize: 10,
                        lineHeight: 1.5,
                        color: '#9AA4B2',
                        wordBreak: 'break-word',
                      }}
                    >
                      {truncate(entry.detail, 84)}
                    </div>
                  </div>
                  <div
                    style={{
                      fontFamily: 'JetBrains Mono, monospace',
                      fontSize: 9,
                      color: '#6B7480',
                      whiteSpace: 'nowrap',
                      marginTop: 1,
                    }}
                  >
                    {formatActivityAge(entry.timestamp)}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div
        style={{
          border: `1px solid ${PANEL_BORDER}`,
          borderRadius: 10,
          background: 'rgba(255,255,255,0.02)',
          padding: '10px 12px',
        }}
      >
        <div
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 9,
            color: '#6B7480',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            marginBottom: 8,
          }}
        >
          Search Focus
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {persona.queries.slice(0, 4).map(query => (
            <span
              key={query}
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 9,
                color: '#9AA4B2',
                padding: '4px 6px',
                borderRadius: 999,
                background: 'rgba(77,163,255,0.08)',
                border: '1px solid rgba(77,163,255,0.14)',
              }}
            >
              {truncate(query, 26)}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}

export default memo(PersonaDetailCard);
