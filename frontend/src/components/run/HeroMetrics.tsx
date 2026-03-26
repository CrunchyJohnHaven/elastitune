import React, { memo } from 'react';
import {
  LineChart,
  Line,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import type { HeroMetrics as HeroMetricsType } from '@/types/contracts';
import { formatScore, formatPercent } from '@/lib/format';
import { ACCENT_BLUE, PANEL_BORDER } from '@/lib/theme';

interface HeroMetricsProps {
  metrics: HeroMetricsType;
}

function MetricMini({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={{ textAlign: 'center' }}>
      <div
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 9,
          color: '#6B7480',
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
          marginBottom: 2,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 15,
          fontWeight: 600,
          color: color ?? '#EEF3FF',
        }}
      >
        {value}
      </div>
    </div>
  );
}

function HeroMetrics({ metrics }: HeroMetricsProps) {
  const timeline = metrics.scoreTimeline ?? [];
  const improvementPositive = metrics.improvementPct >= 0;

  const chartData = timeline.map(pt => ({
    t: pt.t,
    score: pt.score,
  }));

  return (
    <div
      style={{
        padding: '10px 12px',
        borderBottom: `1px solid ${PANEL_BORDER}`,
      }}
    >
      {/* Mini stats row */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 8,
          marginBottom: 10,
        }}
      >
        <MetricMini
          label="Current"
          value={formatScore(metrics.currentScore)}
          color={ACCENT_BLUE}
        />
        <MetricMini
          label="Baseline"
          value={formatScore(metrics.baselineScore)}
          color="#6B7480"
        />
        <MetricMini
          label="Gain"
          value={formatPercent(metrics.improvementPct)}
          color={improvementPositive ? '#4ADE80' : '#FB7185'}
        />
      </div>

      {/* Sparkline chart */}
      {chartData.length >= 2 ? (
        <div style={{ height: 44 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: 4 }}>
              <ReferenceLine
                y={metrics.baselineScore}
                stroke="rgba(107,116,128,0.3)"
                strokeDasharray="3 3"
                strokeWidth={1}
              />
              <Line
                type="monotone"
                dataKey="score"
                stroke={ACCENT_BLUE}
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
              />
              <Tooltip
                contentStyle={{
                  background: 'rgba(10,14,20,0.92)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: 6,
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: 10,
                  color: '#EEF3FF',
                  padding: '4px 8px',
                }}
                formatter={(val: number) => [formatScore(val), 'nDCG@10']}
                labelFormatter={() => ''}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div
          style={{
            height: 44,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontFamily: 'Inter, sans-serif',
            fontSize: 10,
            color: '#4B5563',
            fontStyle: 'italic',
          }}
        >
          Score history will appear here
        </div>
      )}

      {/* Best score note */}
      {metrics.bestScore > metrics.baselineScore && (
        <div
          style={{
            marginTop: 5,
            textAlign: 'right',
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 9,
            color: '#4ADE80',
          }}
        >
          Best: {formatScore(metrics.bestScore)}
        </div>
      )}
    </div>
  );
}

export default memo(HeroMetrics);
