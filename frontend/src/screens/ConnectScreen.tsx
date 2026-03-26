import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import ConnectForm from '@/components/connect/ConnectForm';
import ClusterSummaryCard from '@/components/connect/ClusterSummaryCard';
import DemoPreviewCanvas from '@/components/connect/DemoPreviewCanvas';
import CaseStudyHero from '@/components/connect/CaseStudyHero';
import RunHistory from '@/components/connect/RunHistory';
import { useAppStore } from '@/store/useAppStore';
import { useToast } from '@/components/ui/ToastProvider';
import { api } from '@/lib/api';
import type { ConnectionSummary, SearchRunListItem } from '@/types/contracts';
import { Link } from 'react-router-dom';


export default function ConnectScreen() {
  const navigate = useNavigate();
  const { setConnection, setRunId } = useAppStore();
  const toast = useToast();

  const [isLoading, setIsLoading] = useState(false);
  const [connectedId, setConnectedId] = useState<string | null>(null);
  const [summary, setSummary] = useState<ConnectionSummary | null>(null);
  const [startingRun, setStartingRun] = useState(false);
  const [previousRun, setPreviousRun] = useState<SearchRunListItem | null>(null);

  const handleConnected = async (
    connectionId: string,
    sum: ConnectionSummary,
    autoRun?: boolean,
    previousRunCandidate?: SearchRunListItem | null,
  ) => {
    setConnection(connectionId, sum);
    setConnectedId(connectionId);
    setSummary(sum);
    setPreviousRun(previousRunCandidate ?? null);

    // If autoRun is set (benchmark preset), skip the summary card and go straight to optimization
    if (autoRun) {
      toast.info(
        previousRunCandidate
          ? 'Previous run found — continuing from the strongest saved profile…'
          : 'Benchmark detected — starting optimization\u2026'
      );
      try {
        const resp = await api.startRun(connectionId, {
          durationMinutes: 30,
          maxExperiments: 200,
          personaCount: 36,
          autoStopOnPlateau: true,
          previousRunId: previousRunCandidate?.run_id,
        });
        setRunId(resp.runId);
        navigate(`/run/${resp.runId}`);
      } catch (err) {
        toast.error('Failed to start optimization. Check your connection.');
        console.error('Auto-start run failed:', err);
        setIsLoading(false);
      }
      return;
    }

    toast.success(`Connected to ${sum.clusterName}`);
  };

  const handleDemoStart = (runId: string) => {
    setRunId(runId);
    toast.info('Demo starting\u2026');
    navigate(`/run/${runId}`);
  };

  const handleStartOptimization = async (
    connectionId: string,
    options: {
      durationMinutes: number;
      maxExperiments: number;
      personaCount: number;
      autoStopOnPlateau: boolean;
      previousRunId?: string;
    }
  ) => {
    setStartingRun(true);
    try {
      const resp = await api.startRun(connectionId, options);
      setRunId(resp.runId);
      toast.info('Optimization starting\u2026');
      navigate(`/run/${resp.runId}`);
    } catch (err) {
      toast.error('Failed to start optimization. Check your connection.');
      console.error('Start run failed:', err);
      setStartingRun(false);
    }
  };

  return (
    <div
      style={{
        width: '100vw',
        height: '100vh',
        background: '#05070B',
        display: 'flex',
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      {/* Background radial gradient */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'radial-gradient(ellipse 70% 60% at 50% 0%, rgba(77,163,255,0.06) 0%, transparent 70%)',
          pointerEvents: 'none',
        }}
      />

      {/* Left side — form panel */}
      <div
        style={{
          width: '44%',
          minWidth: 420,
          maxWidth: 580,
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'flex-start',
          padding: '28px 52px 48px',
          position: 'relative',
          zIndex: 10,
          overflowY: 'auto',
          overflowX: 'hidden',
          scrollPaddingTop: 24,
        }}
      >
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
        >
          {/* Logo */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              marginBottom: 10,
            }}
          >
            <div
              style={{
                width: 36,
                height: 36,
                borderRadius: '50%',
                background:
                  'radial-gradient(circle, #4DA3FF 0%, rgba(77,163,255,0.4) 55%, rgba(77,163,255,0.1) 100%)',
                boxShadow: '0 0 18px rgba(77,163,255,0.6)',
                flexShrink: 0,
              }}
            />
            <span
              style={{
                fontFamily: 'Inter, sans-serif',
                fontWeight: 700,
                fontSize: 26,
                color: '#EEF3FF',
                letterSpacing: '-0.02em',
              }}
            >
              ElastiTune
            </span>
          </div>

          {/* Tagline */}
          <p
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 11,
              color: '#6B7480',
              marginBottom: 14,
              letterSpacing: '0.04em',
            }}
          >
            Find weak search results, test fixes automatically, and leave with a before/after report.
          </p>

          <div
            style={{
              fontFamily: 'Inter, sans-serif',
              fontSize: 15,
              color: '#C5CDD8',
              lineHeight: 1.6,
              marginBottom: 24,
              maxWidth: 520,
            }}
          >
            ElastiTune watches how different people would search your system, tries ranking changes for you, and keeps only the ones that improve results.
          </div>

          <div
            style={{
              marginBottom: 22,
              padding: '12px 14px',
              borderRadius: 10,
              background: 'rgba(255,255,255,0.025)',
              border: '1px solid rgba(255,255,255,0.06)',
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
              Easiest path
            </div>
            <div
              style={{
                fontFamily: 'Inter, sans-serif',
                fontSize: 11,
                color: '#9AA4B2',
                lineHeight: 1.5,
              }}
            >
              Use one of these two first steps:
              <br />
              1. Click <span style={{ color: '#EEF3FF' }}>Launch Demo</span> if you just want to watch it work.
              <br />
              2. Click <span style={{ color: '#EEF3FF' }}>Use benchmark preset</span> if you want a real local benchmark with a fixed test set.
            </div>
            <div style={{ marginTop: 10 }}>
              <Link
                to="/benchmarks"
                style={{
                  fontFamily: 'Inter, sans-serif',
                  fontSize: 12,
                  fontWeight: 600,
                  color: '#7CE7FF',
                  textDecoration: 'none',
                }}
              >
                Open benchmark dashboard
              </Link>
            </div>
          </div>

          {/* Form card */}
          <div
            style={{
              background: 'rgba(10,14,20,0.72)',
              border: '1px solid rgba(255,255,255,0.08)',
              borderRadius: 12,
              padding: '28px 28px',
              backdropFilter: 'blur(16px)',
              boxShadow: '0 24px 64px rgba(0,0,0,0.4)',
            }}
          >
            <h2
              style={{
                fontFamily: 'Inter, sans-serif',
                fontWeight: 600,
                fontSize: 17,
                color: '#EEF3FF',
                marginBottom: 10,
              }}
            >
              Start a search tuning run
            </h2>
            <div
              style={{
                fontFamily: 'Inter, sans-serif',
                fontSize: 12,
                color: '#9AA4B2',
                lineHeight: 1.5,
                marginBottom: 20,
              }}
            >
              The sample benchmark is the simplest path. Only open the custom index section if you want to test your own Elasticsearch data.
            </div>

            <ConnectForm
              onConnected={handleConnected}
              onDemoStart={handleDemoStart}
              isLoading={isLoading}
              setIsLoading={setIsLoading}
            />
          </div>

          {/* Cluster summary card */}
          {summary && connectedId && (
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, ease: 'easeOut' }}
            >
              <ClusterSummaryCard
                summary={summary}
                connectionId={connectedId}
                previousRun={previousRun}
                onStartOptimization={handleStartOptimization}
                isLoading={startingRun}
              />
            </motion.div>
          )}

          <RunHistory />

          {/* Footer note */}
          <p
            style={{
              fontFamily: 'Inter, sans-serif',
              fontSize: 11,
              color: '#4B5563',
              marginTop: 20,
              textAlign: 'center',
            }}
          >
            No data leaves your environment — all optimization runs locally.
          </p>
          <div style={{ marginTop: 18, textAlign: 'center' }}>
            <Link
              to="/committee"
              style={{
                fontFamily: 'Inter, sans-serif',
                fontSize: 12,
                color: '#4DA3FF',
                textDecoration: 'none',
              }}
            >
              Switch to Simulated Buying Committee mode
            </Link>
          </div>
        </motion.div>
      </div>

      {/* Divider */}
      <div
        style={{
          width: 1,
          height: '100%',
          background:
            'linear-gradient(to bottom, transparent 5%, rgba(255,255,255,0.06) 30%, rgba(255,255,255,0.06) 70%, transparent 95%)',
          flexShrink: 0,
        }}
      />

      {/* Right side — case study hero */}
      <div
        style={{
          flex: 1,
          position: 'relative',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Animated background canvas (dimmed) */}
        <div style={{ opacity: 0.25 }}>
          <DemoPreviewCanvas />
        </div>

        {/* Case study overlay */}
        <CaseStudyHero />
      </div>
    </div>
  );
}

