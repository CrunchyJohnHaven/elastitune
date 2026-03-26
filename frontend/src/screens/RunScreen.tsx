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
import { SkeletonBlock, SkeletonCard, SkeletonPage } from '@/components/ui/Skeleton';

export default function RunScreen() {
  const { runId } = useParams<{ runId: string }>();
  const { runSnapshot } = useAppStore();
  const toast = useToast();

  // Connect WebSocket and walkthrough events
  useRunSocket(runId ?? null);
  useWalkthroughEvents();

  const stage = runSnapshot?.stage ?? 'idle';
  const showExplainer = useAppStore(state => state.showExplainer);

  if (!runSnapshot) {
    return (
      <SkeletonPage
        title="Loading search run"
        subtitle="The backend is preparing the live telemetry, personas, and optimization workspace."
      >
        <div style={{ display: 'grid', gridTemplateColumns: '320px minmax(0, 1fr) 360px', gap: 16 }}>
          <SkeletonCard minHeight={520}>
            <SkeletonBlock height={14} width={120} />
            <div style={{ marginTop: 14 }}>
              <SkeletonBlock height={10} width="80%" />
            </div>
            <div style={{ marginTop: 18, display: 'grid', gap: 10 }}>
              <SkeletonBlock height={72} />
              <SkeletonBlock height={72} />
              <SkeletonBlock height={72} />
            </div>
          </SkeletonCard>
          <SkeletonCard minHeight={520}>
            <SkeletonBlock height={20} width={180} />
            <div style={{ marginTop: 18 }}>
              <SkeletonBlock height={340} radius={18} />
            </div>
          </SkeletonCard>
          <SkeletonCard minHeight={520}>
            <SkeletonBlock height={14} width={110} />
            <div style={{ marginTop: 16, display: 'grid', gap: 10 }}>
              <SkeletonBlock height={84} />
              <SkeletonBlock height={84} />
              <SkeletonBlock height={84} />
            </div>
          </SkeletonCard>
        </div>
      </SkeletonPage>
    );
  }

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
          <ErrorBoundary fallbackTitle="Visualization error">
            <FishTankCanvas />
          </ErrorBoundary>
          {runId && (
            <RunControlBar
              stage={stage}
              runId={runId}
              onStop={handleStop}
            />
          )}
        </div>

        {/* Right rail or explainer */}
        {showExplainer ? <ExplainerPanel /> : <RightRail />}
      </div>

      {/* Walkthrough overlay */}
      <WalkthroughOverlay />
    </ShellFrame>
  );
}
