import React, { memo } from 'react';
import type { PersonaViewModel } from '@/types/contracts';
import { personaColor, STATE_COLORS, PANEL_BORDER } from '@/lib/theme';
import { initials, truncate } from '@/lib/format';

interface PersonaListProps {
  personas: PersonaViewModel[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
}

function StateDot({ state }: { state: PersonaViewModel['state'] }) {
  const color = STATE_COLORS[state];
  const isPulsing = state === 'searching';

  return (
    <div style={{ position: 'relative', width: 8, height: 8, flexShrink: 0 }}>
      {isPulsing && (
        <div
          style={{
            position: 'absolute',
            inset: -3,
            borderRadius: '50%',
            background: color,
            opacity: 0.3,
            animation: 'personaDotPulse 1s ease-in-out infinite',
          }}
        />
      )}
      <div
        style={{
          width: 8,
          height: 8,
          borderRadius: '50%',
          background: color,
          position: 'relative',
          zIndex: 1,
        }}
      />
    </div>
  );
}

function SuccessBar({ rate }: { rate: number }) {
  const color =
    rate >= 0.7 ? '#4ADE80' : rate >= 0.5 ? '#FBBF24' : '#FB7185';
  return (
    <div
      style={{
        width: '100%',
        height: 2,
        background: 'rgba(255,255,255,0.06)',
        borderRadius: 1,
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          height: '100%',
          width: `${rate * 100}%`,
          background: color,
          borderRadius: 1,
          transition: 'width 0.6s ease',
        }}
      />
    </div>
  );
}

const PersonaRow = memo(function PersonaRow({
  persona,
  isSelected,
  onSelect,
}: {
  persona: PersonaViewModel;
  isSelected: boolean;
  onSelect: (id: string | null) => void;
}) {
  const avatarColor = personaColor(persona.colorSeed);
  const abbr = initials(persona.name);

  return (
    <div
      onClick={() => onSelect(isSelected ? null : persona.id)}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        padding: '8px 12px',
        borderBottom: `1px solid ${PANEL_BORDER}`,
        cursor: 'pointer',
        background: isSelected
          ? 'rgba(77,163,255,0.06)'
          : 'transparent',
        borderLeft: isSelected
          ? '2px solid rgba(77,163,255,0.5)'
          : '2px solid transparent',
        transition: 'background 0.15s, border-color 0.15s',
      }}
      onMouseEnter={event => {
        event.currentTarget.style.background = isSelected
          ? 'rgba(77,163,255,0.08)'
          : 'rgba(255,255,255,0.02)';
      }}
      onMouseLeave={event => {
        event.currentTarget.style.background = isSelected
          ? 'rgba(77,163,255,0.06)'
          : 'transparent';
      }}
    >
      {/* Avatar */}
      <div
        style={{
          width: 28,
          height: 28,
          borderRadius: '50%',
          background: avatarColor,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          fontFamily: 'Inter, sans-serif',
          fontWeight: 700,
          fontSize: 10,
          color: '#fff',
          boxShadow: isSelected
            ? `0 0 8px ${avatarColor}`
            : 'none',
        }}
      >
        {abbr}
      </div>

      {/* Info */}
      <div style={{ flex: 1, overflow: 'hidden', minWidth: 0 }}>
        {/* Name + state dot */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 1,
          }}
        >
          <span
            style={{
              fontFamily: 'Inter, sans-serif',
              fontWeight: 500,
              fontSize: 12,
              color: isSelected ? '#EEF3FF' : '#C5CDD8',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {truncate(persona.name, 20)}
          </span>
          <StateDot state={persona.state} />
        </div>

        {/* Role */}
        <div
          style={{
            fontFamily: 'Inter, sans-serif',
            fontSize: 10,
            color: '#6B7480',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
            marginBottom: 4,
          }}
        >
          {persona.role}
        </div>

        {/* Success bar */}
        <SuccessBar rate={persona.successRate} />

        {/* Last query */}
        {persona.lastQuery && (
          <div
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 9,
              color: '#4B5563',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              marginTop: 3,
            }}
          >
            {truncate(persona.lastQuery, 30)}
          </div>
        )}
      </div>
    </div>
  );
});

export default function PersonaList({ personas, selectedId, onSelect }: PersonaListProps) {
  return (
    <>
      <style>{`
        @keyframes personaDotPulse {
          0%, 100% { transform: scale(1); opacity: 0.3; }
          50% { transform: scale(1.8); opacity: 0.1; }
        }
      `}</style>
      <div
        style={{
          overflowY: 'auto',
          flex: 1,
          scrollbarWidth: 'thin',
          scrollbarColor: 'rgba(255,255,255,0.07) transparent',
        }}
      >
        {personas.length === 0 ? (
          <div
            style={{
              padding: '16px',
              textAlign: 'center',
              fontFamily: 'Inter, sans-serif',
              fontSize: 12,
              color: '#4B5563',
              fontStyle: 'italic',
            }}
          >
            No personas loaded yet
          </div>
        ) : (
          personas.map(p => (
            <PersonaRow
              key={p.id}
              persona={p}
              isSelected={selectedId === p.id}
              onSelect={onSelect}
            />
          ))
        )}
      </div>
    </>
  );
}
