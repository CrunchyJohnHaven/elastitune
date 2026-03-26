import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Printer, Copy, ArrowLeft, Loader2, Download } from 'lucide-react';
import { useAppStore } from '@/store/useAppStore';
import { api } from '@/lib/api';
import type { ReportPayload } from '@/types/contracts';
import ExecutiveSummary from '@/components/report/ExecutiveSummary';
import SearchProfileDiff from '@/components/report/SearchProfileDiff';
import PersonaImpactTable from '@/components/report/PersonaImpactTable';
import CompressionSummaryComp from '@/components/report/CompressionSummary';
import ExperimentTable from '@/components/report/ExperimentTable';
import { PANEL_BORDER, ACCENT_BLUE } from '@/lib/theme';

export default function ReportScreen() {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();
  const { report: storeReport, setReport } = useAppStore();

  const [report, setLocalReport] = useState<ReportPayload | null>(storeReport);
  const [loading, setLoading] = useState(!storeReport);
  const [error, setError] = useState<string | null>(null);
  const [profileCopied, setProfileCopied] = useState(false);

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
              onClick={() => window.print()}
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
