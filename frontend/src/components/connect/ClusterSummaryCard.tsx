import React, { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import type { ConnectionSummary } from '@/types/contracts';
import { formatDocCount } from '@/lib/format';
import { PANEL_BORDER, ACCENT_BLUE } from '@/lib/theme';

interface RunLaunchOptions {
  durationMinutes: number;
  maxExperiments: number;
  personaCount: number;
  autoStopOnPlateau: boolean;
}

interface ClusterSummaryCardProps {
  summary: ConnectionSummary;
  connectionId: string;
  onStartOptimization: (connectionId: string, options: RunLaunchOptions) => void;
  isLoading?: boolean;
}

const DOMAIN_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  security: {
    label: 'Security',
    color: '#4DA3FF',
    bg: 'rgba(77,163,255,0.12)',
  },
  developer_docs: {
    label: 'Developer Docs',
    color: '#A78BFA',
    bg: 'rgba(167,139,250,0.12)',
  },
  compliance: {
    label: 'Compliance',
    color: '#FBBF24',
    bg: 'rgba(251,191,36,0.12)',
  },
  general: {
    label: 'General',
    color: '#9AA4B2',
    bg: 'rgba(154,164,178,0.1)',
  },
};

function FieldChip({ label }: { label: string }) {
  return (
    <span
      style={{
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: 10,
        color: '#9AA4B2',
        background: 'rgba(255,255,255,0.05)',
        border: '1px solid rgba(255,255,255,0.08)',
        borderRadius: 4,
        padding: '2px 7px',
        whiteSpace: 'nowrap',
      }}
    >
      {label}
    </span>
  );
}

