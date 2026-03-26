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
import { SkeletonBlock, SkeletonCard, SkeletonPage } from '@/components/ui/Skeleton';

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

  if (!snapshot) {
    return (
      <ErrorBoundary title="Committee Run Failed">
        <SkeletonPage
          title="Loading committee run"
          subtitle="The document is being parsed, personas are being prepared, and the live consensus loop is warming up."
        >
          <div style={{ display: 'grid', gridTemplateColumns: '320px minmax(0, 1fr) 360px', gap: 16 }}>
            <SkeletonCard minHeight={520}>
              <SkeletonBlock height={14} width={130} />
              <div style={{ marginTop: 14, display: 'grid', gap: 10 }}>
                <SkeletonBlock height={78} />
                <SkeletonBlock height={78} />
                <SkeletonBlock height={78} />
              </div>
            </SkeletonCard>
            <SkeletonCard minHeight={520}>
              <SkeletonBlock height={18} width={190} />
              <div style={{ marginTop: 18 }}>
                <SkeletonBlock height={350} radius={18} />
              </div>
            </SkeletonCard>
            <SkeletonCard minHeight={520}>
              <SkeletonBlock height={14} width={120} />
              <div style={{ marginTop: 14, display: 'grid', gap: 10 }}>
                <SkeletonBlock height={90} />
                <SkeletonBlock height={90} />
                <SkeletonBlock height={90} />
              </div>
            </SkeletonCard>
          </div>
        </SkeletonPage>
      </ErrorBoundary>
    );
  }

  return (
    <ErrorBoundary title="Committee Run Failed">
      <ShellFrame>
        <CommitteeTopBar />
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
                <Link to="/committee/history" style={{ padding: '8px 12px', borderRadius: 10, background: 'rgba(10,14,20,0.9)', border: '1px solid rgba(255,255,255,0.08)', color: '#EEF3FF', textDecoration: 'none', fontSize: 12, fontFamily: 'Inter, sans-serif' }}>
                  History
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
