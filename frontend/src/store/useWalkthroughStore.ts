import { create } from 'zustand';

export interface WalkthroughStep {
  id: number;
  title: string;
  description: string;
  /** Which part of the UI this step highlights */
  highlight: 'full' | 'left' | 'center' | 'right' | 'top' | 'report';
  /** Event type that auto-advances to this step (null = manual or first) */
  triggerEvent?: string;
  /** Minimum delay (ms) before this step can trigger from the previous */
  minDelay?: number;
}

export const WALKTHROUGH_STEPS: WalkthroughStep[] = [
  {
    id: 0,
    title: 'Welcome to ElastiTune',
    description:
      'ElastiTune is like a piano tuner for your search engine. It tests hundreds of small changes to how search results are ranked, keeps the ones that work, and throws away the ones that don\'t. You end up with measurably better search.',
    highlight: 'full',
  },
  {
    id: 1,
    title: 'Connected to your search engine',
    description:
      'We just connected to a search engine with 42,381 security advisories. ElastiTune detected the document structure and built a test suite of realistic search queries to measure quality.',
    highlight: 'top',
    triggerEvent: 'snapshot',
  },
  {
    id: 2,
    title: 'Measuring current search quality',
    description:
      'Before changing anything, we run all test queries and measure how often the right document appears in the top 10 results. This "nDCG@10" score is the starting line. Think of it like a batting average for your search engine.',
    highlight: 'left',
    minDelay: 2000,
  },
  {
    id: 3,
    title: 'First experiment: testing a change',
    description:
      'ElastiTune just tried its first tweak: adjusting how strictly search terms need to match. It ran every test query with the new setting and compared it against the baseline. This took about 2 seconds.',
    highlight: 'right',
    triggerEvent: 'experiment.completed',
  },
  {
    id: 4,
    title: 'That change improved search!',
    description:
      'The green checkmark means this change made search results better. From now on, all future experiments build on top of this improved version. Think of it like compound interest: each small gain stacks on the last.',
    highlight: 'right',
    triggerEvent: 'experiment.completed',
    minDelay: 1500,
  },
  {
    id: 5,
    title: 'Not every change helps',
    description:
      'This experiment made results worse, so ElastiTune automatically rolled it back. Only improvements survive. This is the key insight: we try many ideas quickly and let the data decide what works.',
    highlight: 'right',
    triggerEvent: 'experiment.completed',
    minDelay: 1500,
  },
  {
    id: 6,
    title: 'Simulated searchers test the changes',
    description:
      'Each dot orbiting the center represents a different type of person searching your system: analysts, executives, engineers. They each search differently. ElastiTune makes sure improvements help everyone, not just one group.',
    highlight: 'center',
    triggerEvent: 'persona.batch',
    minDelay: 2000,
  },
  {
    id: 7,
    title: 'Multiple improvements stacking up',
    description:
      'Several experiments have now completed. The left panel shows your running score: how much search has improved so far. Every green result is a permanent gain locked in.',
    highlight: 'left',
    triggerEvent: 'experiment.completed',
    minDelay: 3000,
  },
  {
    id: 8,
    title: 'Optimization complete',
    description:
      'All experiments are finished. The final score shows the total improvement from where we started. Every change is logged, every decision is auditable, and the optimized search configuration is ready to deploy.',
    highlight: 'full',
    triggerEvent: 'run.stage',
    minDelay: 2000,
  },
  {
    id: 9,
    title: 'Your before-and-after report',
    description:
      'This report shows exactly what changed and by how much. For every 100,000 searches, the improvement means thousands more people find what they\'re looking for on the first try. Export it, share it with your team, or use it as the starting point for the next tuning pass.',
    highlight: 'report',
    triggerEvent: 'report.ready',
    minDelay: 1000,
  },
];

interface WalkthroughState {
  active: boolean;
  currentStep: number;
  stepTimestamp: number;
  experimentsSeenCount: number;

  startWalkthrough: () => void;
  stopWalkthrough: () => void;
  nextStep: () => void;
  prevStep: () => void;
  goToStep: (step: number) => void;
  handleEvent: (eventType: string) => void;
}

export const useWalkthroughStore = create<WalkthroughState>((set, get) => ({
  active: false,
  currentStep: 0,
  stepTimestamp: 0,
  experimentsSeenCount: 0,

  startWalkthrough: () =>
    set({ active: true, currentStep: 0, stepTimestamp: Date.now(), experimentsSeenCount: 0 }),

  stopWalkthrough: () =>
    set({ active: false, currentStep: 0, experimentsSeenCount: 0 }),

  nextStep: () => {
    const { currentStep } = get();
    if (currentStep < WALKTHROUGH_STEPS.length - 1) {
      set({ currentStep: currentStep + 1, stepTimestamp: Date.now() });
    }
  },

  prevStep: () => {
    const { currentStep } = get();
    if (currentStep > 0) {
      set({ currentStep: currentStep - 1, stepTimestamp: Date.now() });
    }
  },

  goToStep: (step: number) => {
    if (step >= 0 && step < WALKTHROUGH_STEPS.length) {
      set({ currentStep: step, stepTimestamp: Date.now() });
    }
  },

  handleEvent: (eventType: string) => {
    const { active, currentStep, stepTimestamp, experimentsSeenCount } = get();
    if (!active) return;

    const nextStepIndex = currentStep + 1;
    if (nextStepIndex >= WALKTHROUGH_STEPS.length) return;

    const nextStep = WALKTHROUGH_STEPS[nextStepIndex];
    if (!nextStep.triggerEvent) return;

    // Track experiment count
    let newExpCount = experimentsSeenCount;
    if (eventType === 'experiment.completed') {
      newExpCount = experimentsSeenCount + 1;
    }

    // Check if this event matches the next step's trigger
    const triggerMatches = nextStep.triggerEvent === eventType;
    if (!triggerMatches) {
      if (newExpCount !== experimentsSeenCount) {
        set({ experimentsSeenCount: newExpCount });
      }
      return;
    }

    // Check minimum delay
    const elapsed = Date.now() - stepTimestamp;
    const minDelay = nextStep.minDelay ?? 0;
    if (elapsed < minDelay) {
      // Schedule the advance after the remaining delay
      const remaining = minDelay - elapsed;
      setTimeout(() => {
        const current = get();
        if (current.active && current.currentStep === currentStep) {
          set({
            currentStep: nextStepIndex,
            stepTimestamp: Date.now(),
            experimentsSeenCount: newExpCount,
          });
        }
      }, remaining);
      return;
    }

    set({
      currentStep: nextStepIndex,
      stepTimestamp: Date.now(),
      experimentsSeenCount: newExpCount,
    });
  },
}));
