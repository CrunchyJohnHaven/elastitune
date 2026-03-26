import React from 'react';
import { useAppStore } from '@/store/useAppStore';
import { PANEL_BORDER, PANEL_BG, ACCENT_BLUE } from '@/lib/theme';

/* ──────────────────────────────────────────────
   "How It Works" — in-app mission briefing panel
   Replaces the right rail when toggled.
   ────────────────────────────────────────────── */

function Glyph({ children, color }: { children: string; color: string }) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: 22,
        height: 22,
        borderRadius: '50%',
        background: `${color}18`,
        border: `1px solid ${color}40`,
        fontSize: 11,
        flexShrink: 0,
        marginRight: 8,
      }}
    >
      {children}
    </span>
  );
}

function Section({
  icon,
  iconColor,
  title,
  children,
}: {
  icon: string;
  iconColor: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div style={{ marginBottom: 20 }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          marginBottom: 8,
        }}
      >
        <Glyph color={iconColor}>{icon}</Glyph>
        <span
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            color: iconColor,
          }}
        >
          {title}
        </span>
      </div>
      <div
        style={{
          fontFamily: 'Inter, sans-serif',
          fontSize: 12,
          lineHeight: 1.65,
          color: '#9AA4B2',
          paddingLeft: 30,
        }}
      >
        {children}
      </div>
    </div>
  );
}

function KeyValue({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        padding: '4px 0',
        borderBottom: '1px solid rgba(255,255,255,0.04)',
      }}
    >
      <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#6B7480' }}>
        {label}
      </span>
      <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#C5CDD8' }}>
        {value}
      </span>
    </div>
  );
}

