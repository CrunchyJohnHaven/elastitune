import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { api } from '@/lib/api';
import type { CommitteeExportPayload, CommitteeReport } from '@/types/committee';
import { formatPercent, formatScore } from '@/lib/format';
import { PANEL_BORDER } from '@/lib/theme';
import ErrorBoundary from '@/components/ErrorBoundary';
import { useToast } from '@/components/ui/ToastProvider';
import { useViewportWidth } from '@/hooks/useViewportWidth';
import CommitteeReportNarrative from '@/components/committee/CommitteeReportNarrative';
import CommitteeImplementationGuide from '@/components/committee/CommitteeImplementationGuide';

function sentimentColor(sentiment: string): string {
  switch (sentiment) {
    case 'supportive': return '#4ADE80';
    case 'cautiously_interested': return '#9AE66E';
    case 'neutral': return '#FBBF24';
    case 'skeptical': return '#FB8B5F';
    case 'opposed': return '#FB7185';
    default: return '#9AA4B2';
  }
}

function KpiCard({ label, value, color, sub }: { label: string; value: string; color?: string; sub?: string }) {
  return (
    <div style={{
      padding: '16px 18px',
      borderRadius: 14,
      background: 'rgba(10,14,20,0.76)',
      border: `1px solid ${PANEL_BORDER}`,
    }}>
      <div style={{
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: 9,
        color: '#6B7480',
        letterSpacing: '0.12em',
        textTransform: 'uppercase',
        marginBottom: 8,
      }}>
        {label}
      </div>
      <div style={{
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: 22,
        fontWeight: 700,
        color: color ?? '#EEF3FF',
        lineHeight: 1,
      }}>
        {value}
      </div>
      {sub && (
        <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 10, color: '#6B7480', marginTop: 5 }}>
          {sub}
        </div>
      )}
    </div>
  );
}

function SectionCard({ label }: { label: React.ReactNode }) {
  return (
    <div
      style={{
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: 9,
        color: '#6B7480',
        letterSpacing: '0.14em',
        textTransform: 'uppercase',
        marginBottom: 14,
      }}
    >
      {label}
    </div>
  );
}

function SkeletonBlock({ height = 16, width = '100%' }: { height?: number; width?: number | string }) {
  return (
    <div
      style={{
        height,
        width,
        borderRadius: 8,
        background: 'linear-gradient(90deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.03) 100%)',
        backgroundSize: '220% 100%',
        animation: 'committeeSkeleton 1.2s ease-in-out infinite',
      }}
    />
  );
}