export default function ClusterSummaryCard({
  summary,
  connectionId,
  onStartOptimization,
  isLoading,
}: ClusterSummaryCardProps) {
  const domain = DOMAIN_CONFIG[summary.detectedDomain] ?? DOMAIN_CONFIG.general;
  const [durationMinutes, setDurationMinutes] = useState(30);
  const [maxExperiments, setMaxExperiments] = useState(60);
  const [personaCount, setPersonaCount] = useState(36);
  const [autoStopOnPlateau, setAutoStopOnPlateau] = useState(true);
  const [tuneOpen, setTuneOpen] = useState(false);
  const isBenchmarkTarget = summary.indexName === 'products-catalog';

  return (
    <div
      style={{
        background: 'rgba(10,14,20,0.6)',
        border: `1px solid rgba(74,222,128,0.25)`,
        borderRadius: 10,
        padding: '18px 20px',
        marginTop: 16,
        boxShadow: '0 0 32px rgba(74,222,128,0.05)',
      }}
    >
      {/* Header row */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          marginBottom: 14,
          gap: 12,
        }}
      >
        <div>
          <div
            style={{
              fontFamily: 'Inter, sans-serif',
              fontWeight: 600,
              fontSize: 15,
              color: '#EEF3FF',
              marginBottom: 2,
            }}
          >
            {summary.clusterName}
          </div>
          <div
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 11,
              color: '#6B7480',
            }}
          >
            {summary.indexName}
          </div>
        </div>

        {/* Domain badge */}
        <span
          style={{
            fontFamily: 'Inter, sans-serif',
            fontSize: 11,
            fontWeight: 500,
            padding: '3px 10px',
            borderRadius: 20,
            background: domain.bg,
            color: domain.color,
            border: `1px solid ${domain.color}33`,
            whiteSpace: 'nowrap',
            flexShrink: 0,
          }}
        >
          {domain.label}
        </span>
      </div>

      {/* Stats grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 10,
          marginBottom: 14,
        }}
      >
        {[
          { label: 'Documents', value: formatDocCount(summary.docCount) },
          { label: 'ES Version', value: summary.clusterVersion ?? '—' },
          { label: 'Eval Cases', value: String(summary.baselineEvalCount) },
        ].map(stat => (
          <div
            key={stat.label}
            style={{
              background: 'rgba(255,255,255,0.03)',
              borderRadius: 6,
              padding: '8px 10px',
              border: '1px solid rgba(255,255,255,0.05)',
            }}
          >
            <div
              style={{
                fontFamily: 'Inter, sans-serif',
                fontSize: 10,
                color: '#6B7480',
                marginBottom: 3,
              }}
            >
              {stat.label}
            </div>
            <div
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 14,
                fontWeight: 600,
                color: '#EEF3FF',
              }}
            >
              {stat.value}
            </div>
          </div>
        ))}
      </div>

      {isBenchmarkTarget && (
        <div
          style={{
            marginBottom: 14,
            padding: '10px 12px',
            borderRadius: 8,
            border: '1px solid rgba(77,163,255,0.16)',
            background: 'rgba(77,163,255,0.05)',
          }}
        >
          <div
            style={{
              fontFamily: 'Inter, sans-serif',
              fontSize: 12,
              fontWeight: 600,
              color: '#EEF3FF',
              marginBottom: 3,
            }}
          >
            Benchmark target detected
          </div>
          <div
            style={{
              fontFamily: 'Inter, sans-serif',
              fontSize: 11,
              color: '#9AA4B2',
              lineHeight: 1.45,
            }}
          >
            This matches the Elastic product-store benchmark pack. Recommended run: 30 minutes, 40-60 experiments, 36 personas.
          </div>
        </div>
      )}

      {/* Text fields */}
      {summary.primaryTextFields.length > 0 && (
        <div style={{ marginBottom: 10 }}>
          <div
            style={{
              fontFamily: 'Inter, sans-serif',
              fontSize: 10,
              color: '#6B7480',
              marginBottom: 5,
            }}
          >
            Text fields
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
            {summary.primaryTextFields.map(f => (
              <FieldChip key={f} label={f} />
            ))}
          </div>
        </div>
      )}

      {/* Vector field */}
      <div
        style={{
          fontFamily: 'Inter, sans-serif',
          fontSize: 11,
          color: '#6B7480',
          marginBottom: 12,
          display: 'flex',
          alignItems: 'center',
          gap: 6,
        }}
      >
        <span>Vector field:</span>
        {summary.vectorField ? (
          <span
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              color: '#7CE7FF',
              fontSize: 11,
            }}
          >
            {summary.vectorField}
            {summary.vectorDims ? ` (${summary.vectorDims}d)` : ''}
          </span>
        ) : (
          <span style={{ color: '#4B5563', fontStyle: 'italic' }}>
            No vector field
          </span>
        )}
      </div>

      {/* Warnings */}
      {/* (warnings are on ConnectResponse, not summary — skipped here for type safety) */}

      {/* Divider */}
      <div
        style={{
          height: 1,
          background: PANEL_BORDER,
          marginBottom: 14,
        }}
      />

      {/* Collapsible run configuration */}
      <div style={{ marginBottom: 14 }}>
        <button
          type="button"
          onClick={() => setTuneOpen(o => !o)}
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'none',
            border: '1px solid rgba(255,255,255,0.07)',
            borderRadius: 7,
            padding: '8px 12px',
            cursor: 'pointer',
            color: '#6B7480',
            fontFamily: 'Inter, sans-serif',
            fontSize: 11,
            fontWeight: 500,
          }}
        >
          <span>Tune run settings</span>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {!tuneOpen && (
              <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#4B5563' }}>
                {durationMinutes}m \u00B7 {maxExperiments} exp \u00B7 {personaCount} personas
              </span>
            )}
            {tuneOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </div>
        </button>

        {tuneOpen && (
          <div
            style={{
              marginTop: 8,
              padding: '12px',
              background: 'rgba(255,255,255,0.02)',
              borderRadius: 8,
              border: '1px solid rgba(255,255,255,0.06)',
            }}
          >
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
                gap: 8,
                marginBottom: 10,
              }}
            >
              {[
                {
                  label: 'Duration',
                  hint: 'Total run time limit',
                  value: String(durationMinutes),
                  onChange: setDurationMinutes,
                  options: [10, 20, 30, 45],
                  suffix: 'm',
                  defaultVal: 30,
                },
                {
                  label: 'Experiments',
                  hint: 'More = more thorough',
                  value: String(maxExperiments),
                  onChange: setMaxExperiments,
                  options: [20, 40, 60, 80],
                  suffix: '',
                  defaultVal: 60,
                },
                {
                  label: 'Personas',
                  hint: 'Simulated user types',
                  value: String(personaCount),
                  onChange: setPersonaCount,
                  options: [24, 36, 48, 60],
                  suffix: '',
                  defaultVal: 36,
                },
              ].map(control => (
                <label key={control.label} style={{ display: 'block' }}>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: 4, marginBottom: 4 }}>
                    <span style={{ fontFamily: 'Inter, sans-serif', fontSize: 10, color: '#6B7480' }}>
                      {control.label}
                    </span>
                    {Number(control.value) === control.defaultVal && (
                      <span style={{ fontFamily: 'Inter, sans-serif', fontSize: 8, color: '#4DA3FF', letterSpacing: '0.05em' }}>
                        REC
                      </span>
                    )}
                  </div>
                  <select
                    value={control.value}
                    onChange={e => control.onChange(Number(e.target.value))}
                    style={{
                      width: '100%',
                      padding: '8px 10px',
                      background: 'rgba(255,255,255,0.03)',
                      border: '1px solid rgba(255,255,255,0.08)',
                      borderRadius: 6,
                      color: '#EEF3FF',
                      fontFamily: 'JetBrains Mono, monospace',
                      fontSize: 11,
                      appearance: 'none',
                    }}
                  >
                    {control.options.map(option => (
                      <option key={option} value={option}>
                        {`${option}${control.suffix}`}
                      </option>
                    ))}
                  </select>
                  <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 9, color: '#4B5563', marginTop: 3 }}>
                    {control.hint}
                  </div>
                </label>
              ))}
            </div>

            <button
              type="button"
              onClick={() => setAutoStopOnPlateau(v => !v)}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '8px 10px',
                borderRadius: 7,
                border: '1px solid rgba(255,255,255,0.06)',
                background: 'rgba(255,255,255,0.02)',
                color: '#9AA4B2',
                fontFamily: 'Inter, sans-serif',
                fontSize: 11,
                cursor: 'pointer',
              }}
            >
              <div>
                <span>Auto-stop when score plateaus</span>
                <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 9, color: '#4B5563', marginTop: 2 }}>
                  Stops early if improvements stall
                </div>
              </div>
              <span style={{ color: autoStopOnPlateau ? ACCENT_BLUE : '#6B7480' }}>
                {autoStopOnPlateau ? 'On' : 'Off'}
              </span>
            </button>
          </div>
        )}
      </div>

      {/* CTA */}
      <button
        onClick={() =>
          onStartOptimization(connectionId, {
            durationMinutes,
            maxExperiments,
            personaCount,
            autoStopOnPlateau,
          })
        }
        disabled={isLoading}
        style={{
          width: '100%',
          padding: '12px',
          background: isLoading
            ? 'rgba(77,163,255,0.3)'
            : 'linear-gradient(135deg, #4DA3FF 0%, #3D8BFF 100%)',
          color: '#fff',
          border: 'none',
          borderRadius: 8,
          fontFamily: 'Inter, sans-serif',
          fontWeight: 600,
          fontSize: 14,
          cursor: isLoading ? 'not-allowed' : 'pointer',
          boxShadow: isLoading ? 'none' : '0 0 24px rgba(77,163,255,0.4)',
          transition: 'box-shadow 0.2s, transform 0.1s',
          opacity: isLoading ? 0.7 : 1,
        }}
        onMouseEnter={e => {
          if (!isLoading) {
            (e.currentTarget as HTMLButtonElement).style.boxShadow =
              '0 0 36px rgba(77,163,255,0.6)';
            (e.currentTarget as HTMLButtonElement).style.transform = 'translateY(-1px)';
          }
        }}
        onMouseLeave={e => {
          if (!isLoading) {
            (e.currentTarget as HTMLButtonElement).style.boxShadow =
              '0 0 24px rgba(77,163,255,0.4)';
            (e.currentTarget as HTMLButtonElement).style.transform = 'translateY(0)';
          }
        }}
      >
        {isLoading ? 'Starting…' : 'Start Optimization →'}
      </button>
    </div>
  );
}
