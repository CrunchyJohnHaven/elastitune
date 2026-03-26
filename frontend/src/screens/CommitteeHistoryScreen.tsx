import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '@/lib/api';
import { PANEL_BORDER } from '@/lib/theme';
import type { CommitteeRunListItem } from '@/types/committee';

function formatRelativeTime(value?: string | null): string {
  if (!value) return 'unknown';
  const date = new Date(value);
  const diffMs = Date.now() - date.getTime();
  const diffMinutes = Math.max(0, Math.round(diffMs / 60000));
  if (diffMinutes < 1) return 'just now';
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  const diffHours = Math.round(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  return `${Math.round(diffHours / 24)}d ago`;
}

export default function CommitteeHistoryScreen() {
  const navigate = useNavigate();
  const [runs, setRuns] = useState<CommitteeRunListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [industryFilter, setIndustryFilter] = useState('');
  const [completedOnly, setCompletedOnly] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api.listCommitteeRuns({ limit: 100, completedOnly })
      .then(({ runs: history }) => {
        if (!cancelled) setRuns(history);
      })
      .catch(() => {
        if (!cancelled) setRuns([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [completedOnly]);

  const filteredRuns = useMemo(() => {
    const needle = industryFilter.trim().toLowerCase();
    if (!needle) return runs;
    return runs.filter((run) => run.industry_label.toLowerCase().includes(needle));
  }, [industryFilter, runs]);

  return (
    <div style={{ minHeight: '100vh', background: '#05070B', color: '#EEF3FF', padding: '28px 32px 48px' }}>
      <div style={{ maxWidth: 1120, margin: '0 auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, marginBottom: 20 }}>
          <div>
            <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 30, fontWeight: 700 }}>Committee History</div>
            <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#9AA4B2', marginTop: 8, lineHeight: 1.6 }}>
              Revisit prior committee runs, reopen reports, and compare how different rooms responded to the same story.
            </div>
          </div>
          <Link to="/committee" style={{ padding: '10px 14px', borderRadius: 10, color: '#EEF3FF', textDecoration: 'none', border: `1px solid ${PANEL_BORDER}` }}>
            Back to Committee
          </Link>
        </div>

        <div style={{ display: 'flex', gap: 12, marginBottom: 18, flexWrap: 'wrap' }}>
          <input
            value={industryFilter}
            onChange={(event) => setIndustryFilter(event.target.value)}
            placeholder="Filter by industry"
            style={{
              width: 260,
              padding: '10px 12px',
              borderRadius: 10,
              border: `1px solid ${PANEL_BORDER}`,
              background: 'rgba(10,14,20,0.72)',
              color: '#EEF3FF',
            }}
          />
          <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8, fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#C5CDD8' }}>
            <input type="checkbox" checked={completedOnly} onChange={(event) => setCompletedOnly(event.target.checked)} />
            Completed only
          </label>
        </div>

        <div style={{ display: 'grid', gap: 12 }}>
          {!loading && filteredRuns.length === 0 && (
            <div style={{ padding: '18px 20px', borderRadius: 14, border: `1px solid ${PANEL_BORDER}`, background: 'rgba(10,14,20,0.72)', color: '#9AA4B2' }}>
              No persisted committee runs matched the current filter.
            </div>
          )}
          {filteredRuns.map((run) => (
            <div
              key={run.run_id}
              style={{
                display: 'grid',
                gridTemplateColumns: 'minmax(0, 1fr) auto',
                gap: 18,
                padding: '18px 20px',
                borderRadius: 14,
                border: `1px solid ${PANEL_BORDER}`,
                background: 'rgba(10,14,20,0.72)',
              }}
            >
              <div>
                <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 18, fontWeight: 600, marginBottom: 6 }}>
                  {run.document_name}
                </div>
                <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: run.improvement_pct >= 0 ? '#4ADE80' : '#FB7185', marginBottom: 8 }}>
                  {run.improvement_pct >= 0 ? '+' : ''}
                  {run.improvement_pct.toFixed(1)}% consensus lift
                </div>
                <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap', fontFamily: 'Inter, sans-serif', fontSize: 12, color: '#9AA4B2' }}>
                  <span>{run.industry_label}</span>
                  <span>{run.personas_count} personas</span>
                  <span>{run.accepted_rewrites}/{run.rewrites_tested} kept</span>
                  <span>{formatRelativeTime(run.completed_at ?? run.updated_at)}</span>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  onClick={() => navigate(`/committee/run/${run.run_id}`)}
                  style={{ padding: '10px 12px', borderRadius: 10, border: `1px solid ${PANEL_BORDER}`, background: 'transparent', color: '#EEF3FF', cursor: 'pointer' }}
                >
                  Open Run
                </button>
                <button
                  type="button"
                  onClick={() => navigate(`/committee/report/${run.run_id}`)}
                  style={{ padding: '10px 12px', borderRadius: 10, border: 'none', background: 'linear-gradient(135deg, #4DA3FF 0%, #2563EB 100%)', color: '#fff', cursor: 'pointer' }}
                >
                  View Report
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
