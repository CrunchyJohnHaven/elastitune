import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Printer, Copy, ArrowLeft, Loader2, Download, RefreshCw, RotateCcw } from 'lucide-react';
import { useAppStore } from '@/store/useAppStore';
import { useToast } from '@/components/ui/ToastProvider';
import { api } from '@/lib/api';
import type { ReportPayload } from '@/types/contracts';
import ExecutiveSummary from '@/components/report/ExecutiveSummary';
import ImprovementGraph from '@/components/report/ImprovementGraph';
import MitreCoverageHeatmap from '@/components/report/MitreCoverageHeatmap';
import SearchProfileDiff from '@/components/report/SearchProfileDiff';
import QueryBreakdown from '@/components/report/QueryBreakdown';
import PersonaImpactTable from '@/components/report/PersonaImpactTable';
import CompressionSummaryComp from '@/components/report/CompressionSummary';
import ExperimentTable from '@/components/report/ExperimentTable';
import { PANEL_BORDER, ACCENT_BLUE } from '@/lib/theme';
import { buildShareableReportHtml } from '@/lib/reportExport';

export default function ReportScreen() {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();
  const { report: storeReport, setReport, connectionId, setConnection, setRunId } = useAppStore();
  const toast = useToast();

  const [report, setLocalReport] = useState<ReportPayload | null>(storeReport);
  const [loading, setLoading] = useState(!storeReport);
  const [error, setError] = useState<string | null>(null);
  const [profileCopied, setProfileCopied] = useState(false);
  const [continuing, setContinuing] = useState(false);
  const [runChain, setRunChain] = useState<ReportPayload[]>([]);
  const [shareCopied, setShareCopied] = useState(false);
  const [queryCopied, setQueryCopied] = useState(false);

  const canReconnectFromReport = Boolean(report?.connectionConfig);

  // Fetch report if not already in store
  useEffect(() => {
    if (storeReport) {
      setLocalReport(storeReport);
      setLoading(false);
      return;
    }

    if (!runId) return;

    setLoading(true);
    api
      .getReport(runId)
      .then(r => {
        setReport(r);
        setLocalReport(r);
        setLoading(false);
      })
      .catch(err => {
        setError(err instanceof Error ? err.message : 'Failed to load report');
        setLoading(false);
      });
  }, [runId, storeReport, setReport]);

  useEffect(() => {
    let cancelled = false;

    async function loadChain() {
      if (!report?.previousRunId) {
        setRunChain([]);
        return;
      }

      const chain: ReportPayload[] = [];
      let nextRunId: string | null | undefined = report.previousRunId;
      let depth = 0;
      while (nextRunId && depth < 10) {
        try {
          const prior = await api.getReport(nextRunId);
          chain.push(prior);
          nextRunId = prior.previousRunId;
          depth += 1;
        } catch {
          break;
        }
      }
      if (!cancelled) {
        setRunChain(chain);
      }
    }

    void loadChain();
    return () => {
      cancelled = true;
    };
  }, [report?.previousRunId]);

  const handleCopyProfile = () => {
    if (!report) return;
    navigator.clipboard.writeText(
      JSON.stringify(report.searchProfileAfter, null, 2)
    );
    setProfileCopied(true);
    setTimeout(() => setProfileCopied(false), 2000);
  };

  const handleDownloadReport = () => {
    if (!report) return;
    const blob = new Blob([JSON.stringify(report, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `elastitune-report-${report.runId}.json`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  };

  const handleShareReport = async () => {
    if (!report) return;
    const html = buildShareableReportHtml(report);
    try {
      await navigator.clipboard.writeText(html);
      setShareCopied(true);
      setTimeout(() => setShareCopied(false), 2000);
      toast.success('Shareable report HTML copied to clipboard.');
    } catch {
      const blob = new Blob([html], { type: 'text/html' });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `elastitune-report-${report.runId}.html`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    }
  };

  const handleExportPdf = () => {
    if (!report) return;
    const html = buildShareableReportHtml(report);
    const printWindow = window.open('', '_blank', 'width=1200,height=900');
    if (!printWindow) {
      toast.error('Popup blocked. Allow popups to export this report.');
      return;
    }
    printWindow.document.open();
    printWindow.document.write(html);
    printWindow.document.close();
    printWindow.focus();
    setTimeout(() => {
      printWindow.print();
    }, 250);
  };

  const handleCopyEsQuery = async () => {
    if (!report || report.queryBreakdown.length === 0) return;
    const queryId = report.queryBreakdown[0].queryId;
    try {
      const preview = await api.previewQuery(report.runId, queryId);
      const payload = preview.optimizedQueryDsl ?? {
        size: 5,
        query: {
          multi_match: {
            query: preview.query,
            fields: report.searchProfileAfter.lexicalFields.map((field) => `${field.field}^${field.boost}`),
            type: report.searchProfileAfter.multiMatchType,
            minimum_should_match: report.searchProfileAfter.minimumShouldMatch,
          },
        },
      };
      await navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
      setQueryCopied(true);
      setTimeout(() => setQueryCopied(false), 2000);
      toast.success('Optimized Elasticsearch query copied to clipboard.');
    } catch {
      toast.error('Failed to build the optimized Elasticsearch query.');
    }
  };

  const handleContinueOptimization = async () => {
    if (!report || !runId) {
      toast.error('Report context is missing. Please return home and reconnect.');
      return;
    }
    setContinuing(true);
    try {
      const resp = await startRunWithReconnect({
        durationMinutes: 30,
        maxExperiments: 200,
        personaCount: 36,
        autoStopOnPlateau: true,
        previousRunId: runId,
      });
      setRunId(resp.runId);
      setReport(null as unknown as ReportPayload);
      toast.info('Continuing optimization from best profile\u2026');
      navigate(`/run/${resp.runId}`);
    } catch (err) {
      toast.error('Failed to continue optimization. Check your connection.');
      console.error('Continue optimization failed:', err);
      setContinuing(false);
    }
  };

  const handleStartFresh = async () => {
    if (!report) {
      toast.error('Report context is missing. Please return home and reconnect.');
      return;
    }
    setContinuing(true);
    try {
      const resp = await startRunWithReconnect({
        durationMinutes: 30,
        maxExperiments: 200,
        personaCount: 36,
        autoStopOnPlateau: true,
      });
      setRunId(resp.runId);
      setReport(null as unknown as ReportPayload);
      toast.info('Starting fresh optimization run\u2026');
      navigate(`/run/${resp.runId}`);
    } catch (err) {
      toast.error('Failed to start fresh run. Check your connection.');
      console.error('Start fresh failed:', err);
      setContinuing(false);
    }
  };

  const reconnectUsingReport = async () => {
    const connectionConfig = report?.connectionConfig;
    if (!connectionConfig) {
      throw new Error('This saved report does not include enough connection details to reconnect automatically.');
    }

    const reconnectResp = await api.connect({
      mode: connectionConfig.mode,
      esUrl: connectionConfig.esUrl ?? undefined,
      apiKey: connectionConfig.apiKey ?? undefined,
      indexName: connectionConfig.indexName ?? undefined,
      uploadedEvalSet: connectionConfig.evalSet?.length ? connectionConfig.evalSet : undefined,
      autoGenerateEval: !connectionConfig.evalSet?.length,
      llm: connectionConfig.llm ?? undefined,
    });
    setConnection(reconnectResp.connectionId, reconnectResp.summary);
    return reconnectResp.connectionId;
  };

  const startRunWithReconnect = async (opts: {
    durationMinutes: number;
    maxExperiments: number;
    personaCount: number;
    autoStopOnPlateau: boolean;
    previousRunId?: string;
  }) => {
    let activeConnectionId = connectionId;

    if (!activeConnectionId) {
      activeConnectionId = await reconnectUsingReport();
    }

    try {
      return await api.startRun(activeConnectionId, opts);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      if (!message.includes('HTTP 404')) {
        throw err;
      }
      const reconnectedId = await reconnectUsingReport();
      return await api.startRun(reconnectedId, opts);
    }
  };

  if (loading) {
    return (
      <div
        style={{
          width: '100vw',
          height: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#05070B',
          flexDirection: 'column',
          gap: 14,
        }}
      >
        <Loader2
          size={28}
          style={{ color: ACCENT_BLUE, animation: 'spin 1s linear infinite' }}
        />
        <span
          style={{
            fontFamily: 'Inter, sans-serif',
            fontSize: 13,
            color: '#6B7480',
          }}
        >
          Loading report…
        </span>
        <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div
        style={{
          width: '100vw',
          height: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: '#05070B',
          flexDirection: 'column',
          gap: 14,
        }}
      >
        <div
          style={{
            fontFamily: 'Inter, sans-serif',
            fontSize: 14,
            color: '#FB7185',
            padding: '14px 20px',
            background: 'rgba(251,113,133,0.06)',
            border: '1px solid rgba(251,113,133,0.2)',
            borderRadius: 8,
          }}
        >
          {error ?? 'Report not found'}
        </div>
        <button
          onClick={() => navigate('/')}
          style={{
            fontFamily: 'Inter, sans-serif',
            fontSize: 12,
            color: ACCENT_BLUE,
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            textDecoration: 'underline',
          }}
        >
          Return home
        </button>
      </div>
    );
  }

  return (
    <>
      {/* Print styles */}
      <style>{`
        @media print {
          .no-print { display: none !important; }
          body { background: #fff !important; color: #000 !important; }
          .report-content { color: #111 !important; }
        }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>

      <div
        style={{
          height: '100vh',
          background: '#05070B',
          color: '#EEF3FF',
          overflowY: 'auto',
          overflowX: 'hidden',
          WebkitOverflowScrolling: 'touch',
        }}
      >
        {/* No-print header bar */}
        <div
          className="no-print"
          style={{
            position: 'sticky',
            top: 0,
            zIndex: 100,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 32px',
            height: 56,
            background: 'rgba(11,15,21,0.96)',
            borderBottom: `1px solid ${PANEL_BORDER}`,
            backdropFilter: 'blur(12px)',
            gap: 16,
          }}
        >
          {/* Left: back + logo */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <Link
              to={runId ? `/run/${runId}` : '/'}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 5,
                fontFamily: 'Inter, sans-serif',
                fontSize: 12,
                color: '#6B7480',
                textDecoration: 'none',
                transition: 'color 0.15s',
              }}
              onMouseEnter={e =>
                ((e.currentTarget as HTMLAnchorElement).style.color = '#EEF3FF')
              }
              onMouseLeave={e =>
                ((e.currentTarget as HTMLAnchorElement).style.color = '#6B7480')
              }
            >
              <ArrowLeft size={13} />
              Back to Run
            </Link>

            <div
              style={{
                width: 1,
                height: 20,
                background: PANEL_BORDER,
              }}
            />

            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 7,
              }}
            >
              <div
                style={{
                  width: 20,
                  height: 20,
                  borderRadius: '50%',
                  background:
                    'radial-gradient(circle, #4DA3FF 0%, rgba(77,163,255,0.3) 60%, transparent 100%)',
                  boxShadow: '0 0 10px rgba(77,163,255,0.5)',
                }}
              />
              <span
                style={{
                  fontFamily: 'Inter, sans-serif',
                  fontWeight: 700,
                  fontSize: 14,
                  color: '#EEF3FF',
                  letterSpacing: '-0.01em',
                }}
              >
                ElastiTune
              </span>
              <span
                style={{
                  fontFamily: 'Inter, sans-serif',
                  fontSize: 12,
                  color: '#6B7480',
                }}
              >
                / Report
              </span>
            </div>
          </div>

          {/* Right: actions */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <button
              onClick={handleDownloadReport}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                fontFamily: 'Inter, sans-serif',
                fontWeight: 500,
                fontSize: 12,
                padding: '6px 12px',
                background: 'transparent',
                border: `1px solid ${PANEL_BORDER}`,
                borderRadius: 7,
                color: '#9AA4B2',
                cursor: 'pointer',
                transition: 'color 0.2s, border-color 0.2s',
              }}
              onMouseEnter={e => {
                (e.currentTarget as HTMLButtonElement).style.borderColor =
                  'rgba(255,255,255,0.2)';
                (e.currentTarget as HTMLButtonElement).style.color = '#EEF3FF';
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLButtonElement).style.borderColor =
                  PANEL_BORDER;
                (e.currentTarget as HTMLButtonElement).style.color = '#9AA4B2';
              }}
            >
              <Download size={12} />
              Download JSON
            </button>

            <button
              onClick={handleShareReport}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                fontFamily: 'Inter, sans-serif',
                fontWeight: 500,
                fontSize: 12,
                padding: '6px 12px',
                background: 'transparent',
                border: `1px solid ${PANEL_BORDER}`,
                borderRadius: 7,
                color: shareCopied ? '#4ADE80' : '#9AA4B2',
                cursor: 'pointer',
                transition: 'color 0.2s, border-color 0.2s',
              }}
            >
              <Copy size={12} />
              {shareCopied ? 'HTML Copied' : 'Share Report'}
            </button>

            <button
              onClick={() => {
                void handleCopyEsQuery();
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                fontFamily: 'Inter, sans-serif',
                fontWeight: 500,
                fontSize: 12,
                padding: '6px 12px',
                background: 'transparent',
                border: `1px solid ${PANEL_BORDER}`,
                borderRadius: 7,
                color: queryCopied ? '#4ADE80' : '#9AA4B2',
                cursor: 'pointer',
              }}
            >
              <Copy size={12} />
              {queryCopied ? 'ES Query Copied' : 'Copy ES Query'}
            </button>

            <button
              onClick={handleCopyProfile}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                fontFamily: 'Inter, sans-serif',
                fontWeight: 500,
                fontSize: 12,
                padding: '6px 12px',
                background: 'transparent',
                border: `1px solid ${PANEL_BORDER}`,
                borderRadius: 7,
                color: profileCopied ? '#4ADE80' : '#9AA4B2',
                cursor: 'pointer',
                transition: 'color 0.2s, border-color 0.2s',
              }}
              onMouseEnter={e => {
                (e.currentTarget as HTMLButtonElement).style.borderColor =
                  'rgba(255,255,255,0.2)';
                (e.currentTarget as HTMLButtonElement).style.color = '#EEF3FF';
              }}
              onMouseLeave={e => {
                (e.currentTarget as HTMLButtonElement).style.borderColor =
                  PANEL_BORDER;
                (e.currentTarget as HTMLButtonElement).style.color = profileCopied
                  ? '#4ADE80'
                  : '#9AA4B2';
              }}
            >
              <Copy size={12} />
              {profileCopied ? 'Copied!' : 'Copy Search Profile'}
            </button>

            <button
              onClick={handleExportPdf}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                fontFamily: 'Inter, sans-serif',
                fontWeight: 600,
                fontSize: 12,
                padding: '6px 14px',
                background: 'linear-gradient(135deg, #4DA3FF, #3A8FFF)',
                border: 'none',
                borderRadius: 7,
                color: '#fff',
                cursor: 'pointer',
                boxShadow: '0 0 14px rgba(77,163,255,0.3)',
              }}
            >
              <Printer size={12} />
              Export PDF
            </button>
          </div>
        </div>

        {/* Report content */}
        <div
          className="report-content"
          style={{
            maxWidth: 860,
            margin: '0 auto',
            padding: '40px 32px 80px',
          }}
        >
          {/* Executive Summary */}
          <ExecutiveSummary report={report} />
          <ImprovementGraph report={report} />
          <MitreCoverageHeatmap report={report} />

          {/* Continue / Start Fresh buttons */}
          <div
            className="no-print"
            style={{
              display: 'flex',
              gap: 10,
              marginTop: 20,
              marginBottom: 8,
            }}
          >
            <button
              onClick={handleContinueOptimization}
              disabled={continuing || !canReconnectFromReport}
              style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 7,
                padding: '12px 16px',
                background: continuing
                  ? 'rgba(74,222,128,0.2)'
                  : 'linear-gradient(135deg, #22C55E 0%, #16A34A 100%)',
                color: '#fff',
                border: 'none',
                borderRadius: 8,
                fontFamily: 'Inter, sans-serif',
                fontWeight: 600,
                fontSize: 13,
                cursor: continuing ? 'not-allowed' : 'pointer',
                boxShadow: continuing ? 'none' : '0 0 20px rgba(34,197,94,0.3)',
                transition: 'box-shadow 0.2s, transform 0.1s',
                opacity: continuing || !canReconnectFromReport ? 0.6 : 1,
              }}
              onMouseEnter={e => {
                if (!continuing && canReconnectFromReport)
                  (e.currentTarget as HTMLButtonElement).style.boxShadow =
                    '0 0 32px rgba(34,197,94,0.5)';
              }}
              onMouseLeave={e => {
                if (!continuing && canReconnectFromReport)
                  (e.currentTarget as HTMLButtonElement).style.boxShadow =
                    '0 0 20px rgba(34,197,94,0.3)';
              }}
            >
              <RefreshCw size={14} />
              {continuing ? 'Starting\u2026' : 'Continue Optimization'}
            </button>

            <button
              onClick={handleStartFresh}
              disabled={continuing || !canReconnectFromReport}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 6,
                padding: '12px 16px',
                background: 'transparent',
                color: '#9AA4B2',
                border: `1px solid ${PANEL_BORDER}`,
                borderRadius: 8,
                fontFamily: 'Inter, sans-serif',
                fontWeight: 500,
                fontSize: 12,
                cursor: continuing ? 'not-allowed' : 'pointer',
                transition: 'color 0.15s, border-color 0.15s',
                opacity: continuing || !canReconnectFromReport ? 0.5 : 1,
              }}
              onMouseEnter={e => {
                if (!continuing && canReconnectFromReport) {
                  (e.currentTarget as HTMLButtonElement).style.color = '#EEF3FF';
                  (e.currentTarget as HTMLButtonElement).style.borderColor = 'rgba(255,255,255,0.2)';
                }
              }}
              onMouseLeave={e => {
                if (!continuing && canReconnectFromReport) {
                  (e.currentTarget as HTMLButtonElement).style.color = '#9AA4B2';
                  (e.currentTarget as HTMLButtonElement).style.borderColor = PANEL_BORDER;
                }
              }}
            >
              <RotateCcw size={12} />
              Start Fresh
            </button>
          </div>

          {!canReconnectFromReport && (
            <div
              className="no-print"
              style={{
                fontFamily: 'Inter, sans-serif',
                fontSize: 11,
                color: '#6B7480',
                marginBottom: 12,
                fontStyle: 'italic',
              }}
            >
              This saved report does not include reconnect details. <Link to="/" style={{ color: ACCENT_BLUE, textDecoration: 'none' }}>Return home</Link> to start a new run.
            </div>
          )}

          {report.previousRunId && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 10,
                fontFamily: 'Inter, sans-serif',
                fontSize: 11,
                color: '#4DA3FF',
                marginBottom: 12,
                padding: '8px 12px',
                background: 'rgba(77,163,255,0.06)',
                border: '1px solid rgba(77,163,255,0.15)',
                borderRadius: 7,
              }}
            >
              <span>
                This run continued from a previous optimization (Run {report.previousRunId.slice(0, 8)}\u2026).
              </span>
              <Link
                to={`/compare/${report.previousRunId}/${report.runId}`}
                style={{
                  color: '#7CE7FF',
                  textDecoration: 'none',
                  fontWeight: 600,
                  whiteSpace: 'nowrap',
                }}
              >
                Compare runs
              </Link>
            </div>
          )}

          {report.previousRunId && runChain.length > 0 && (
            <div
              style={{
                marginBottom: 16,
                padding: '12px 14px',
                background: 'rgba(34,197,94,0.06)',
                border: '1px solid rgba(34,197,94,0.16)',
                borderRadius: 8,
              }}
            >
              <div
                style={{
                  fontFamily: 'Inter, sans-serif',
                  fontSize: 12,
                  fontWeight: 600,
                  color: '#EEF3FF',
                  marginBottom: 5,
                }}
              >
                Cumulative improvement across the run chain
              </div>
              <div
                style={{
                  fontFamily: 'Inter, sans-serif',
                  fontSize: 11,
                  color: '#9AA4B2',
                  lineHeight: 1.5,
                }}
              >
                Original baseline: {runChain[runChain.length - 1].summary.baselineScore.toFixed(3)} · Previous best: {runChain[0].summary.bestScore.toFixed(3)} · New best: {report.summary.bestScore.toFixed(3)} · Total lift:{' '}
                {`${((((report.summary.bestScore - runChain[runChain.length - 1].summary.baselineScore) / Math.max(runChain[runChain.length - 1].summary.baselineScore, 0.001)) * 100)).toFixed(1)}%`}
              </div>
            </div>
          )}

          {/* Divider */}
          <div
            style={{
              height: 1,
              background: PANEL_BORDER,
              margin: '28px 0',
            }}
          />

          {/* Search Profile Diff */}
          <SearchProfileDiff
            before={report.searchProfileBefore}
            after={report.searchProfileAfter}
            diff={report.diff}
          />

          {/* Per-Query Breakdown */}
          {report.queryBreakdown && report.queryBreakdown.length > 0 && (
            <QueryBreakdown runId={report.runId} rows={report.queryBreakdown} />
          )}

          {/* Kept Experiments */}
          <ExperimentTable
            experiments={report.experiments}
            title="Accepted Experiments"
            filterKept
          />

          {/* Persona Impact */}
          {report.personaImpact.length > 0 && (
            <PersonaImpactTable personaImpact={report.personaImpact} />
          )}

          {/* Compression Summary */}
          <CompressionSummaryComp compression={report.compression} />

          {/* All Experiments */}
          <ExperimentTable
            experiments={report.experiments}
            title="All Experiments"
          />

          {/* Warnings */}
          {report.warnings.length > 0 && (
            <div style={{ marginBottom: 32 }}>
              <h2
                style={{
                  fontFamily: 'Inter, sans-serif',
                  fontWeight: 600,
                  fontSize: 17,
                  color: '#EEF3FF',
                  marginBottom: 12,
                }}
              >
                Warnings
              </h2>
              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 8,
                }}
              >
                {report.warnings.map((w, i) => (
                  <div
                    key={i}
                    style={{
                      padding: '10px 14px',
                      background: 'rgba(251,191,36,0.06)',
                      border: '1px solid rgba(251,191,36,0.2)',
                      borderRadius: 7,
                      fontFamily: 'Inter, sans-serif',
                      fontSize: 12,
                      color: '#FBBF24',
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: 8,
                    }}
                  >
                    <span style={{ flexShrink: 0 }}>⚠</span>
                    {w}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Footer */}
          <div
            style={{
              marginTop: 48,
              paddingTop: 20,
              borderTop: `1px solid ${PANEL_BORDER}`,
              textAlign: 'center',
            }}
          >
            <p
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: 10,
                color: '#4B5563',
                letterSpacing: '0.06em',
              }}
            >
              Generated by ElastiTune · Run {report.runId} ·{' '}
              {new Date(report.generatedAt).toLocaleString()}
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
