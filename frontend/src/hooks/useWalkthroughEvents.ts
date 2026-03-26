import { useEffect } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { useWalkthroughStore } from '@/store/useWalkthroughStore';

/**
 * Bridges the run store events to the walkthrough step progression.
 * Watches for key state changes and calls handleEvent() on the walkthrough store.
 */
export function useWalkthroughEvents() {
  const active = useWalkthroughStore(s => s.active);
  const handleEvent = useWalkthroughStore(s => s.handleEvent);

  // Watch for snapshot loaded
  const runSnapshot = useAppStore(s => s.runSnapshot);
  useEffect(() => {
    if (!active || !runSnapshot) return;
    handleEvent('snapshot');
  }, [active, runSnapshot?.runId]);

  // Watch for new experiments
  const latestExperiment = useAppStore(s => s.latestExperiment);
  useEffect(() => {
    if (!active || !latestExperiment) return;
    handleEvent('experiment.completed');
  }, [active, latestExperiment?.experimentId]);

  // Watch for persona batches
  const personas = useAppStore(s => s.runSnapshot?.personas);
  const personaCount = personas?.length ?? 0;
  const anySearching = personas?.some(p => p.state !== 'idle') ?? false;
  useEffect(() => {
    if (!active || !anySearching) return;
    handleEvent('persona.batch');
  }, [active, anySearching, personaCount]);

  // Watch for stage changes
  const stage = useAppStore(s => s.runSnapshot?.stage);
  useEffect(() => {
    if (!active || !stage) return;
    if (stage === 'completed') {
      handleEvent('run.stage');
    }
  }, [active, stage]);

  // Watch for report ready
  const report = useAppStore(s => s.report);
  useEffect(() => {
    if (!active || !report) return;
    handleEvent('report.ready');
  }, [active, report]);
}
