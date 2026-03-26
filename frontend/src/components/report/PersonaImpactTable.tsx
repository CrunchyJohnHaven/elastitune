import React from 'react';
import type { PersonaImpactRow } from '@/types/contracts';
import { PANEL_BORDER } from '@/lib/theme';

interface PersonaImpactTableProps {
  personaImpact: PersonaImpactRow[];
}

function DeltaBadge({ delta }: { delta: number }) {
  const isPositive = delta >= 0;
  return (
    <span
      style={{
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: 11,
        fontWeight: 600,
        color: isPositive ? '#4ADE80' : '#FB7185',
        background: isPositive
          ? 'rgba(74,222,128,0.08)'
          : 'rgba(251,113,133,0.08)',
        padding: '2px 7px',
        borderRadius: 4,
      }}
    >
      {isPositive ? '+' : ''}{delta.toFixed(1)}%
    </span>
  );
}

export default function PersonaImpactTable({ personaImpact }: PersonaImpactTableProps) {
  const sorted = [...personaImpact].sort((a, b) => b.deltaPct - a.deltaPct);

  const thStyle: React.CSSProperties = {
    fontFamily: 'Inter, sans-serif',
    fontSize: 10,
    fontWeight: 600,
    color: '#6B7480',
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    padding: '8px 14px',
    textAlign: 'left',
    borderBottom: `1px solid ${PANEL_BORDER}`,
    background: 'rgba(255,255,255,0.02)',
  };

  const tdStyle: React.CSSProperties = {
    fontFamily: 'Inter, sans-serif',
    fontSize: 12,
    color: '#9AA4B2',
    padding: '9px 14px',
    borderBottom: `1px solid ${PANEL_BORDER}`,
    verticalAlign: 'middle',
  };

  return (
    <div style={{ marginBottom: 32 }}>
      <h2
        style={{
          fontFamily: 'Inter, sans-serif',
          fontWeight: 600,
          fontSize: 17,
          color: '#EEF3FF',
          marginBottom: 16,
        }}
      >
        Persona Impact
      </h2>

      <div
        style={{
          border: `1px solid ${PANEL_BORDER}`,
          borderRadius: 8,
          overflow: 'hidden',
        }}
      >
        <table
          style={{
            width: '100%',
            borderCollapse: 'collapse',
          }}
        >
          <thead>
            <tr>
              <th style={thStyle}>Name</th>
              <th style={thStyle}>Role</th>
              <th style={{ ...thStyle, textAlign: 'right' }}>Before</th>
              <th style={{ ...thStyle, textAlign: 'right' }}>After</th>
              <th style={{ ...thStyle, textAlign: 'right' }}>Delta</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map(row => (
              <tr
                key={row.personaId}
                style={{
                  background:
                    row.deltaPct > 5
                      ? 'rgba(74,222,128,0.02)'
                      : row.deltaPct < -5
                      ? 'rgba(251,113,133,0.02)'
                      : 'transparent',
                }}
              >
                <td
                  style={{
                    ...tdStyle,
                    fontWeight: 500,
                    color: '#EEF3FF',
                  }}
                >
                  {row.name}
                </td>
                <td style={{ ...tdStyle, color: '#6B7480' }}>{row.role}</td>
                <td
                  style={{
                    ...tdStyle,
                    textAlign: 'right',
                    fontFamily: 'JetBrains Mono, monospace',
                    color: '#6B7480',
                  }}
                >
                  {(row.beforeSuccessRate * 100).toFixed(0)}%
                </td>
                <td
                  style={{
                    ...tdStyle,
                    textAlign: 'right',
                    fontFamily: 'JetBrains Mono, monospace',
                    color: '#9AA4B2',
                  }}
                >
                  {(row.afterSuccessRate * 100).toFixed(0)}%
                </td>
                <td style={{ ...tdStyle, textAlign: 'right' }}>
                  <DeltaBadge delta={row.deltaPct} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
