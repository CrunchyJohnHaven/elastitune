import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '@/lib/api';
import { useToast } from '@/components/ui/ToastProvider';
import { useAppStore } from '@/store/useAppStore';
import type { ReportPayload, SearchRunListItem } from '@/types/contracts';
import { PANEL_BORDER } from '@/lib/theme';

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

async function reconnectFromReport(report: ReportPayload) {
  if (!report.connectionConfig) {
    throw new Error('Saved report is missing connection details.');
  }
  if (report.connectionConfig.hasApiKey && !report.connectionConfig.apiKey) {
    throw new Error('Saved report came from a secured cluster. Reconnect from the landing page and enter the Elasticsearch API key again.');
  }
  return api.connect({
    mode: report.connectionConfig.mode,
    esUrl: report.connectionConfig.esUrl ?? undefined,
    apiKey: report.connectionConfig.apiKey ?? undefined,
    indexName: report.connectionConfig.indexName ?? undefined,
    uploadedEvalSet: report.connectionConfig.evalSet?.length
      ? report.connectionConfig.evalSet
      : undefined,
    autoGenerateEval: !report.connectionConfig.evalSet?.length,
    llm: report.connectionConfig.llm ?? undefined,
  });
}

export default function HistoryScreen() {
  const navigate = useNavigate();
  const toast = useToast();
  const { setConnection, setRunId } = useAppStore();
  const [runs, setRuns] = useState<SearchRunListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [indexFilter, setIndexFilter] = useState('');
  const [completedOnly, setCompletedOnly] = useState(true);
  const [loadingRunId, setLoadingRunId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api.listRuns({ limit: 100, completedOnly })
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
    const needle = indexFilter.trim().toLowerCase();
    if (!needle) return runs;
    return runs.filter((run) => (run.index_name ?? '').toLowerCase().includes(needle));
  }, [indexFilter, runs]);

  const handleContinue = async (run: SearchRunListItem) => {
    setLoadingRunId(run.run_id);
    try {
      const report = await api.getReport(run.run_id);
      const reconnected = await reconnectFromReport(report);
      setConnection(reconnected.connectionId, reconnected.summary);
      const started = await api.startRun(reconnected.connectionId, {
        durationMinutes: 30,
        maxExperiments: 200,
        personaCount: 36,
        autoStopOnPlateau: true,
        previousRunId: run.run_id,
      });
      setRunId(started.runId);
      navigate(`/run/${started.runId}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to continue saved run.');
    } finally {
      setLoadingRunId(null);
    }
  };

  return (
    <div style={{ minHeight: '100vh', background: '#05070B', color: '#EEF3FF', padding: '28px 32px 48px' }}>
      <div style={{ maxWidth: 1120, margin: '0 auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, marginBottom: 20 }}>
          <div>
            <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 30, fontWeight: 700 }}>Search Run History</div>
            <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#9AA4B2', marginTop: 8, lineHeight: 1.6 }}>
              Reopen saved reports, compare prior lifts, or continue optimizing from the best preserved profile.
            </div>
          </div>
          <Link to="/" style={{ padding: '10px 14px', borderRadius: 10, color: '#EEF3FF', textDecoration: 'none', border: `1px solid ${PANEL_BORDER}` }}>
            Back to Launch
          </Link>
        </div>

        <div style={{ display: 'flex', gap: 12, marginBottom: 18, flexWrap: 'wrap' }}>
          <input
            value={indexFilter}
            onChange={(event) => setIndexFilter(event.target.value)}
            placeholder="Filter by index"
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
              No persisted search runs matched the current filter.
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
                  {run.index_name ?? 'Saved run'}
                </div>
                <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11, color: run.improvement_pct >= 0 ? '#4ADE80' : '#FB7185', marginBottom: 8 }}>
                  {run.improvement_pct >= 0 ? '+' : ''}
                  {run.improvement_pct.toFixed(1)}% improvement
                </div>
                <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap', fontFamily: 'Inter, sans-serif', fontSize: 12, color: '#9AA4B2' }}>
                  <span>{run.baseline_score.toFixed(3)} → {run.best_score.toFixed(3)}</span>
                  <span>{run.experiments_run} experiments</span>
                  <span>{formatRelativeTime(run.completed_at ?? run.updated_at)}</span>
                  <span>{run.cluster_name ?? 'unknown cluster'}</span>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  onClick={() => navigate(`/report/${run.run_id}`)}
                  style={{ padding: '10px 12px', borderRadius: 10, border: `1px solid ${PANEL_BORDER}`, background: 'transparent', color: '#EEF3FF', cursor: 'pointer' }}
                >
                  View Report
                </button>
                <button
                  type="button"
                  onClick={() => void handleContinue(run)}
                  disabled={loadingRunId === run.run_id}
                  style={{ padding: '10px 12px', borderRadius: 10, border: 'none', background: 'linear-gradient(135deg, #22C55E 0%, #16A34A 100%)', color: '#fff', cursor: 'pointer', opacity: loadingRunId === run.run_id ? 0.7 : 1 }}
                >
                  {loadingRunId === run.run_id ? 'Starting…' : 'Continue'}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
