import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
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

export default function RunHistory() {
  const navigate = useNavigate();
  const toast = useToast();
  const { setConnection, setRunId } = useAppStore();
  const [runs, setRuns] = useState<SearchRunListItem[]>([]);
  const [loadingRunId, setLoadingRunId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.listRuns({ limit: 8, completedOnly: true })
      .then(({ runs: history }) => {
        if (!cancelled) {
          setRuns(history);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setRuns([]);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const groupedRuns = useMemo(() => {
    const seen = new Set<string>();
    return runs.filter((run) => {
      const key = run.index_name ?? run.run_id;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }, [runs]);

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
      toast.info('Continuing from saved best profile…');
      navigate(`/run/${started.runId}`);
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to continue saved run.');
    } finally {
      setLoadingRunId(null);
    }
  };

  if (groupedRuns.length === 0) {
    return null;
  }

  return (
    <div
      style={{
        marginTop: 18,
        background: 'rgba(10,14,20,0.62)',
        border: `1px solid ${PANEL_BORDER}`,
        borderRadius: 12,
        padding: '18px 18px 14px',
      }}
    >
      <div
        style={{
          fontFamily: 'Inter, sans-serif',
          fontSize: 14,
          fontWeight: 600,
          color: '#EEF3FF',
          marginBottom: 4,
        }}
      >
        Recent optimization runs
      </div>
      <div
        style={{
          fontFamily: 'Inter, sans-serif',
          fontSize: 11,
          color: '#6B7480',
          lineHeight: 1.45,
          marginBottom: 14,
        }}
      >
        Jump back into a saved benchmark or open the report without reconnecting everything by hand.
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {groupedRuns.map((run) => (
          <div
            key={run.run_id}
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr auto',
              gap: 10,
              padding: '12px 12px',
              borderRadius: 10,
              border: `1px solid ${PANEL_BORDER}`,
              background: 'rgba(255,255,255,0.02)',
            }}
          >
            <div>
              <div
                style={{
                  fontFamily: 'Inter, sans-serif',
                  fontSize: 12,
                  fontWeight: 600,
                  color: '#EEF3FF',
                  marginBottom: 3,
                }}
              >
                {run.index_name ?? 'Saved run'}
              </div>
              <div
                style={{
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: 10,
                  color: run.improvement_pct >= 0 ? '#4ADE80' : '#FB7185',
                  marginBottom: 4,
                }}
              >
                {run.improvement_pct >= 0 ? '+' : ''}
                {run.improvement_pct.toFixed(1)}% · {run.experiments_run} exp · {formatRelativeTime(run.completed_at ?? run.updated_at)}
              </div>
              <div
                style={{
                  fontFamily: 'Inter, sans-serif',
                  fontSize: 10,
                  color: '#6B7480',
                }}
              >
                {run.baseline_score.toFixed(3)} → {run.best_score.toFixed(3)}
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <button
                type="button"
                onClick={() => navigate(`/report/${run.run_id}`)}
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
                View Report
              </button>
              <button
                type="button"
                onClick={() => handleContinue(run)}
                disabled={loadingRunId === run.run_id}
                style={{
                  padding: '8px 10px',
                  borderRadius: 8,
                  border: 'none',
                  background: 'linear-gradient(135deg, #22C55E 0%, #16A34A 100%)',
                  color: '#fff',
                  fontFamily: 'Inter, sans-serif',
                  fontSize: 11,
                  fontWeight: 600,
                  cursor: loadingRunId === run.run_id ? 'not-allowed' : 'pointer',
                  opacity: loadingRunId === run.run_id ? 0.7 : 1,
                }}
              >
                {loadingRunId === run.run_id ? 'Starting…' : 'Continue'}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
