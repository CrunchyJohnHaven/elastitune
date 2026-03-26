import React from 'react';
import ReactDOM from 'react-dom';
import type { PersonaViewModel } from '@/types/contracts';
import { PANEL_BORDER } from '@/lib/theme';

interface TooltipPortalProps {
  persona: PersonaViewModel | null;
  x: number;
  y: number;
  visible: boolean;
}

export default function TooltipPortal({ persona, x, y, visible }: TooltipPortalProps) {
  if (!visible || !persona) return null;

  const content = (
    <div
      style={{
        position: 'fixed',
        left: x + 14,
        top: y - 10,
        zIndex: 9999,
        pointerEvents: 'none',
        background: 'rgba(10, 14, 20, 0.92)',
        border: `1px solid ${PANEL_BORDER}`,
        borderRadius: 8,
        padding: '10px 14px',
        minWidth: 180,
        maxWidth: 240,
        backdropFilter: 'blur(16px)',
        boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
      }}
    >
      <div
        style={{
          fontFamily: 'Inter, sans-serif',
          fontWeight: 600,
          fontSize: 13,
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
          marginBottom: 6,
        }}
      >
        {persona.role} · {persona.department}
      </div>

      {persona.lastQuery && (
        <div
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 10,
            color: '#6B7480',
            fontStyle: 'italic',
            marginBottom: 6,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          "{persona.lastQuery}"
        </div>
      )}

      {persona.lastResultRank != null && (
        <div
          style={{
            fontFamily: 'Inter, sans-serif',
            fontSize: 10,
            color: '#9AA4B2',
            marginBottom: 4,
          }}
        >
          Last rank:{' '}
          <span style={{ color: '#EEF3FF' }}>#{persona.lastResultRank}</span>
        </div>
      )}

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          marginTop: 4,
        }}
      >
        <div
          style={{
            flex: 1,
            height: 3,
            borderRadius: 2,
            background: 'rgba(255,255,255,0.08)',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              height: '100%',
              width: `${persona.successRate * 100}%`,
              background:
                persona.successRate >= 0.7
                  ? '#4ADE80'
                  : persona.successRate >= 0.5
                  ? '#FBBF24'
                  : '#FB7185',
              borderRadius: 2,
            }}
          />
        </div>
        <span
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 10,
            color: '#9AA4B2',
            whiteSpace: 'nowrap',
          }}
        >
          {(persona.successRate * 100).toFixed(0)}% success
        </span>
      </div>
    </div>
  );

  return ReactDOM.createPortal(content, document.body);
}