export default function ExplainerPanel() {
  const toggleExplainer = useAppStore(state => state.toggleExplainer);
  const metrics = useAppStore(state => state.runSnapshot?.metrics);
  const stage = useAppStore(state => state.runSnapshot?.stage ?? 'idle');
  const experimentsRun = metrics?.experimentsRun ?? 0;
  const kept = metrics?.improvementsKept ?? 0;

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
        overflow: 'hidden',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '14px 16px',
          borderBottom: `1px solid ${PANEL_BORDER}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexShrink: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 14 }}>?</span>
          <span
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 10,
              fontWeight: 700,
              letterSpacing: '0.14em',
              textTransform: 'uppercase',
              color: ACCENT_BLUE,
            }}
          >
            How It Works
          </span>
        </div>
        <button
          onClick={toggleExplainer}
          style={{
            background: 'rgba(255,255,255,0.06)',
            border: `1px solid ${PANEL_BORDER}`,
            borderRadius: 4,
            color: '#9AA4B2',
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 9,
            padding: '4px 10px',
            cursor: 'pointer',
            letterSpacing: '0.06em',
            transition: 'background 0.15s',
          }}
          onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.1)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)'; }}
        >
          Back to Dashboard
        </button>
      </div>

      {/* Scrollable content */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '20px 16px',
          scrollbarWidth: 'thin',
          scrollbarColor: 'rgba(255,255,255,0.08) transparent',
        }}
      >
        {/* Hero narrative */}
        <div
          style={{
            marginBottom: 24,
            padding: '14px',
            background: 'rgba(77,163,255,0.04)',
            border: `1px solid rgba(77,163,255,0.15)`,
            borderRadius: 8,
          }}
        >
          <p
            style={{
              fontFamily: 'Inter, sans-serif',
              fontSize: 13,
              lineHeight: 1.7,
              color: '#C5CDD8',
              margin: 0,
            }}
          >
            ElastiTune is <strong style={{ color: '#EEF3FF' }}>optimizing your search engine in real time</strong>.
            It runs dozens of A/B experiments against your Elasticsearch index, testing different
            configuration tweaks, and keeps only the changes that measurably improve search quality.
          </p>
        </div>

        {/* What's happening right now */}
        <Section icon="1" iconColor={ACCENT_BLUE} title="What's Happening Right Now">
          {stage === 'running' ? (
            <>
              The optimizer has run <strong style={{ color: '#EEF3FF' }}>{experimentsRun} experiments</strong> so
              far. Each one tests a specific change — like boosting title matches, adding phrase matching,
              or adjusting how many words need to match. Of those, <strong style={{ color: '#4ADE80' }}>{kept} improved
              results</strong> and were kept. The rest were reverted.
            </>
          ) : stage === 'completed' ? (
            <>
              Optimization is <strong style={{ color: '#4ADE80' }}>complete</strong>. The optimizer
              ran {experimentsRun} experiments and found {kept} improvements. View the report
              for the full recommended configuration.
            </>
          ) : (
            <>
              Waiting for the optimization run to begin. Once started, you'll see experiments
              stream in here in real time.
            </>
          )}
        </Section>

        {/* The Visualization */}
        <Section icon="2" iconColor="#7CE7FF" title="The Visualization">
          Each <strong style={{ color: '#EEF3FF' }}>colored dot</strong> is a simulated user persona
          — a SOC Analyst, a CISO, a Threat Hunter — each with their own typical search queries.
          When a dot <strong style={{ color: '#4DA3FF' }}>fires a beam</strong> toward the center,
          that persona is running a search against the current configuration.{' '}
          <strong style={{ color: '#4ADE80' }}>Green flashes</strong> mean they found what they needed.{' '}
          <strong style={{ color: '#FB7185' }}>Red</strong> means they didn't.{' '}
          <strong style={{ color: '#FBBF24' }}>Amber</strong> means partial results.
          <br /><br />
          The <strong style={{ color: '#EEF3FF' }}>wave ripples</strong> from the center indicate an
          experiment was just evaluated — green for kept, red for reverted.
          <strong style={{ color: '#9AA4B2' }}> Floating query text</strong> shows the actual searches
          being tested.
        </Section>

        {/* Experiment Stream */}
        <Section icon="3" iconColor="#4ADE80" title="Experiment Stream (Left Panel)">
          Every row is one optimization attempt. The system generates a{' '}
          <strong style={{ color: '#EEF3FF' }}>hypothesis</strong> (e.g., "Stronger title weighting will help
          exact incident lookups"), makes the change, evaluates it against{' '}
          <strong style={{ color: '#EEF3FF' }}>127 test queries</strong>, and either keeps or reverts it.
          <br /><br />
          <span style={{ color: '#4ADE80' }}>KEPT</span> = search quality improved.{' '}
          <span style={{ color: '#FB7185' }}>REVERTED</span> = it made things worse.
        </Section>

        {/* How Quality Is Measured */}
        <Section icon="4" iconColor="#FBBF24" title="How Quality Is Measured">
          <strong style={{ color: '#EEF3FF' }}>nDCG@10</strong> (Normalized Discounted Cumulative Gain)
          is the gold standard for ranking quality. It measures: <em>"Are the most relevant documents
          appearing in the top 10 results, in the right order?"</em>
          <br /><br />
          A score of <span style={{ color: '#FB7185' }}>0.41</span> means search results are mediocre — relevant
          docs exist but aren't surfacing well. A score of <span style={{ color: '#4ADE80' }}>0.55+</span> means
          significantly better ranking — the right answers are consistently near the top.
        </Section>

        {/* What Gets Tuned */}
        <Section icon="5" iconColor="#A78BFA" title="What Gets Tuned">
          The optimizer explores a parameter space including:
          <div style={{ marginTop: 8 }}>
            <KeyValue label="Field boosts" value="title, message, description" />
            <KeyValue label="Match type" value="best_fields, cross_fields, phrase" />
            <KeyValue label="Phrase boost" value="0.0 → 3.0" />
            <KeyValue label="Minimum match" value="50% → 100%" />
            <KeyValue label="Fuzziness" value="OFF / AUTO" />
            <KeyValue label="Tie breaker" value="0.0 → 1.0" />
            <KeyValue label="Lexical/vector weight" value="0.0 → 1.0" />
            <KeyValue label="Vector candidates" value="50 → 500" />
            <KeyValue label="RRF rank constant" value="1 → 100" />
          </div>
        </Section>

        {/* Under the Hood */}
        <Section icon="6" iconColor="#FB7185" title="Under the Hood">
          ElastiTune uses a <strong style={{ color: '#EEF3FF' }}>greedy hill-climbing optimizer</strong>.
          Starting from the current search configuration, it makes one change at a time, measures the
          effect, and keeps the change only if nDCG@10 improves by at least +0.3%. This conservative
          approach avoids overfitting while still finding significant gains.
          <br /><br />
          Each experiment takes the full evaluation set, runs both the baseline and candidate queries,
          computes nDCG@10 for each, and compares. No training data is needed — just the index itself.
        </Section>

        {/* Personas */}
        <Section icon="7" iconColor="#F472B6" title="The Personas">
          The 24 personas represent different user archetypes that would search this index in
          real life. Each has their own set of typical queries and success criteria. For a security
          index: a <strong style={{ color: '#EEF3FF' }}>SOC Analyst</strong> searches for specific
          CVE IDs, a <strong style={{ color: '#EEF3FF' }}>Threat Hunter</strong> looks for lateral
          movement patterns, a <strong style={{ color: '#EEF3FF' }}>CISO</strong> wants executive
          risk summaries.
          <br /><br />
          As the optimizer improves the search configuration, you'll see persona success rates climb
          — the right results start appearing for everyone's queries, not just a few.
        </Section>

        {/* Bottom */}
        <div
          style={{
            marginTop: 12,
            padding: '12px',
            background: 'rgba(255,255,255,0.02)',
            borderRadius: 6,
            border: `1px solid ${PANEL_BORDER}`,
            textAlign: 'center',
          }}
        >
          <span
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 9,
              color: '#6B7480',
              letterSpacing: '0.06em',
            }}
          >
            Built with ElastiTune — Autonomous Search Optimization
          </span>
        </div>
      </div>
    </div>
  );
}
