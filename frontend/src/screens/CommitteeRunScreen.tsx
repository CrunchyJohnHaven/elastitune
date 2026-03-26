import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import ShellFrame from '@/components/layout/ShellFrame';
import CommitteeTopBar from '@/components/committee/CommitteeTopBar';
import CommitteeLeftRail from '@/components/committee/CommitteeLeftRail';
import CommitteeSpaceCanvas from '@/components/committee/CommitteeSpaceCanvas';
import CommitteeRightRail from '@/components/committee/CommitteeRightRail';
import ErrorBoundary from '@/components/ErrorBoundary';
import ConfirmDialog from '@/components/ui/ConfirmDialog';
import { useToast } from '@/components/ui/ToastProvider';
import { useCommitteeRunSocket } from '@/hooks/useCommitteeRunSocket';
import { useViewportWidth } from '@/hooks/useViewportWidth';
import { useCommitteeStore } from '@/store/useCommitteeStore';
import { api } from '@/lib/api';
import { formatPercent, formatScore } from '@/lib/format';

export default function CommitteeRunScreen() {
  const { runId } = useParams<{ runId: string }>();
  const navigate = useNavigate();
  const toast = useToast();
  const width = useViewportWidth();
  const snapshot = useCommitteeStore(state => state.snapshot);
  const report = useCommitteeStore(state => state.report);
  const socketStatus = useCommitteeStore(state => state.socketStatus);
  const [loadingTimedOut, setLoadingTimedOut] = useState(false);
  const [stopLoading, setStopLoading] = useState(false);
  const [stopError, setStopError] = useState<string | null>(null);
  const [showStopConfirm, setShowStopConfirm] = useState(false);

  useCommitteeRunSocket(runId ?? null);

  const isCompact = width < 1320;

  useEffect(() => {
    if (snapshot) {
      setLoadingTimedOut(false);
      return;
    }
    const timer = window.setTimeout(() => setLoadingTimedOut(true), 30000);
    return () => window.clearTimeout(timer);
  }, [snapshot]);

  const warningMessages = useMemo(() => {
    if (!snapshot) return [];
    return Array.from(new Set([...(snapshot.warnings ?? []), ...(snapshot.document.parseWarnings ?? [])]));
  }, [snapshot]);

  const handleStop = async () => {
    if (!runId) return;
    setStopLoading(true);
    setStopError(null);
    try {
      await api.stopCommitteeRun(runId);
      toast.info('Stopping committee run…');
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to stop committee run';
      setStopError(message);
      toast.error(message);
    } finally {
      setStopLoading(false);
    }
  };

  const stopDescription = snapshot
    ? `Current consensus is ${formatScore(snapshot.metrics.currentScore)} (${formatPercent(snapshot.metrics.improvementPct)} from baseline). ${snapshot.metrics.rewritesTested}/${Math.max(snapshot.metrics.rewritesTested, 30)} rewrites have run so far.`
    : 'The run will stop and keep the results gathered so far.';

  return (
    <ErrorBoundary title="Committee Run Failed">
      <ShellFrame>
        <CommitteeTopBar />
        {!snapshot && (
          <div
            style={{
              flex: 1,
              position: 'relative',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background:
                'radial-gradient(circle at 50% 12%, rgba(77,163,255,0.12) 0%, rgba(8,12,18,0.96) 52%, rgba(5,7,11,1) 100%)',
            }}
          >
            <div
              style={{
                width: 620,
                maxWidth: 'calc(100vw - 48px)',
                padding: '28px 30px',
                borderRadius: 18,
                background: 'rgba(8,12,18,0.78)',
                border: '1px solid rgba(255,255,255,0.08)',
                boxShadow: '0 30px 80px rgba(0,0,0,0.32)',
              }}
              >
                <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#6B7480', letterSpacing: '0.16em', textTransform: 'uppercase', marginBottom: 10 }}>
                  Committee Launch
                </div>
                <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 28, fontWeight: 700, color: '#EEF3FF', marginBottom: 8 }}>
                  Building the live committee run
                </div>
                <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 14, color: '#9AA4B2', lineHeight: 1.6, marginBottom: 18 }}>
                  Parsing the document, establishing the baseline, then pacing the rewrite loop so you can actually watch the room react section by section.
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 10 }}>
                  {[
                    ['Status', loadingTimedOut ? 'Timed out' : socketStatus === 'reconnecting' ? 'Reconnecting' : socketStatus === 'dead' ? 'Connection lost' : 'Starting'],
                    ['Mode', 'Full Committee'],
                    ['Output', 'Live consensus'],
                  ].map(([label, value]) => (
                    <div key={label} style={{ padding: '12px 14px', borderRadius: 12, background: 'rgba(255,255,255,0.03)' }}>
                      <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#6B7480', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 6 }}>{label}</div>
                      <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#EEF3FF', fontWeight: 600 }}>{value}</div>
                    </div>
                  ))}
                </div>
                {loadingTimedOut && (
                  <div style={{ marginTop: 18, display: 'flex', gap: 10 }}>
                    <button
                      onClick={() => window.location.reload()}
                      style={{ padding: '10px 14px', borderRadius: 10, border: 'none', background: '#4DA3FF', color: '#05070B', cursor: 'pointer', fontFamily: 'Inter, sans-serif', fontWeight: 700 }}
                    >
                      Retry
                    </button>
                    <Link
                      to="/committee"
                      style={{ padding: '10px 14px', borderRadius: 10, border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.03)', color: '#EEF3FF', textDecoration: 'none', fontFamily: 'Inter, sans-serif', fontWeight: 600 }}
                    >
                      Back to Setup
                    </Link>
                  </div>
                )}
                {loadingTimedOut && (
                  <div style={{ marginTop: 12, color: '#FBBF24', fontFamily: 'Inter, sans-serif', fontSize: 12 }}>
                    Connection failed. Check that the backend and WebSocket server are running, then retry.
                  </div>
                )}
              </div>
            </div>
        )}
        {snapshot && (
          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, ease: 'easeOut' }}
            style={{
              flex: 1,
              display: 'grid',
              gridTemplateColumns: isCompact ? 'minmax(0, 1fr)' : '320px minmax(0, 1fr) 360px',
              gridTemplateRows: isCompact ? 'minmax(420px, 60vh) auto auto' : '1fr',
              height: isCompact ? 'auto' : 0,
              minHeight: 0,
              overflow: isCompact ? 'auto' : 'hidden',
            }}
          >
            {!isCompact && <CommitteeLeftRail />}
            <div style={{ position: 'relative', background: '#05070B', minHeight: isCompact ? 420 : 0 }}>
              <CommitteeSpaceCanvas />
              {warningMessages.length > 0 && (
                <div style={{ position: 'absolute', top: 18, left: 18, zIndex: 5, maxWidth: 440 }}>
                  {warningMessages.slice(0, 3).map((warning) => (
                    <div
                      key={warning}
                      style={{
                        padding: '10px 12px',
                        borderRadius: 10,
                        background: 'rgba(251,191,36,0.10)',
                        border: '1px solid rgba(251,191,36,0.20)',
                        color: '#FCD34D',
                        fontFamily: 'Inter, sans-serif',
                        fontSize: 12,
                        marginBottom: 8,
                        lineHeight: 1.45,
                      }}
                    >
                      {warning}
                    </div>
                  ))}
                </div>
              )}
              {socketStatus === 'dead' && snapshot.stage !== 'completed' && (
                <div
                  style={{
                    position: 'absolute',
                    left: 18,
                    right: 18,
                    bottom: 18,
                    zIndex: 5,
                    padding: '12px 14px',
                    borderRadius: 12,
                    background: 'rgba(251,113,133,0.12)',
                    border: '1px solid rgba(251,113,133,0.22)',
                    color: '#FCA5A5',
                    fontFamily: 'Inter, sans-serif',
                    fontSize: 12,
                  }}
                >
                  Connection lost. Refresh to reconnect. The last visible run state may be stale.
                </div>
              )}
              <div style={{ position: 'absolute', top: 18, right: 18, display: 'flex', gap: 10, zIndex: 5 }}>
                <Link to="/committee" style={{ padding: '8px 12px', borderRadius: 10, background: 'rgba(10,14,20,0.9)', border: '1px solid rgba(255,255,255,0.08)', color: '#EEF3FF', textDecoration: 'none', fontSize: 12, fontFamily: 'Inter, sans-serif' }}>
                  New Committee
                </Link>
                <button
                  onClick={() => setShowStopConfirm(true)}
                  disabled={stopLoading || snapshot.stage === 'completed' || snapshot.stage === 'stopping'}
                  style={{ padding: '8px 12px', borderRadius: 10, background: 'rgba(251,113,133,0.12)', border: '1px solid rgba(251,113,133,0.22)', color: '#FB7185', fontSize: 12, fontFamily: 'Inter, sans-serif', cursor: stopLoading ? 'not-allowed' : 'pointer', opacity: stopLoading ? 0.7 : 1 }}
                >
                  {stopLoading || snapshot.stage === 'stopping' ? 'Stopping…' : 'Stop Run'}
                </button>
                {(snapshot.stage === 'completed' || report) && runId && (
                  <button
                    onClick={() => navigate(`/committee/report/${runId}`)}
                    style={{ padding: '8px 12px', borderRadius: 10, background: 'rgba(74,222,128,0.12)', border: '1px solid rgba(74,222,128,0.22)', color: '#4ADE80', fontSize: 12, fontFamily: 'Inter, sans-serif', cursor: 'pointer' }}
                  >
                    View Report
                  </button>
                )}
              </div>
              {stopError && (
                <div style={{ position: 'absolute', top: 64, right: 18, zIndex: 5, maxWidth: 300, padding: '10px 12px', borderRadius: 10, background: 'rgba(251,113,133,0.12)', border: '1px solid rgba(251,113,133,0.22)', color: '#FCA5A5', fontFamily: 'Inter, sans-serif', fontSize: 12 }}>
                  {stopError}
                </div>
              )}
            </div>
            {isCompact && <CommitteeLeftRail compact />}
            <CommitteeRightRail compact={isCompact} />
          </motion.div>
        )}
      </ShellFrame>
      <ConfirmDialog
        open={showStopConfirm}
        title="Stop this committee run?"
        description={stopDescription}
        confirmLabel="Stop Run"
        confirmColor="#FB7185"
        cancelLabel="Keep Running"
        onConfirm={() => {
          setShowStopConfirm(false);
          void handleStop();
        }}
        onCancel={() => setShowStopConfirm(false)}
      />
    </ErrorBoundary>
  );
}
