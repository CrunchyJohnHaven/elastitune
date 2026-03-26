import React, { useEffect, useRef } from 'react';
import { useAppStore } from '@/store/useAppStore';
import IndexSummaryMiniCard from '@/components/run/IndexSummaryMiniCard';
import PersonaList from '@/components/run/PersonaList';
import PersonaDetailCard from '@/components/run/PersonaDetailCard';
import CompressionCard from '@/components/run/CompressionCard';
import HeroMetrics from '@/components/run/HeroMetrics';
import type { PersonaActivityEntry, PersonaViewModel } from '@/types/contracts';
import { PANEL_BORDER, PANEL_BG, FONT_MONO, TEXT_DIM } from '@/lib/theme';

const EMPTY_PERSONAS: PersonaViewModel[] = [];
const EMPTY_ACTIVITY: PersonaActivityEntry[] = [];

function PostureStat({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div
      style={{
        border: `1px solid ${PANEL_BORDER}`,
        borderRadius: 8,
        background: 'rgba(255,255,255,0.02)',
        padding: '8px 10px',
      }}
    >
      <div
        style={{
          fontFamily: FONT_MONO,
          fontSize: 9,
          color: TEXT_DIM,
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          marginBottom: 4,
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: FONT_MONO,
          fontSize: 14,
          fontWeight: 600,
          color: color ?? '#EEF3FF',
        }}
      >
        {value}
      </div>
    </div>
  );
}

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        padding: '10px 14px',
        borderBottom: `1px solid ${PANEL_BORDER}`,
        flexShrink: 0,
      }}
    >
      <span
        style={{
          fontFamily: FONT_MONO,
          fontSize: 10,
          fontWeight: 600,
          letterSpacing: '0.14em',
          textTransform: 'uppercase',
          color: TEXT_DIM,
        }}
      >
        {children}
      </span>
    </div>
  );
}

