import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { api } from '@/lib/api';
import type { CommitteeExportPayload, CommitteeReport } from '@/types/committee';
import { formatPercent, formatScore } from '@/lib/format';
import { PANEL_BORDER } from '@/lib/theme';
import ErrorBoundary from '@/components/ErrorBoundary';

/* ────────────────────────────────────────────────────────────────
   Committee Report Screen — polished post-run presentation.
   ──────────────────────────────────────────────────────────────── */

function sentimentColor(sentiment: string): string {
  switch (sentiment) {
    case 'supportive':            return '#4ADE80';
    case 'cautiously_interested': return '#9AE66E';
    case 'neutral':               return '#FBBF24';
    case 'skeptical':             return '#FB8B5F';
    case 'opposed':               return '#FB7185';
    default:                      return '#9AA4B2';
  }
}

function KpiCard({ label, value, color, sub }: { label: string; value: string; color?: string; sub?: string }) {
  return (
    <div style={{
      padding: '16px 18px', borderRadius: 14,
      background: 'rgba(10,14,20,0.76)',
      border: `1px solid ${PANEL_BORDER}`,
    }}>
      <div style={{
        fontFamily: 'JetBrains Mono, monospace', fontSize: 9,
        color: '#6B7480', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 8,
      }}>
        {label}
      </div>
      <div style={{
        fontFamily: 'JetBrains Mono, monospace', fontSize: 22, fontWeight: 700,
        color: color ?? '#EEF3FF', lineHeight: 1,
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
    <div style={{
      fontFamily: 'JetBrains Mono, monospace', fontSize: 9,
      color: '#6B7480', letterSpacing: '0.14em', textTransform: 'uppercase', marginBottom: 14,
    }}>
      {label}
    </div>
  );
}

export default function CommitteeReportScreen() {
  const { runId } = useParams<{ runId: string }>();
  const [report, setReport]               = useState<CommitteeReport | null>(null);
  const [exportPayload, setExportPayload] = useState<CommitteeExportPayload | null>(null);
  const [error, setError]                 = useState<string | null>(null);
  const [copyState, setCopyState]         = useState<'idle' | 'copied' | 'failed'>('idle');

  useEffect(() => {
    if (!runId) return;
    Promise.all([api.getCommitteeReport(runId), api.getCommitteeExport(runId)])
      .then(([r, p]) => { setReport(r); setExportPayload(p); })
      .catch(err => setError(err instanceof Error ? err.message : 'Failed to load committee report'));
  }, [runId]);

  if (error) return (
    <div style={{ padding: 40, color: '#FB7185', background: '#05070B', minHeight: '100vh', fontFamily: 'Inter, sans-serif' }}>
      {error}
    </div>
  );

  if (!report || !exportPayload) return (
    <div style={{ padding: 40, color: '#9AA4B2', background: '#05070B', minHeight: '100vh', fontFamily: 'Inter, sans-serif' }}>
      Loading committee report…
    </div>
  );

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
  };

  const handleCopyExport = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(exportPayload, null, 2));
      setCopyState('copied');
      window.setTimeout(() => setCopyState('idle'), 1600);
    } catch {
      setCopyState('failed');
    }
  };

  return (
    <ErrorBoundary title="Committee Report Failed">
    <div style={{ minHeight: '100vh', background: '#05070B', color: '#EEF3FF', padding: '0 0 60px' }}>

      {/* ── Header bar ── */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '20px 36px',
        borderBottom: `1px solid ${PANEL_BORDER}`,
        background: 'rgba(10,14,20,0.85)',
        backdropFilter: 'blur(12px)',
        position: 'sticky', top: 0, zIndex: 50,
      }}>
        <div>
          <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: 20 }}>
            Committee Report
          </div>
          <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 12, color: '#9AA4B2', marginTop: 3 }}>
            {report.summary.headline}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <button
            onClick={handleCopyExport}
            style={{
              padding: '9px 14px', borderRadius: 9,
              border: `1px solid rgba(255,255,255,0.10)`,
              background: 'rgba(255,255,255,0.03)',
              color: '#EEF3FF', cursor: 'pointer',
              fontFamily: 'Inter, sans-serif', fontSize: 12, fontWeight: 600,
            }}
          >
            {copyState === 'copied' ? 'Copied JSON' : copyState === 'failed' ? 'Copy Failed' : 'Copy JSON'}
          </button>
          <button
            onClick={handleDownloadExport}
            style={{
              padding: '9px 14px', borderRadius: 9,
              border: `1px solid rgba(77,163,255,0.25)`,
              background: 'rgba(77,163,255,0.08)',
              color: '#4DA3FF', cursor: 'pointer',
              fontFamily: 'Inter, sans-serif', fontSize: 12, fontWeight: 600,
              transition: 'background 0.2s',
            }}
          >
            ↓ Export JSON
          </button>
          <Link
            to={runId ? `/committee/run/${runId}` : '/committee'}
            style={{ color: '#9AA4B2', textDecoration: 'none', fontFamily: 'Inter, sans-serif', fontSize: 12 }}
          >
            ← Back to Run
          </Link>
        </div>
      </div>

      {/* ── Main content ── */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        style={{ padding: '28px 36px 0' }}
      >
        {report.warnings.length > 0 && (
          <div style={{ marginBottom: 18, padding: '12px 14px', borderRadius: 12, background: 'rgba(251,191,36,0.08)', border: '1px solid rgba(251,191,36,0.18)', color: '#FCD34D', fontFamily: 'Inter, sans-serif', fontSize: 12, lineHeight: 1.5 }}>
            {report.warnings.slice(0, 3).join(' ')}
          </div>
        )}

        {/* KPI row */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 12, marginBottom: 24 }}>
          <KpiCard label="Baseline Score" value={formatScore(report.summary.baselineScore)} color="#9AA4B2" />
          <KpiCard label="Best Score" value={formatScore(report.summary.bestScore)} color="#4DA3FF" />
          <KpiCard
            label="Gain"
            value={`${gainPositive ? '+' : ''}${formatPercent(gain)}`}
            color={gainPositive ? '#4ADE80' : '#FB7185'}
          />
          <KpiCard
            label="Rewrites Accepted"
            value={`${report.summary.acceptedRewrites}/${report.summary.rewritesTested}`}
            color="#EEF3FF"
            sub={`${report.summary.rewritesTested - report.summary.acceptedRewrites} reverted`}
          />
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 12, marginBottom: 24 }}>
          <KpiCard label="Industry" value={String(exportPayload.committeeSummary?.industryLabel ?? 'General Enterprise')} />
          <KpiCard label="AI Coverage" value={`${Number(exportPayload.committeeSummary?.llmCoveragePct ?? 0).toFixed(0)}%`} />
          <KpiCard label="Scoring Mode" value={String(exportPayload.committeeSummary?.evaluationMode ?? report.evaluationMode).replace(/_/g, ' ')} />
        </div>

        {/* Main two-column layout */}
        <div style={{ display: 'grid', gridTemplateColumns: '1.1fr 0.9fr', gap: 18 }}>

          {/* Left: Optimized Document sections */}
          <div>
            <div style={{ padding: '16px 18px', borderRadius: 14, background: 'rgba(10,14,20,0.76)', border: `1px solid ${PANEL_BORDER}` }}>
              <SectionCard label="Optimized Document" />
              <div style={{ display: 'grid', gap: 10 }}>
                {exportPayload.sections.map(section => (
                  <div key={section.sectionId} style={{
                    padding: '12px 14px', borderRadius: 10,
                    background: 'rgba(255,255,255,0.02)',
                    border: `1px solid ${PANEL_BORDER}`,
                  }}>
                    <div style={{
                      fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: 12,
                      color: '#EEF3FF', marginBottom: 8,
                    }}>
                      {section.sectionId}. {section.title}
                    </div>
                    {/* Before */}
                    <div style={{
                      padding: '8px 10px', borderRadius: 7,
                      background: 'rgba(251,113,133,0.04)',
                      borderLeft: '2px solid rgba(251,113,133,0.2)',
                      marginBottom: 6,
                    }}>
                      <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: '#FB7185', letterSpacing: '0.1em', marginBottom: 4 }}>
                        ORIGINAL
                      </div>
                      <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 11, color: '#9AA4B2', lineHeight: 1.5 }}>
                        {section.originalContent.slice(0, 200)}{section.originalContent.length > 200 ? '…' : ''}
                      </div>
                    </div>
                    {/* After */}
                    <div style={{
                      padding: '8px 10px', borderRadius: 7,
                      background: 'rgba(74,222,128,0.04)',
                      borderLeft: '2px solid rgba(74,222,128,0.2)',
                    }}>
                      <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 8, color: '#4ADE80', letterSpacing: '0.1em', marginBottom: 4 }}>
                        OPTIMIZED
                      </div>
                      <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 11, color: '#C5CDD8', lineHeight: 1.5 }}>
                        {section.optimizedContent.slice(0, 260)}{section.optimizedContent.length > 260 ? '…' : ''}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right column: persona outcomes + rewrite log */}
          <div style={{ display: 'grid', gap: 18, alignContent: 'start' }}>

            {/* Persona outcomes */}
            <div style={{ padding: '16px 18px', borderRadius: 14, background: 'rgba(10,14,20,0.76)', border: `1px solid ${PANEL_BORDER}` }}>
              <SectionCard label="Persona Outcomes" />
              <div style={{ display: 'grid', gap: 8 }}>
                {(report.personas ?? []).map(persona => {
                  const color = sentimentColor((persona as any).sentiment ?? 'neutral');
                  const score = Math.max(0, Math.min(1, persona.currentScore ?? 0));
                  const pct = Math.max(0, Math.min(100, Math.round(score * 100)));
                  return (
                    <div key={persona.id} style={{
                      padding: '10px 12px', borderRadius: 10,
                      background: 'rgba(255,255,255,0.025)',
                      borderLeft: `3px solid ${color}`,
                    }}>
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
                      {/* Score bar */}
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

            {/* Rewrite log */}
            <div style={{ padding: '16px 18px', borderRadius: 14, background: 'rgba(10,14,20,0.76)', border: `1px solid ${PANEL_BORDER}` }}>
              <SectionCard label={`Rewrite Log (${report.rewrites.length} total)`} />
              <div style={{ display: 'grid', gap: 6 }}>
                {report.rewrites.slice().reverse().slice(0, 12).map(rewrite => {
                  const kept = rewrite.decision === 'kept';
                  return (
                    <div key={rewrite.experimentId} style={{
                      padding: '9px 11px', borderRadius: 9,
                      background: kept ? 'rgba(74,222,128,0.03)' : 'rgba(251,113,133,0.02)',
                      borderLeft: `2px solid ${kept ? 'rgba(74,222,128,0.3)' : 'rgba(251,113,133,0.2)'}`,
                    }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, marginBottom: 3 }}>
                        <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#6B7480' }}>
                          #{rewrite.experimentId} · §{rewrite.sectionId} · {rewrite.parameterName}
                        </div>
                        <div style={{
                          fontFamily: 'JetBrains Mono, monospace', fontSize: 9,
                          color: kept ? '#4ADE80' : '#FB7185',
                          flexShrink: 0,
                        }}>
                          {kept ? 'KEPT' : 'REVERTED'} · {rewrite.deltaPercent > 0 ? '+' : ''}{formatPercent(rewrite.deltaPercent)}
                        </div>
                      </div>
                      <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 11, color: '#9AA4B2', lineHeight: 1.4 }}>
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

          </div>
        </div>
      </motion.div>
    </div>
    </ErrorBoundary>
  );
}
