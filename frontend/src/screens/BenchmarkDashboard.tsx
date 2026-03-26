import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '@/lib/api';
import type { ReportPayload, SearchRunListItem } from '@/types/contracts';
import { PANEL_BORDER } from '@/lib/theme';

interface BenchmarkCardData {
  run: SearchRunListItem;
  report?: ReportPayload;
}

function formatRelativeDate(value?: string | null): string {
  if (!value) return 'unknown';
  return new Date(value).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' });
}

export default function BenchmarkDashboard() {
  const navigate = useNavigate();
  const [runs, setRuns] = useState<SearchRunListItem[]>([]);
  const [reports, setReports] = useState<Record<string, ReportPayload>>({});

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const { runs: history } = await api.listRuns({ limit: 100, completedOnly: true });
      if (cancelled) return;
      setRuns(history);

      const grouped = new Map<string, SearchRunListItem>();
      for (const run of history) {
        const key = run.index_name ?? run.run_id;
        if (!grouped.has(key)) {
          grouped.set(key, run);
        }
      }
      const reportEntries = await Promise.all(
        Array.from(grouped.values()).map(async (run) => {
          try {
            return [run.run_id, await api.getReport(run.run_id)] as const;
          } catch {
            return null;
          }
        })
      );
      if (!cancelled) {
        setReports(
          Object.fromEntries(reportEntries.filter((entry): entry is readonly [string, ReportPayload] => Boolean(entry)))
        );
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  const cards = useMemo<BenchmarkCardData[]>(() => {
    const grouped = new Map<string, SearchRunListItem>();
    for (const run of runs) {
      const key = run.index_name ?? run.run_id;
      if (!grouped.has(key)) {
        grouped.set(key, run);
      }
    }
    return Array.from(grouped.values()).map((run) => ({
      run,
      report: reports[run.run_id],
    }));
  }, [reports, runs]);

  return (
    <div
      style={{
        minHeight: '100vh',
        background: '#05070B',
        color: '#EEF3FF',
        padding: '36px 32px 64px',
      }}
    >
      <div style={{ maxWidth: 1180, margin: '0 auto' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, marginBottom: 26 }}>
          <div>
            <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: 30, marginBottom: 6 }}>
              Benchmark dashboard
            </div>
            <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#9AA4B2', lineHeight: 1.6 }}>
              Review the best saved run for each benchmark, jump into the latest report, and compare measurable lift across systems.
            </div>
          </div>
          <Link
            to="/"
            style={{
              fontFamily: 'Inter, sans-serif',
              fontSize: 12,
              fontWeight: 600,
              color: '#7CE7FF',
              textDecoration: 'none',
            }}
          >
            Back to home
          </Link>
        </div>

        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
            gap: 16,
          }}
        >
          {cards.map(({ run, report }) => (
            <button
              key={run.run_id}
              type="button"
              onClick={() => navigate(`/report/${run.run_id}`)}
              style={{
                textAlign: 'left',
                padding: '18px',
                borderRadius: 12,
                border: `1px solid ${PANEL_BORDER}`,
                background: 'rgba(255,255,255,0.025)',
                cursor: 'pointer',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, marginBottom: 10 }}>
                <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 15, fontWeight: 700, color: '#EEF3FF' }}>
                  {run.index_name ?? 'Saved run'}
                </div>
                <div
                  style={{
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: 11,
                    fontWeight: 700,
                    color: run.improvement_pct >= 0 ? '#4ADE80' : '#FB7185',
                  }}
                >
                  {run.improvement_pct >= 0 ? '+' : ''}
                  {run.improvement_pct.toFixed(1)}%
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 12 }}>
                <div>
                  <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 10, color: '#6B7480', marginBottom: 2 }}>
                    Docs
                  </div>
                  <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 14, color: '#EEF3FF' }}>
                    {report?.connection.docCount?.toLocaleString() ?? '—'}
                  </div>
                </div>
                <div>
                  <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 10, color: '#6B7480', marginBottom: 2 }}>
                    Best score
                  </div>
                  <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 14, color: '#7CE7FF' }}>
                    {run.best_score.toFixed(3)}
                  </div>
                </div>
              </div>

              <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 11, color: '#9AA4B2', lineHeight: 1.5 }}>
                {run.experiments_run} experiments · last run {formatRelativeDate(run.completed_at ?? run.updated_at)}
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