function ReportSkeleton() {
  return (
    <div style={{ minHeight: '100vh', background: '#05070B', color: '#EEF3FF', padding: '0 0 60px' }}>
      <style>{`
        @keyframes committeeSkeleton {
          0% { background-position: 200% 0; }
          100% { background-position: -20% 0; }
        }
      `}</style>
      <div style={{ padding: '20px 36px', borderBottom: `1px solid ${PANEL_BORDER}`, background: 'rgba(10,14,20,0.85)' }}>
        <SkeletonBlock height={22} width={220} />
        <div style={{ marginTop: 10 }}>
          <SkeletonBlock height={12} width={420} />
        </div>
      </div>
      <div style={{ padding: '28px 36px 0' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 12, marginBottom: 24 }}>
          {Array.from({ length: 4 }).map((_, index) => (
            <div key={index} style={{ padding: '16px 18px', borderRadius: 14, background: 'rgba(10,14,20,0.76)', border: `1px solid ${PANEL_BORDER}` }}>
              <SkeletonBlock height={10} width={90} />
              <div style={{ marginTop: 10 }}>
                <SkeletonBlock height={24} width={120} />
              </div>
            </div>
          ))}
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 0.9fr', gap: 18 }}>
          {Array.from({ length: 2 }).map((_, column) => (
            <div key={column} style={{ padding: '16px 18px', borderRadius: 14, background: 'rgba(10,14,20,0.76)', border: `1px solid ${PANEL_BORDER}` }}>
              <SkeletonBlock height={10} width={120} />
              <div style={{ display: 'grid', gap: 10, marginTop: 14 }}>
                {Array.from({ length: 4 }).map((__, card) => (
                  <div key={card} style={{ padding: '12px 14px', borderRadius: 10, background: 'rgba(255,255,255,0.02)', border: `1px solid ${PANEL_BORDER}` }}>
                    <SkeletonBlock height={14} width="60%" />
                    <div style={{ marginTop: 10 }}>
                      <SkeletonBlock height={10} />
                    </div>
                    <div style={{ marginTop: 8 }}>
                      <SkeletonBlock height={10} width="92%" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function CommitteeReportScreen() {
  const { runId } = useParams<{ runId: string }>();
  const toast = useToast();
  const width = useViewportWidth();
  const isNarrow = width < 1120;
  const [report, setReport] = useState<CommitteeReport | null>(null);
  const [exportPayload, setExportPayload] = useState<CommitteeExportPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copyState, setCopyState] = useState<'idle' | 'copied' | 'failed'>('idle');

  useEffect(() => {
    if (!runId) return;
    Promise.all([api.getCommitteeReport(runId), api.getCommitteeExport(runId)])
      .then(([r, p]) => {
        setReport(r);
        setExportPayload(p);
      })
      .catch(err => {
        const message = err instanceof Error ? err.message : 'Failed to load committee report';
        setError(message);
      });
  }, [runId]);

  if (error) {
    return (
      <div style={{ padding: 40, color: '#FB7185', background: '#05070B', minHeight: '100vh', fontFamily: 'Inter, sans-serif' }}>
        {error}
      </div>
    );
  }

  if (!report || !exportPayload) {
    return <ReportSkeleton />;
  }

  const gain = report.summary.improvementPct;
  const gainPositive = gain >= 0;

  const handleDownloadExport = () => {
    const blob = new Blob([JSON.stringify(exportPayload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `${exportPayload.documentName.replace(/\.[^.]+$/, '') || 'committee-export'}-export.json`;
    anchor.click();
    URL.revokeObjectURL(url);
    toast.success('Export JSON downloaded');
  };

  const handleCopyExport = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(exportPayload, null, 2));
      setCopyState('copied');
      toast.success('Export JSON copied');
      window.setTimeout(() => setCopyState('idle'), 1600);
    } catch {
      setCopyState('failed');
      toast.error('Failed to copy export JSON');
    }
  };

  return (
    <ErrorBoundary title="Committee Report Failed">
      <div style={{ minHeight: '100vh', background: '#05070B', color: '#EEF3FF', padding: '0 0 60px' }}>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: 16,
            flexWrap: 'wrap',
            padding: isNarrow ? '16px 20px' : '20px 36px',
            borderBottom: `1px solid ${PANEL_BORDER}`,
            background: 'rgba(10,14,20,0.85)',
            backdropFilter: 'blur(12px)',
            position: 'sticky',
            top: 0,
            zIndex: 50,
          }}
        >
          <div>
            <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: 20 }}>
              Committee Report
            </div>
            <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 12, color: '#9AA4B2', marginTop: 3 }}>
              {report.summary.headline}
            </div>
          </div>
          <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            <button onClick={handleCopyExport} aria-label="Copy committee export JSON" style={actionButtonStyle('neutral')}>
              {copyState === 'copied' ? 'Copied JSON' : copyState === 'failed' ? 'Copy Failed' : 'Copy JSON'}
            </button>
            <button onClick={handleDownloadExport} aria-label="Download committee export JSON" style={actionButtonStyle('accent')}>
              ↓ Export JSON
            </button>
            <Link
              to="/committee/history"
              style={{ color: '#9AA4B2', textDecoration: 'none', fontFamily: 'Inter, sans-serif', fontSize: 12 }}
            >
              History
            </Link>
            <Link
              to={runId ? `/committee/run/${runId}` : '/committee'}
              aria-label="Back to committee run"
              style={{ color: '#9AA4B2', textDecoration: 'none', fontFamily: 'Inter, sans-serif', fontSize: 12 }}
            >
              ← Back to Run
            </Link>
          </div>
        </div>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
          style={{ padding: isNarrow ? '20px 20px 0' : '28px 36px 0' }}
        >
          {report.warnings.length > 0 && (
            <div style={{ marginBottom: 18, padding: '12px 14px', borderRadius: 12, background: 'rgba(251,191,36,0.08)', border: '1px solid rgba(251,191,36,0.18)', color: '#FCD34D', fontFamily: 'Inter, sans-serif', fontSize: 12, lineHeight: 1.5 }}>
              {report.warnings.slice(0, 3).join(' ')}
            </div>
          )}

          <CommitteeReportNarrative report={report} exportPayload={exportPayload} />

          <div style={{ display: 'grid', gridTemplateColumns: isNarrow ? 'repeat(2, minmax(0, 1fr))' : 'repeat(4, minmax(0, 1fr))', gap: 12, marginBottom: 24 }}>
            <KpiCard label="Baseline Score" value={formatScore(report.summary.baselineScore)} color="#9AA4B2" />
            <KpiCard label="Best Score" value={formatScore(report.summary.bestScore)} color="#4DA3FF" />
            <KpiCard label="Gain" value={`${gainPositive ? '+' : ''}${formatPercent(gain)}`} color={gainPositive ? '#4ADE80' : '#FB7185'} />
            <KpiCard label="Rewrites Accepted" value={`${report.summary.acceptedRewrites}/${report.summary.rewritesTested}`} color="#EEF3FF" sub={`${report.summary.rewritesTested - report.summary.acceptedRewrites} reverted`} />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: isNarrow ? 'repeat(2, minmax(0, 1fr))' : 'repeat(3, minmax(0, 1fr))', gap: 12, marginBottom: 24 }}>
            <KpiCard label="Industry" value={String(exportPayload.committeeSummary.industryLabel ?? 'General Enterprise')} />
            <KpiCard label="AI Coverage" value={`${Number(exportPayload.committeeSummary.llmCoveragePct ?? 0).toFixed(0)}%`} />
            <KpiCard label="Scoring Mode" value={String(exportPayload.committeeSummary.evaluationMode ?? report.evaluationMode).replace(/_/g, ' ')} />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: isNarrow ? '1fr' : '1.08fr 0.92fr', gap: 18 }}>
            <div>
              <CommitteeImplementationGuide
                guide={report.implementationGuide}
                sections={exportPayload.sections}
                actionableFeedback={exportPayload.llmHandoff.actionableSectionFeedback}
              />
            </div>

            <div style={{ display: 'grid', gap: 18, alignContent: 'start' }}>
              <div style={{ padding: '16px 18px', borderRadius: 14, background: 'rgba(10,14,20,0.76)', border: `1px solid ${PANEL_BORDER}` }}>
                <SectionCard label="Persona Outcomes" />
                <div style={{ display: 'grid', gap: 8 }}>
                  {(report.personas ?? []).map(persona => {
                    const color = sentimentColor((persona as any).sentiment ?? 'neutral');
                    const score = Math.max(0, Math.min(1, persona.currentScore ?? 0));
                    const pct = Math.max(0, Math.min(100, Math.round(score * 100)));
                    return (
                      <div key={persona.id} style={{ padding: '10px 12px', borderRadius: 10, background: 'rgba(255,255,255,0.025)', borderLeft: `3px solid ${color}` }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8, marginBottom: 5 }}>
                          <div>
                            <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, fontSize: 12, color: '#EEF3FF' }}>
                              {persona.name}
                            </div>
                            <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 10, color: '#9AA4B2' }}>
                              {persona.title ?? 'Committee Persona'}
                            </div>
                          </div>
                          <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 13, color, flexShrink: 0 }}>
                            {formatScore(score)}
                          </div>
                        </div>
                        <div style={{ height: 2, background: 'rgba(255,255,255,0.06)', borderRadius: 1, marginBottom: 5 }}>
                          <div style={{ height: '100%', width: `${pct}%`, background: color, borderRadius: 1 }} />
                        </div>
                        <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 11, color: '#9AA4B2', lineHeight: 1.4 }}>
                          {persona.reactionQuote ?? 'No reaction quote available.'}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div style={{ padding: '16px 18px', borderRadius: 14, background: 'rgba(10,14,20,0.76)', border: `1px solid ${PANEL_BORDER}` }}>
                <SectionCard label={`Rewrite Log (${report.rewrites.length} total)`} />
                <div style={{ display: 'grid', gap: 6 }}>
                  {report.rewrites.slice().reverse().slice(0, 12).map(rewrite => {
                    const kept = rewrite.decision === 'kept';
                    return (
                      <div key={rewrite.experimentId} style={{ padding: '9px 11px', borderRadius: 9, background: kept ? 'rgba(74,222,128,0.03)' : 'rgba(251,113,133,0.02)', borderLeft: `2px solid ${kept ? 'rgba(74,222,128,0.3)' : 'rgba(251,113,133,0.2)'}` }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, marginBottom: 3 }}>
                          <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#6B7480' }}>
                            #{rewrite.experimentId} · §{rewrite.sectionId} · {rewrite.parameterName}
                          </div>
                          <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: kept ? '#4ADE80' : '#FB7185', flexShrink: 0 }}>
                            {kept ? 'KEPT' : 'REVERTED'} · {rewrite.deltaPercent > 0 ? '+' : ''}{formatPercent(rewrite.deltaPercent)}
                          </div>
                        </div>
                        <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 11, color: '#9AA4B2', lineHeight: 1.45 }}>
                          {rewrite.description}
                        </div>
                      </div>
                    );
                  })}
                  {report.rewrites.length > 12 && (
                    <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 11, color: '#4B5563', textAlign: 'center', padding: '6px 0', fontStyle: 'italic' }}>
                      + {report.rewrites.length - 12} more in Export JSON
                    </div>
                  )}
                </div>
              </div>

              <div style={{ padding: '16px 18px', borderRadius: 14, background: 'rgba(10,14,20,0.76)', border: `1px solid ${PANEL_BORDER}` }}>
                <SectionCard label="Export Handoff" />
                <div style={{ display: 'grid', gap: 10 }}>
                  <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 12, color: '#C5CDD8', lineHeight: 1.6 }}>
                    {exportPayload.llmHandoff.task ?? 'Use the export handoff to rewrite the document for the committee.'}
                  </div>

                  {exportPayload.llmHandoff.rewriteGoals && exportPayload.llmHandoff.rewriteGoals.length > 0 && (
                    <div style={{ display: 'grid', gap: 6 }}>
                      <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#6B7480', letterSpacing: '0.14em', textTransform: 'uppercase' }}>
                        Rewrite goals
                      </div>
                      {exportPayload.llmHandoff.rewriteGoals.slice(0, 4).map(goal => (
                        <div key={goal} style={{ padding: '9px 10px', borderRadius: 8, background: 'rgba(77,163,255,0.05)', border: '1px solid rgba(77,163,255,0.12)', fontFamily: 'Inter, sans-serif', fontSize: 11, color: '#D7DEE8', lineHeight: 1.5 }}>
                          {goal}
                        </div>
                      ))}
                    </div>
                  )}

                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 8 }}>
                    <KpiCard label="AI Eval" value={String(exportPayload.committeeSummary.aiEvaluations ?? 0)} />
                    <KpiCard label="Heuristics" value={String(exportPayload.committeeSummary.heuristicEvaluations ?? 0)} />
                    <KpiCard label="LLM Coverage" value={`${Number(exportPayload.committeeSummary.llmCoveragePct ?? 0).toFixed(0)}%`} />
                  </div>

                  {exportPayload.llmHandoff.suggestedPrompt && (
                    <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 11, color: '#9AA4B2', lineHeight: 1.55 }}>
                      Suggested prompt: {exportPayload.llmHandoff.suggestedPrompt}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </ErrorBoundary>
  );
}

function actionButtonStyle(mode: 'neutral' | 'accent'): React.CSSProperties {
  if (mode === 'accent') {
    return {
      padding: '9px 14px',
      borderRadius: 9,
      border: '1px solid rgba(77,163,255,0.25)',
      background: 'rgba(77,163,255,0.08)',
      color: '#4DA3FF',
      cursor: 'pointer',
      fontFamily: 'Inter, sans-serif',
      fontSize: 12,
      fontWeight: 600,
    };
  }
  return {
    padding: '9px 14px',
    borderRadius: 9,
    border: '1px solid rgba(255,255,255,0.10)',
    background: 'rgba(255,255,255,0.03)',
    color: '#EEF3FF',
    cursor: 'pointer',
    fontFamily: 'Inter, sans-serif',
    fontSize: 12,
    fontWeight: 600,
  };
}
