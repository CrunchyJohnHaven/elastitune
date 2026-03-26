import type { PersonaViewModel, ExperimentRecord } from '@/types/contracts';

// Seed personas for the animated preview on connect screen
export const PREVIEW_PERSONAS: PersonaViewModel[] = [
  {
    id: 'prev_0', name: 'Maya Chen', role: 'SOC Analyst', department: 'Security',
    archetype: 'SOC Analyst', goal: 'Investigate alerts', orbit: 0, colorSeed: 13,
    queries: ['lateral movement smb', 'failed auth admin'],
    state: 'idle', successRate: 0.72, totalSearches: 45, successes: 32, partials: 8,
    failures: 5, angle: 0.52, speed: 0.08, radius: 120, pulseUntil: null, reactUntil: null,
    lastQuery: 'lateral movement smb east west', lastResultRank: 1,
  },
  {
    id: 'prev_1', name: 'Jordan Price', role: 'Threat Hunter', department: 'Threat Intel',
    archetype: 'Threat Hunter', goal: 'Hunt APT', orbit: 1, colorSeed: 50,
    queries: ['c2 beacon dns', 'credential lsass'],
    state: 'idle', successRate: 0.61, totalSearches: 38, successes: 23, partials: 10,
    failures: 5, angle: 1.8, speed: 0.10, radius: 172, pulseUntil: null, reactUntil: null,
    lastQuery: 'c2 beacon dns exfil', lastResultRank: 2,
  },
  {
    id: 'prev_2', name: 'Elena Ortiz', role: 'Detection Engineer', department: 'SecEng',
    archetype: 'Detection Engineer', goal: 'Tune detection rules', orbit: 2, colorSeed: 87,
    queries: ['detection rule fidelity', 'sigma rule edr'],
    state: 'idle', successRate: 0.55, totalSearches: 29, successes: 16, partials: 8,
    failures: 5, angle: 3.2, speed: 0.07, radius: 224, pulseUntil: null, reactUntil: null,
    lastQuery: 'detection coverage mitre', lastResultRank: 3,
  },
  {
    id: 'prev_3', name: 'Samir Patel', role: 'Incident Commander', department: 'CISO',
    archetype: 'Incident Commander', goal: 'Manage incidents', orbit: 3, colorSeed: 124,
    queries: ['incident timeline', 'blast radius'],
    state: 'idle', successRate: 0.68, totalSearches: 22, successes: 15, partials: 4,
    failures: 3, angle: 4.7, speed: 0.09, radius: 276, pulseUntil: null, reactUntil: null,
    lastQuery: 'incident timeline reconstruction', lastResultRank: 1,
  },
  {
    id: 'prev_4', name: 'Nora Kim', role: 'Vulnerability Analyst', department: 'VulnMgmt',
    archetype: 'Vulnerability Analyst', goal: 'Track CVEs', orbit: 4, colorSeed: 161,
    queries: ['critical cve unpatched', 'cvss 9 exploitable'],
    state: 'idle', successRate: 0.59, totalSearches: 17, successes: 10, partials: 4,
    failures: 3, angle: 5.5, speed: 0.11, radius: 328, pulseUntil: null, reactUntil: null,
    lastQuery: 'critical cve unpatched servers', lastResultRank: 2,
  },
];

export const PREVIEW_EXPERIMENTS: Partial<ExperimentRecord>[] = [
  {
    experimentId: 1, hypothesis: 'Stronger title weighting improves exact lookups',
    change: { path: 'lexicalFields[0].boost', before: 3.0, after: 4.0, label: 'title boost 3.0 \u2192 4.0' },
    baselineScore: 0.412, candidateScore: 0.428, deltaAbsolute: 0.016, deltaPercent: 3.88,
    decision: 'kept', durationMs: 2341,
  },
  {
    experimentId: 2, hypothesis: 'Cross-fields matching improves multi-field recall',
    change: { path: 'multiMatchType', before: 'best_fields', after: 'cross_fields', label: 'multiMatchType best_fields \u2192 cross_fields' },
    baselineScore: 0.428, candidateScore: 0.421, deltaAbsolute: -0.007, deltaPercent: -1.63,
    decision: 'reverted', durationMs: 1987,
  },
  {
    experimentId: 3, hypothesis: 'Phrase boost rewards exact term sequences',
    change: { path: 'phraseBoost', before: 0.0, after: 1.0, label: 'phraseBoost 0.0 \u2192 1.0' },
    baselineScore: 0.428, candidateScore: 0.441, deltaAbsolute: 0.013, deltaPercent: 3.04,
    decision: 'kept', durationMs: 2104,
  },
];
