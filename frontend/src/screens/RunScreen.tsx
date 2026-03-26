import React from 'react';
import { useParams } from 'react-router-dom';
import { useRunSocket } from '@/hooks/useRunSocket';
import { useWalkthroughEvents } from '@/hooks/useWalkthroughEvents';
import { useAppStore } from '@/store/useAppStore';
import { useToast } from '@/components/ui/ToastProvider';
import { api } from '@/lib/api';
import ShellFrame from '@/components/layout/ShellFrame';
import TopTelemetryBar from '@/components/layout/TopTelemetryBar';
import LeftRail from '@/components/layout/LeftRail';
import RightRail from '@/components/layout/RightRail';
import ExplainerPanel from '@/components/run/ExplainerPanel';
import FishTankCanvas from '@/components/run/FishTankCanvas';
import RunControlBar from '@/components/run/RunControlBar';
import WalkthroughOverlay from '@/components/walkthrough/WalkthroughOverlay';
import ErrorBoundary from '@/components/ui/ErrorBoundary';
import SkeletonCard from '@/components/ui/SkeletonCard';

export default function RunScreen() {
  const { runId } = useParams<{ runId: string }>();
  const { runSnapshot } = useAppStore();
  const toast = useToast();

  // Connect WebSocket and walkthrough events
  useRunSocket(runId ?? null);
  useWalkthroughEvents();

  const stage = runSnapshot?.stage ?? 'idle';
  const showExplainer = useAppStore(state => state.showExplainer);

  const handleStop = async () => {
    if (!runId) return;
    try {
      await api.stopRun(runId);
      toast.info('Stopping optimization\u2026');
    } catch (err) {
      toast.error('Failed to stop run. Try again.');
      console.error('Stop run failed:', err);
    }
  };

  return (
    <ShellFrame>
      {/* Top bar */}
      <TopTelemetryBar />

      {/* Main grid: left | center | right */}
      <div
        style={{
          flex: 1,
          display: 'grid',
          gridTemplateColumns: '320px 1fr 360px',
          overflow: 'hidden',
          height: 0, // forces grid to fill available flex space
        }}
      >
        {/* Left rail */}
        <LeftRail />

        {/* Center: fish tank + control overlay */}
        <div
          style={{
            position: 'relative',
            overflow: 'hidden',
            background: '#05070B',
          }}
        >
          {runSnapshot ? (
            <ErrorBoundary fallbackTitle="Visualization error">
              <FishTankCanvas />
            </ErrorBoundary>
          ) : (
            <div
              style={{
                height: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: 24,
                background: 'radial-gradient(circle at 50% 20%, rgba(77,163,255,0.08) 0%, rgba(5,7,11,0.98) 60%)',
              }}
            >
              <div style={{ width: 'min(560px, 100%)', display: 'grid', gap: 16 }}>
                <SkeletonCard lines={2} height={120} titleWidth={220} />
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 16 }}>
                  <SkeletonCard lines={3} height={160} titleWidth={120} />
                  <SkeletonCard lines={3} height={160} titleWidth={120} />
                </div>
              </div>
            </div>
          )}
          {runId && (
            <RunControlBar
              stage={stage}
              runId={runId}
              onStop={handleStop}
            />
          )}
        </div>

        {/* Right rail or explainer */}
        {showExplainer ? <ExplainerPanel /> : (runSnapshot ? <RightRail /> : <div style={{ padding: 16 }}><SkeletonCard lines={6} height={280} /></div>)}
      </div>

      {/* Walkthrough overlay */}
      <WalkthroughOverlay />
    </ShellFrame>
  );
}
