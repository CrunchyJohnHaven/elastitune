import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { api } from '@/lib/api';
import type { QueryBreakdownRow, ReportPayload } from '@/types/contracts';
import { PANEL_BORDER, ACCENT_BLUE } from '@/lib/theme';

function MetricTile({
  label,
  left,
  right,
  accent,
}: {
  label: string;
  left: string;
  right: string;
  accent?: string;
}) {
  return (
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
          fontSize: 10,
          fontWeight: 600,
          color: '#6B7480',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          marginBottom: 8,
        }}
      >
        {label}
      </div>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr auto 1fr',
          gap: 10,
          alignItems: 'center',
        }}
      >
        <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 24, color: '#EEF3FF' }}>{left}</div>
        <div style={{ color: '#4B5563' }}>→</div>
        <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 24, color: accent ?? '#4ADE80' }}>{right}</div>
      </div>
    </div>
  );
}

function formatPct(value: number) {
  return `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`;
}

export default function CompareScreen() {
  const { runId1, runId2 } = useParams<{ runId1: string; runId2: string }>();
  const navigate = useNavigate();
  const [leftReport, setLeftReport] = useState<ReportPayload | null>(null);
  const [rightReport, setRightReport] = useState<ReportPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId1 || !runId2) return;
    let cancelled = false;

    Promise.all([api.getReport(runId1), api.getReport(runId2)])
      .then(([left, right]) => {
        if (!cancelled) {
          setLeftReport(left);
          setRightReport(right);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load comparison');
        }
      });

    return () => {
      cancelled = true;
    };
  }, [runId1, runId2]);

  const queryComparison = useMemo(() => {
    if (!leftReport || !rightReport) return [];
    const leftMap = new Map(leftReport.queryBreakdown.map((row) => [row.queryId, row]));
    return rightReport.queryBreakdown
      .map((row) => {
        const left = leftMap.get(row.queryId);
        if (!left) return null;
        return {
          query: row.query,
          before: left.bestScore,
          after: row.bestScore,
          delta: row.bestScore - left.bestScore,
        };
      })
      .filter((row): row is { query: string; before: number; after: number; delta: number } => Boolean(row))
      .sort((a, b) => b.delta - a.delta);
  }, [leftReport, rightReport]);

  if (error) {
    return (
      <div style={{ width: '100vw', height: '100vh', background: '#05070B', color: '#EEF3FF', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <div>{error}</div>
      </div>
    );
  }

  if (!leftReport || !rightReport) {
    return (
      <div style={{ width: '100vw', height: '100vh', background: '#05070B', color: '#EEF3FF', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12 }}>
        <Loader2 size={22} style={{ animation: 'spin 1s linear infinite', color: ACCENT_BLUE }} />
        <span style={{ fontFamily: 'Inter, sans-serif', fontSize: 13 }}>Loading comparison…</span>
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', background: '#05070B', color: '#EEF3FF' }}>
      <div
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 20,
          height: 56,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 28px',
          background: 'rgba(11,15,21,0.96)',
          borderBottom: `1px solid ${PANEL_BORDER}`,
          backdropFilter: 'blur(12px)',
        }}
      >
        <Link
          to={`/report/${runId2}`}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            color: '#9AA4B2',
            textDecoration: 'none',
            fontFamily: 'Inter, sans-serif',
            fontSize: 12,
          }}
        >
          <ArrowLeft size={13} />
          Back to report
        </Link>
        <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, fontWeight: 600 }}>Run Comparison</div>
        <button
          type="button"
          onClick={() => navigate(`/run/${runId2}`)}
          style={{
            padding: '8px 10px',
            borderRadius: 8,
            border: `1px solid ${PANEL_BORDER}`,
            background: 'transparent',
            color: '#9AA4B2',
            fontFamily: 'Inter, sans-serif',
            fontSize: 11,
            cursor: 'pointer',
          }}
        >
          Open current run
        </button>
      </div>

      <div style={{ maxWidth: 1080, margin: '0 auto', padding: '36px 28px 80px' }}>
        <div style={{ marginBottom: 20 }}>
          <h1 style={{ fontFamily: 'Inter, sans-serif', fontSize: 28, margin: 0, marginBottom: 8 }}>Compare optimization runs</h1>
          <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#9AA4B2', lineHeight: 1.55 }}>
            Compare the earlier best profile against the latest continued run to see whether the second pass found real additional lift.
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 14, marginBottom: 24 }}>
          <MetricTile label="Best nDCG@10" left={leftReport.summary.bestScore.toFixed(3)} right={rightReport.summary.bestScore.toFixed(3)} />
          <MetricTile label="Improvement vs baseline" left={formatPct(leftReport.summary.improvementPct)} right={formatPct(rightReport.summary.improvementPct)} accent="#4DA3FF" />
          <MetricTile label="Experiments run" left={String(leftReport.summary.experimentsRun)} right={String(rightReport.summary.experimentsRun)} accent="#FBBF24" />
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 24 }}>
          {[leftReport, rightReport].map((report, index) => (
            <div
              key={report.runId}
              style={{
                background: 'rgba(255,255,255,0.025)',
                border: `1px solid ${PANEL_BORDER}`,
                borderRadius: 10,
                padding: '16px 18px',
              }}
            >
              <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 12, fontWeight: 700, color: '#EEF3FF', marginBottom: 6 }}>
                {index === 0 ? 'Earlier run' : 'Latest run'}
              </div>
              <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#6B7480', marginBottom: 8 }}>
                {report.runId}
              </div>
              <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 12, color: '#C5CDD8', lineHeight: 1.6 }}>
                {report.summary.overview}
              </div>
            </div>
          ))}
        </div>

        <div
          style={{
            background: 'rgba(255,255,255,0.025)',
            border: `1px solid ${PANEL_BORDER}`,
            borderRadius: 10,
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 120px 120px 120px',
              gap: 10,
              padding: '10px 14px',
              background: 'rgba(255,255,255,0.03)',
              borderBottom: `1px solid ${PANEL_BORDER}`,
              fontFamily: 'Inter, sans-serif',
              fontSize: 10,
              fontWeight: 600,
              color: '#6B7480',
              textTransform: 'uppercase',
              letterSpacing: '0.08em',
            }}
          >
            <div>Query</div>
            <div style={{ textAlign: 'right' }}>Earlier</div>
            <div style={{ textAlign: 'right' }}>Latest</div>
            <div style={{ textAlign: 'right' }}>Delta</div>
          </div>

          {queryComparison.map((row) => (
            <div
              key={row.query}
              style={{
                display: 'grid',
                gridTemplateColumns: '1fr 120px 120px 120px',
                gap: 10,
                padding: '10px 14px',
                borderBottom: `1px solid ${PANEL_BORDER}`,
                alignItems: 'center',
              }}
            >
              <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 12, color: '#EEF3FF' }}>{row.query}</div>
              <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, textAlign: 'right', color: '#9AA4B2' }}>{row.before.toFixed(3)}</div>
              <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, textAlign: 'right', color: '#EEF3FF' }}>{row.after.toFixed(3)}</div>
              <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, textAlign: 'right', color: row.delta >= 0 ? '#4ADE80' : '#FB7185' }}>
                {row.delta >= 0 ? '+' : ''}
                {row.delta.toFixed(3)}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
