import React, { useMemo } from 'react';
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Scatter, Tooltip, XAxis, YAxis } from 'recharts';
import type { ReportPayload } from '@/types/contracts';
import { PANEL_BORDER } from '@/lib/theme';

interface ImprovementGraphProps {
  report: ReportPayload;
}

export default function ImprovementGraph({ report }: ImprovementGraphProps) {
  const chartData = useMemo(() => {
    const rows: Array<{
      experiment: number;
      bestScore: number;
      keptScore: number | null;
      revertedScore: number | null;
    }> = [
      {
        experiment: 0,
        bestScore: report.summary.baselineScore,
        keptScore: null,
        revertedScore: null,
      },
    ];
    let runningBest = report.summary.baselineScore;
    for (const experiment of report.experiments) {
      if (experiment.decision === 'kept') {
        runningBest = experiment.candidateScore;
      }
      rows.push({
        experiment: experiment.experimentId,
        bestScore: runningBest,
        keptScore: experiment.decision === 'kept' ? experiment.candidateScore : null,
        revertedScore: experiment.decision === 'reverted' ? experiment.candidateScore : null,
      });
    }
    return rows;
  }, [report]);

  if (chartData.length <= 1) {
    return null;
  }

  return (
    <div
      style={{
        marginBottom: 28,
        background: 'rgba(255,255,255,0.025)',
        border: `1px solid ${PANEL_BORDER}`,
        borderRadius: 10,
        padding: '16px 18px 12px',
      }}
    >
      <div
        style={{
          fontFamily: 'Inter, sans-serif',
          fontSize: 16,
          fontWeight: 600,
          color: '#EEF3FF',
          marginBottom: 4,
        }}
      >
        Improvement curve
      </div>
      <div
        style={{
          fontFamily: 'Inter, sans-serif',
          fontSize: 12,
          color: '#6B7480',
          lineHeight: 1.5,
          marginBottom: 14,
        }}
      >
        The stepped line shows the best nDCG@10 found so far. Green markers were kept; gray markers were tested and reverted.
      </div>

      <div style={{ width: '100%', height: 260 }}>
        <ResponsiveContainer>
          <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 8, left: 0 }}>
            <CartesianGrid stroke="rgba(255,255,255,0.06)" strokeDasharray="3 3" />
            <XAxis
              dataKey="experiment"
              stroke="#6B7480"
              tick={{ fill: '#6B7480', fontSize: 10 }}
              tickLine={false}
              axisLine={{ stroke: 'rgba(255,255,255,0.08)' }}
            />
            <YAxis
              domain={[0, 1]}
              stroke="#6B7480"
              tick={{ fill: '#6B7480', fontSize: 10 }}
              tickLine={false}
              axisLine={{ stroke: 'rgba(255,255,255,0.08)' }}
            />
            <Tooltip
              contentStyle={{
                background: '#0B0F15',
                border: `1px solid ${PANEL_BORDER}`,
                borderRadius: 8,
                color: '#EEF3FF',
              }}
              labelStyle={{ color: '#EEF3FF' }}
            />
            <ReferenceLine
              y={report.summary.baselineScore}
              stroke="#6B7480"
              strokeDasharray="4 4"
              label={{ value: 'baseline', position: 'insideTopRight', fill: '#6B7480', fontSize: 10 }}
            />
            <Line
              type="stepAfter"
              dataKey="bestScore"
              stroke="#4ADE80"
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
            <Scatter data={chartData} dataKey="keptScore" fill="#4ADE80" />
            <Scatter data={chartData} dataKey="revertedScore" fill="#6B7480" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
