import React from 'react';
import { useAppStore } from '@/store/useAppStore';
import { PANEL_BORDER, PANEL_BG, ACCENT_BLUE } from '@/lib/theme';

/* ──────────────────────────────────────────────
   "How It Works" — live results + mission briefing panel
   Shows real data from the current run.
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

function ScoreBar({ label, score, maxScore = 1.0 }: { label: string; score: number; maxScore?: number }) {
  const pct = Math.min((score / maxScore) * 100, 100);
  const color = score >= 0.8 ? '#4ADE80' : score >= 0.5 ? '#FBBF24' : '#FB7185';

  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
        <span
          style={{
            fontFamily: 'Inter, sans-serif',
            fontSize: 11,
            color: '#C5CDD8',
          }}
        >
          {label}
        </span>
        <span
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 11,
            fontWeight: 600,
            color,
          }}
        >
          {score.toFixed(3)}
        </span>
      </div>
      <div
        style={{
          height: 4,
          borderRadius: 2,
          background: 'rgba(255,255,255,0.06)',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            height: '100%',
            width: `${pct}%`,
            borderRadius: 2,
            background: color,
            transition: 'width 0.5s ease',
          }}
        />
      </div>
    </div>
  );
}

export default function ExplainerPanel() {
  const toggleExplainer = useAppStore(state => state.toggleExplainer);
  const snapshot = useAppStore(state => state.runSnapshot);
  const metrics = snapshot?.metrics;
  const stage = snapshot?.stage ?? 'idle';
  const experiments = snapshot?.experiments ?? [];
  const summary = snapshot?.summary;
  const personas = snapshot?.personas ?? [];
  const searchProfile = snapshot?.searchProfile;
  const recommendedProfile = snapshot?.recommendedProfile;

  const experimentsRun = (metrics?.experimentsRun ?? 0) + (metrics?.priorExperimentsRun ?? 0);
  const kept = (metrics?.improvementsKept ?? 0) + (metrics?.priorImprovementsKept ?? 0);
  // When continuing, show the ORIGINAL baseline so the user sees cumulative progress
  const originalBaseline = metrics?.originalBaselineScore;
  const baselineScore = originalBaseline != null ? originalBaseline : (metrics?.baselineScore ?? 0);
  const bestScore = metrics?.bestScore ?? 0;
  const improvementPct = metrics?.improvementPct ?? 0;
  const isContinued = originalBaseline != null;
  const keptExperiments = experiments.filter(e => e.decision === 'kept');

  // Build a summary of what actually changed
  const profileChanges: { label: string; from: string; to: string }[] = [];
  if (searchProfile && recommendedProfile) {
    if (searchProfile.multiMatchType !== recommendedProfile.multiMatchType) {
      profileChanges.push({
        label: 'Match strategy',
        from: searchProfile.multiMatchType,
        to: recommendedProfile.multiMatchType,
      });
    }
    // Compare field boosts
    const baseBoosts = Object.fromEntries(
      searchProfile.lexicalFields.map(f => [f.field, f.boost])
    );
    const bestBoosts = Object.fromEntries(
      recommendedProfile.lexicalFields.map(f => [f.field, f.boost])
    );
    for (const field of Object.keys(bestBoosts)) {
      const from = baseBoosts[field] ?? 1.0;
      const to = bestBoosts[field];
      if (from !== to) {
        profileChanges.push({
          label: `${field} boost`,
          from: String(from),
          to: String(to),
        });
      }
    }
    if (searchProfile.tieBreaker !== recommendedProfile.tieBreaker) {
      profileChanges.push({
        label: 'Tie breaker',
        from: String(searchProfile.tieBreaker),
        to: String(recommendedProfile.tieBreaker),
      });
    }
    if (searchProfile.phraseBoost !== recommendedProfile.phraseBoost) {
      profileChanges.push({
        label: 'Phrase boost',
        from: String(searchProfile.phraseBoost),
        to: String(recommendedProfile.phraseBoost),
      });
    }
    if (searchProfile.fuzziness !== recommendedProfile.fuzziness) {
      profileChanges.push({
        label: 'Fuzziness',
        from: searchProfile.fuzziness,
        to: recommendedProfile.fuzziness,
      });
    }
    if (searchProfile.minimumShouldMatch !== recommendedProfile.minimumShouldMatch) {
      profileChanges.push({
        label: 'Min should match',
        from: searchProfile.minimumShouldMatch,
        to: recommendedProfile.minimumShouldMatch,
      });
    }
  }

  // Get unique persona queries that were tested
  const sampleQueries = [...new Set(
    personas
      .flatMap(p => p.queries ?? [])
      .filter(q => q && q.length > 0)
  )].slice(0, 8);

  const indexName = summary?.indexName ?? 'your index';
  const docCount = summary?.docCount ?? 0;
  const textFields = summary?.primaryTextFields ?? [];
  const evalCount = summary?.baselineEvalCount ?? 0;
  const isPreRun = stage === 'idle' || stage === 'ready' || stage === 'starting' || (experimentsRun === 0 && stage !== 'completed');
  const panelTitle = isPreRun ? 'How It Works' : stage === 'completed' ? 'What We Found' : 'Live Analysis';

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
          <span style={{ fontSize: 14 }}>{'\u{1F50D}'}</span>
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
            {panelTitle}
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
        {isPreRun && (
          <>
            <div
              style={{
                marginBottom: 24,
                padding: '16px',
                background: 'rgba(77,163,255,0.04)',
                border: '1px solid rgba(77,163,255,0.14)',
                borderRadius: 8,
              }}
            >
              <p
                style={{
                  margin: 0,
                  fontFamily: 'Inter, sans-serif',
                  fontSize: 13,
                  lineHeight: 1.7,
                  color: '#C5CDD8',
                }}
              >
                ElastiTune starts from your current search setup, runs a controlled benchmark against known-good queries,
                and only keeps parameter changes that measurably improve ranking quality.
              </p>
            </div>

            <Section icon="1" iconColor={ACCENT_BLUE} title="Inspect">
              ElastiTune reads the index, finds the main searchable fields, samples documents, and builds a benchmark set of realistic test searches.
            </Section>
            <Section icon="2" iconColor="#4ADE80" title="Experiment">
              The optimizer tests one ranking change at a time, measures the impact on the full query set, and immediately reverts anything that hurts results.
            </Section>
            <Section icon="3" iconColor="#FBBF24" title="Explain">
              As the run progresses, this panel switches from the mission briefing to live findings, then ends with the specific changes that helped.
            </Section>
          </>
        )}

        {/* Hero — The Headline Result */}
        <div
          style={{
            marginBottom: 24,
            padding: '16px',
            background: improvementPct > 5
              ? 'rgba(74,222,128,0.06)'
              : 'rgba(77,163,255,0.04)',
            border: `1px solid ${
              improvementPct > 5
                ? 'rgba(74,222,128,0.2)'
                : 'rgba(77,163,255,0.15)'
            }`,
            borderRadius: 8,
          }}
        >
          {improvementPct > 1 ? (
            <>
              <div
                style={{
                  fontFamily: 'Inter, sans-serif',
                  fontSize: 22,
                  fontWeight: 700,
                  color: '#4ADE80',
                  marginBottom: 6,
                }}
              >
                +{improvementPct.toFixed(1)}% improvement
              </div>
              <p
                style={{
                  fontFamily: 'Inter, sans-serif',
                  fontSize: 13,
                  lineHeight: 1.6,
                  color: '#C5CDD8',
                  margin: 0,
                }}
              >
                ElastiTune improved search quality on{' '}
                <strong style={{ color: '#EEF3FF' }}>{indexName}</strong> ({docCount.toLocaleString()} docs)
                from <span style={{ color: '#FB7185', fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}>{baselineScore.toFixed(3)}</span> to{' '}
                <span style={{ color: '#4ADE80', fontFamily: 'JetBrains Mono, monospace', fontSize: 12 }}>{bestScore.toFixed(3)}</span> nDCG@10
                across {evalCount} test queries.{isContinued && ' (cumulative across runs)'}
              </p>
            </>
          ) : stage === 'running' ? (
            <p
              style={{
                fontFamily: 'Inter, sans-serif',
                fontSize: 13,
                lineHeight: 1.7,
                color: '#C5CDD8',
                margin: 0,
              }}
            >
              ElastiTune is <strong style={{ color: '#EEF3FF' }}>optimizing {indexName}</strong> in real time,
              testing different search configurations against {evalCount} test queries
              to find measurable improvements.
            </p>
          ) : null}
        </div>

        {/* Score comparison */}
        {!isPreRun && baselineScore > 0 && (
          <Section icon="1" iconColor={ACCENT_BLUE} title="Search Quality Score">
            <ScoreBar label={isContinued ? "Original baseline" : "Baseline (before)"} score={baselineScore} />
            <ScoreBar label={stage === 'running' ? 'Current best' : 'After optimization'} score={bestScore} />
            <div
              style={{
                marginTop: 6,
                fontFamily: 'Inter, sans-serif',
                fontSize: 11,
                color: '#6B7480',
                lineHeight: 1.5,
              }}
            >
              <strong style={{ color: '#EEF3FF' }}>nDCG@10</strong> measures whether the most relevant
              documents appear in the top 10 results. 1.0 = perfect ranking. Tested against {evalCount} real queries.
            </div>
          </Section>
        )}

        {/* What Changed — Tangible Profile Diffs */}
        {!isPreRun && profileChanges.length > 0 && (
          <Section icon="2" iconColor="#4ADE80" title="What We Changed">
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: 6,
                marginBottom: 8,
              }}
            >
              {profileChanges.map((change, i) => (
                <div
                  key={i}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    padding: '6px 8px',
                    background: 'rgba(255,255,255,0.03)',
                    border: '1px solid rgba(255,255,255,0.06)',
                    borderRadius: 6,
                  }}
                >
                  <span
                    style={{
                      fontFamily: 'Inter, sans-serif',
                      fontSize: 11,
                      color: '#9AA4B2',
                      flex: 1,
                    }}
                  >
                    {change.label}
                  </span>
                  <span
                    style={{
                      fontFamily: 'JetBrains Mono, monospace',
                      fontSize: 10,
                      color: '#FB7185',
                    }}
                  >
                    {change.from}
                  </span>
                  <span style={{ fontSize: 10, color: '#4B5563' }}>{'\u2192'}</span>
                  <span
                    style={{
                      fontFamily: 'JetBrains Mono, monospace',
                      fontSize: 10,
                      color: '#4ADE80',
                      fontWeight: 600,
                    }}
                  >
                    {change.to}
                  </span>
                </div>
              ))}
            </div>
            <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 11, color: '#6B7480', lineHeight: 1.5 }}>
              {profileChanges.some(c => c.label.includes('boost'))
                ? 'Field boost changes reweight which text fields matter most for ranking. A lower boost on a noisy field (like description) reduces irrelevant matches.'
                : 'These configuration changes directly affect how Elasticsearch ranks search results.'}
            </div>
          </Section>
        )}

        {/* Kept Experiments — What Actually Worked */}
        {!isPreRun && keptExperiments.length > 0 && (
          <Section icon="3" iconColor="#7CE7FF" title="Experiments That Worked">
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: 6,
                marginBottom: 8,
              }}
            >
              {keptExperiments.slice(-5).map((exp) => (
                <div
                  key={exp.experimentId}
                  style={{
                    padding: '8px 10px',
                    background: 'rgba(74,222,128,0.04)',
                    border: '1px solid rgba(74,222,128,0.12)',
                    borderRadius: 6,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                    <span
                      style={{
                        fontFamily: 'JetBrains Mono, monospace',
                        fontSize: 9,
                        color: '#6B7480',
                      }}
                    >
                      Experiment #{exp.experimentId}
                    </span>
                    <span
                      style={{
                        fontFamily: 'JetBrains Mono, monospace',
                        fontSize: 11,
                        fontWeight: 700,
                        color: '#4ADE80',
                      }}
                    >
                      +{exp.deltaPercent.toFixed(1)}%
                    </span>
                  </div>
                  <div
                    style={{
                      fontFamily: 'Inter, sans-serif',
                      fontSize: 11,
                      color: '#C5CDD8',
                      lineHeight: 1.4,
                    }}
                  >
                    {exp.hypothesis}
                  </div>
                  <div
                    style={{
                      fontFamily: 'JetBrains Mono, monospace',
                      fontSize: 10,
                      color: '#6B7480',
                      marginTop: 3,
                    }}
                  >
                    {(exp.beforeScore ?? exp.baselineScore ?? 0).toFixed(4)} {'\u2192'} {exp.candidateScore.toFixed(4)} nDCG@10
                  </div>
                </div>
              ))}
            </div>
          </Section>
        )}

        {/* What We Tested */}
        {!isPreRun && sampleQueries.length > 0 && (
          <Section icon="4" iconColor="#FBBF24" title="Test Queries Used">
            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: 5,
                marginBottom: 8,
              }}
            >
              {sampleQueries.map((q, i) => (
                <span
                  key={i}
                  style={{
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: 10,
                    color: '#C5CDD8',
                    background: 'rgba(255,255,255,0.04)',
                    border: '1px solid rgba(255,255,255,0.08)',
                    borderRadius: 4,
                    padding: '3px 8px',
                  }}
                >
                  "{q}"
                </span>
              ))}
            </div>
            <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 11, color: '#6B7480', lineHeight: 1.5 }}>
              Each experiment is evaluated against {evalCount > 0 ? `all ${evalCount}` : 'these'} queries.
              We compare the full ranked results against known relevant documents and compute nDCG@10.
            </div>
          </Section>
        )}

        {/* Fields being searched */}
        {!isPreRun && textFields.length > 0 && (
          <Section icon="5" iconColor="#A78BFA" title="Fields Being Searched">
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                gap: 4,
                marginBottom: 8,
              }}
            >
              {(recommendedProfile?.lexicalFields ?? searchProfile?.lexicalFields ?? []).map((f, i) => (
                <div
                  key={i}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '5px 8px',
                    background: 'rgba(255,255,255,0.03)',
                    borderRadius: 5,
                    border: '1px solid rgba(255,255,255,0.05)',
                  }}
                >
                  <span
                    style={{
                      fontFamily: 'JetBrains Mono, monospace',
                      fontSize: 11,
                      color: '#EEF3FF',
                    }}
                  >
                    {f.field}
                  </span>
                  <span
                    style={{
                      fontFamily: 'JetBrains Mono, monospace',
                      fontSize: 11,
                      color: '#7CE7FF',
                      fontWeight: 600,
                    }}
                  >
                    {f.boost}x
                  </span>
                </div>
              ))}
            </div>
            <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 11, color: '#6B7480', lineHeight: 1.5 }}>
              Higher boost = more weight in ranking. ElastiTune finds the optimal weight for each field so
              relevant documents rank higher.
            </div>
          </Section>
        )}

        {/* Run progress */}
        {!isPreRun && (
        <Section icon="6" iconColor="#FB7185" title="Optimization Progress">
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: 6,
              marginBottom: 8,
            }}
          >
            {[
              { label: 'Experiments run', value: String(experimentsRun), color: '#EEF3FF' },
              { label: 'Improvements kept', value: String(kept), color: '#4ADE80' },
              { label: 'Reverted', value: String(experimentsRun - kept), color: '#FB7185' },
              { label: 'Success rate', value: kept > 0 ? `${((kept / Math.max(experimentsRun, 1)) * 100).toFixed(0)}%` : '—', color: '#FBBF24' },
            ].map((stat, i) => (
              <div
                key={i}
                style={{
                  padding: '8px',
                  background: 'rgba(255,255,255,0.02)',
                  border: '1px solid rgba(255,255,255,0.05)',
                  borderRadius: 6,
                }}
              >
                <div
                  style={{
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: 9,
                    color: '#6B7480',
                    marginBottom: 2,
                    textTransform: 'uppercase',
                  }}
                >
                  {stat.label}
                </div>
                <div
                  style={{
                    fontFamily: 'Inter, sans-serif',
                    fontSize: 16,
                    fontWeight: 700,
                    color: stat.color,
                  }}
                >
                  {stat.value}
                </div>
              </div>
            ))}
          </div>
          <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 11, color: '#6B7480', lineHeight: 1.5 }}>
            ElastiTune uses greedy hill-climbing: it makes one change at a time, keeps it only if nDCG improves,
            and reverts otherwise. This avoids overfitting while finding real gains.
          </div>
        </Section>
        )}

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
            ElastiTune — Autonomous Search Optimization for Elasticsearch
          </span>
        </div>
      </div>
    </div>
  );
}
