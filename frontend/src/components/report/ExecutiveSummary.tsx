import React from 'react';
import type { ReportPayload } from '@/types/contracts';
import { formatScore, formatPercent, formatDollars } from '@/lib/format';
import { PANEL_BORDER, ACCENT_BLUE } from '@/lib/theme';

interface ExecutiveSummaryProps {
  report: ReportPayload;
}

function MetricCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: string;
}) {
  return (
    <div
      style={{
        background: 'rgba(255,255,255,0.025)',
        border: `1px solid ${PANEL_BORDER}`,
        borderRadius: 10,
        padding: '18px 20px',
        textAlign: 'center',
      }}
    >
      <div
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 28,
          fontWeight: 700,
          color: accent ?? '#EEF3FF',
          letterSpacing: '-0.02em',
          marginBottom: 4,
          lineHeight: 1,
        }}
      >
        {value}
      </div>
      {sub && (
        <div
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 11,
            color: '#6B7480',
            marginBottom: 6,
          }}
        >
          {sub}
        </div>
      )}
      <div
        style={{
          fontFamily: 'Inter, sans-serif',
          fontSize: 11,
          color: '#6B7480',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
        }}
      >
        {label}
      </div>
    </div>
  );
}

export default function ExecutiveSummary({ report }: ExecutiveSummaryProps) {
  const { summary, generatedAt, mode } = report;
  const improvementPositive = summary.improvementPct >= 0;
  const isContinuation = summary.isContinuation ?? false;
  const displayExperiments = summary.totalExperimentsRun ?? summary.experimentsRun;
  const displayKept = summary.totalImprovementsKept ?? summary.improvementsKept;

  const generatedDate = new Date(generatedAt).toLocaleString('en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });

  const formatDuration = (durationSeconds: number) => {
    if (!durationSeconds || durationSeconds <= 0) return '—';
    if (durationSeconds < 60) return `${Math.max(1, Math.round(durationSeconds))} sec`;
    if (durationSeconds < 3600) return `${Math.max(1, Math.round(durationSeconds / 60))} min`;
    const hours = Math.floor(durationSeconds / 3600);
    const minutes = Math.round((durationSeconds % 3600) / 60);
    return minutes > 0 ? `${hours}h ${minutes}m` : `${hours}h`;
  };

  const nextSteps = summary.nextSteps?.length
    ? summary.nextSteps
    : [
        'Review the accepted profile changes.',
        'Validate them against a broader query set.',
        'Promote the best profile only after a final verification pass.',
      ];

  return (
    <div style={{ marginBottom: 36 }}>
      {/* Title + meta */}
      <div style={{ marginBottom: 20 }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            marginBottom: 8,
            flexWrap: 'wrap',
          }}
        >
          <h1
            style={{
              fontFamily: 'Inter, sans-serif',
              fontWeight: 700,
              fontSize: 28,
              color: '#EEF3FF',
              letterSpacing: '-0.02em',
              margin: 0,
            }}
          >
            ElastiTune Optimization Report
          </h1>
          <span
            style={{
              fontFamily: 'Inter, sans-serif',
              fontSize: 11,
              fontWeight: 600,
              padding: '3px 10px',
              borderRadius: 20,
              background:
                mode === 'demo'
                  ? 'rgba(251,191,36,0.12)'
                  : 'rgba(74,222,128,0.1)',
              color: mode === 'demo' ? '#FBBF24' : '#4ADE80',
              border: `1px solid ${mode === 'demo' ? 'rgba(251,191,36,0.25)' : 'rgba(74,222,128,0.2)'}`,
            }}
          >
            {mode.toUpperCase()}
          </span>
        </div>

        <p
          style={{
            fontFamily: 'Inter, sans-serif',
            fontSize: 12,
            color: '#6B7480',
            margin: 0,
          }}
        >
          Generated {generatedDate} · Run ID:{' '}
          <span
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              color: '#9AA4B2',
            }}
          >
            {report.runId}
          </span>{' '}
          · Elapsed {formatDuration(summary.durationSeconds)}
          {summary.modelId && (
            <>
              {' · '}
              <span
                style={{
                  fontFamily: 'Inter, sans-serif',
                  fontSize: 11,
                  color: '#9AA4B2',
                }}
              >
                Model:{' '}
              </span>
              <span
                style={{
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: 11,
                  color: '#7CE7FF',
                }}
              >
                {summary.modelId}
              </span>
            </>
          )}
        </p>
      </div>

      {/* Headline */}
      <div
        style={{
          padding: '16px 20px',
          background: 'rgba(77,163,255,0.05)',
          border: `1px solid rgba(77,163,255,0.15)`,
          borderRadius: 8,
          marginBottom: 24,
        }}
      >
        <p
          style={{
            fontFamily: 'Inter, sans-serif',
            fontSize: 15,
            color: '#C5CDD8',
            lineHeight: 1.6,
            margin: 0,
          }}
        >
          {summary.headline}
        </p>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1.2fr 0.8fr',
          gap: 14,
          marginBottom: 24,
        }}
      >
        <div
          style={{
            background: 'rgba(255,255,255,0.025)',
            border: `1px solid ${PANEL_BORDER}`,
            borderRadius: 10,
            padding: '16px 18px',
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
            What happened
          </div>
          <div
            style={{
              fontFamily: 'Inter, sans-serif',
              fontSize: 13,
              color: '#C5CDD8',
              lineHeight: 1.6,
            }}
          >
            {summary.overview ?? summary.headline}
          </div>
        </div>

        <div
          style={{
            background: 'rgba(255,255,255,0.025)',
            border: `1px solid ${PANEL_BORDER}`,
            borderRadius: 10,
            padding: '16px 18px',
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
            Recommended next steps
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {nextSteps.slice(0, 3).map((step, index) => (
              <div
                key={`${index}-${step}`}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '18px 1fr',
                  gap: 8,
                  alignItems: 'start',
                }}
              >
                <div
                  style={{
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: 11,
                    color: ACCENT_BLUE,
                    marginTop: 1,
                  }}
                >
                  {index + 1}.
                </div>
                <div
                  style={{
                    fontFamily: 'Inter, sans-serif',
                    fontSize: 12,
                    color: '#C5CDD8',
                    lineHeight: 1.5,
                  }}
                >
                  {step}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Metric cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
          gap: 14,
        }}
      >
        <MetricCard
          label={isContinuation ? "Original Baseline" : "Baseline nDCG@10"}
          value={formatScore(summary.baselineScore)}
          accent="#9AA4B2"
        />
        <MetricCard
          label="Best nDCG@10"
          value={formatScore(summary.bestScore)}
          accent={ACCENT_BLUE}
        />
        <MetricCard
          label={isContinuation ? "Cumulative Gain" : "Improvement"}
          value={formatPercent(summary.improvementPct)}
          accent={improvementPositive ? '#4ADE80' : '#FB7185'}
        />
        <MetricCard
          label={isContinuation ? "Total Experiments" : "Experiments"}
          value={String(displayExperiments)}
          sub={`${displayKept} kept${isContinuation ? ' (cumulative)' : ''}`}
        />
        {summary.projectedMonthlySavingsUsd != null &&
          summary.projectedMonthlySavingsUsd > 0 && (
            <MetricCard
              label="Monthly Savings"
              value={formatDollars(summary.projectedMonthlySavingsUsd)}
              sub="projected"
              accent="#4ADE80"
            />
          )}
      </div>
    </div>
  );
}