export default function RightRail() {
  const runId = useAppStore(state => state.runSnapshot?.runId ?? null);
  const summary = useAppStore(state => state.runSnapshot?.summary);
  const metrics = useAppStore(state => state.runSnapshot?.metrics);
  const mode = useAppStore(state => state.runSnapshot?.mode ?? 'demo');
  const stage = useAppStore(state => state.runSnapshot?.stage ?? 'idle');
  const searchProfile = useAppStore(state => state.runSnapshot?.searchProfile);
  const recommendedProfile = useAppStore(state => state.runSnapshot?.recommendedProfile);
  const personas = useAppStore(state => state.runSnapshot?.personas) ?? EMPTY_PERSONAS;
  const compression = useAppStore(state => state.runSnapshot?.compression);
  const startedAt = useAppStore(state => state.runSnapshot?.startedAt);
  const completedAt = useAppStore(state => state.runSnapshot?.completedAt);
  const selectedPersonaId = useAppStore(state => state.selectedPersonaId);
  const personaActivityById = useAppStore(state => state.personaActivityById);
  const setSelectedPersona = useAppStore(state => state.setSelectedPersona);
  const cumulativeCountsRef = useRef({ runId: null as string | null, resolved: 0, missed: 0 });

  const currentResolvedCount = personas.reduce(
    (sum, persona) => sum + persona.successes + persona.partials,
    0
  );
  const currentMissedCount = personas.reduce((sum, persona) => sum + persona.failures, 0);

  useEffect(() => {
    if (!runId) return;
    if (cumulativeCountsRef.current.runId !== runId) {
      cumulativeCountsRef.current = {
        runId,
        resolved: currentResolvedCount,
        missed: currentMissedCount,
      };
      return;
    }

    cumulativeCountsRef.current = {
      runId,
      resolved: Math.max(cumulativeCountsRef.current.resolved, currentResolvedCount),
      missed: Math.max(cumulativeCountsRef.current.missed, currentMissedCount),
    };
  }, [runId, currentResolvedCount, currentMissedCount]);

  if (!summary || !metrics || !searchProfile || !recommendedProfile || !compression) {
    return (
      <div
        style={{
          width: 360,
          flexShrink: 0,
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          background: PANEL_BG,
          borderLeft: `1px solid ${PANEL_BORDER}`,
          backdropFilter: 'blur(12px)',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 12,
        }}
      >
        <div
          style={{
            width: 28,
            height: 28,
            border: '2px solid rgba(255,255,255,0.08)',
            borderTopColor: '#4DA3FF',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
          }}
        />
        <span
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 10,
            color: '#6B7480',
            textTransform: 'uppercase',
            letterSpacing: '0.1em',
          }}
        >
          Loading telemetry…
        </span>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  const selectedPersona =
    personas.find(persona => persona.id === selectedPersonaId)
    ?? personas.find(persona => persona.state !== 'idle')
    ?? personas[0]
    ?? null;
  const selectedPersonaActivity = selectedPersona
    ? (personaActivityById[selectedPersona.id] ?? EMPTY_ACTIVITY)
    : EMPTY_ACTIVITY;
  // Persona state transitions happen instantly in backend batch, so 'searching' is never seen.
  // Count personas as "active" if they have non-idle state (recently searched).
  const activeCount = personas.filter(persona => persona.state !== 'idle' && persona.totalSearches > 0).length;
  const resolvedCount = Math.max(currentResolvedCount, cumulativeCountsRef.current.resolved);
  const missedCount = Math.max(currentMissedCount, cumulativeCountsRef.current.missed);
  const topDepartment = Object.entries(
    personas.reduce<Record<string, number>>((acc, persona) => {
      acc[persona.department] = (acc[persona.department] ?? 0) + 1;
      return acc;
    }, {})
  ).sort((a, b) => b[1] - a[1])[0];

  return (
    <div
      style={{
        width: 360,
        flexShrink: 0,
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        background: PANEL_BG,
        borderLeft: `1px solid ${PANEL_BORDER}`,
        backdropFilter: 'blur(12px)',
        overflowY: 'auto',
        overflowX: 'hidden',
        scrollbarWidth: 'thin',
        scrollbarColor: 'rgba(255,255,255,0.06) transparent',
      }}
    >
      {/* Section 1: Index Summary */}
      <div style={{ flexShrink: 0 }}>
        <SectionHeader>Index Info</SectionHeader>
        <IndexSummaryMiniCard
          summary={summary}
          metrics={metrics}
          mode={mode}
          profile={recommendedProfile ?? searchProfile}
          stage={stage}
          startedAt={startedAt}
          completedAt={completedAt}
        />
      </div>

      {/* Section 2: Score metrics / sparkline */}
      <div style={{ flexShrink: 0 }}>
        <SectionHeader>Score Timeline</SectionHeader>
        <HeroMetrics metrics={metrics} />
      </div>

      <div style={{ flexShrink: 0, borderBottom: `1px solid ${PANEL_BORDER}`, padding: '12px' }}>
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
            gap: 8,
          }}
        >
          <PostureStat label="Active" value={String(activeCount)} color="#4DA3FF" />
          <PostureStat label="Resolved" value={String(resolvedCount)} color="#4ADE80" />
          <PostureStat label="Missed" value={String(missedCount)} color="#FB7185" />
          <PostureStat label="Top Pod" value={topDepartment ? topDepartment[0] : '—'} />
        </div>
      </div>

      {/* Section 3: Focus persona */}
      <div style={{ flexShrink: 0, borderBottom: `1px solid ${PANEL_BORDER}` }}>
        <SectionHeader>Focus Persona</SectionHeader>
        <PersonaDetailCard
          persona={selectedPersona}
          activity={selectedPersonaActivity}
        />
      </div>

      {/* Section 4: Persona list */}
      <div
        style={{
          flexShrink: 0,
          borderBottom: `1px solid ${PANEL_BORDER}`,
        }}
      >
        <SectionHeader>
          Personas ({personas.length})
        </SectionHeader>
        <PersonaList
          personas={personas}
          selectedId={selectedPersonaId}
          onSelect={setSelectedPersona}
        />
      </div>

      {/* Section 5: Compression */}
      <div style={{ flexShrink: 0 }}>
        <SectionHeader>Vector Savings</SectionHeader>
        <CompressionCard compression={compression} />
      </div>
    </div>
  );
}
