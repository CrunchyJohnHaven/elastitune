import React, { useCallback, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { api } from '@/lib/api';
import { PANEL_BORDER } from '@/lib/theme';
import { useCommitteeStore } from '@/store/useCommitteeStore';
import ErrorBoundary from '@/components/ErrorBoundary';
import { useToast } from '@/components/ui/ToastProvider';
import { useViewportWidth } from '@/hooks/useViewportWidth';
import type { CommitteeEvaluationMode } from '@/types/committee';

function FieldLabel({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: 9,
        fontWeight: 700,
        letterSpacing: '0.14em',
        textTransform: 'uppercase',
        color: '#6B7480',
        marginBottom: 7,
      }}
    >
      {children}
    </div>
  );
}

function StepBadge({ n, label, active }: { n: number; label: string; active: boolean }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
      <div
        style={{
          width: 22,
          height: 22,
          borderRadius: '50%',
          flexShrink: 0,
          background: active ? '#4DA3FF' : 'rgba(255,255,255,0.06)',
          border: `1px solid ${active ? '#4DA3FF' : 'rgba(255,255,255,0.1)'}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: 10,
          fontWeight: 700,
          color: active ? '#05070B' : '#4B5563',
        }}
      >
        {n}
      </div>
      <span
        style={{
          fontFamily: 'Inter, sans-serif',
          fontSize: 11,
          color: active ? '#C5CDD8' : '#4B5563',
        }}
      >
        {label}
      </span>
    </div>
  );
}

const INDUSTRY_OPTIONS = [
  { value: 'auto', label: 'Auto-detect from document' },
  { value: 'government', label: 'Government / Public Sector' },
  { value: 'enterprise_tech', label: 'Enterprise Technology' },
  { value: 'financial_services', label: 'Financial Services' },
  { value: 'healthcare', label: 'Healthcare' },
  { value: 'general_enterprise', label: 'General Enterprise' },
];

const MODE_LABELS: Record<CommitteeEvaluationMode, string> = {
  full_committee: 'Full Committee',
  adversarial: 'Adversarial',
  champion_only: 'Champion Only',
};

export default function CommitteeScreen() {
  const navigate = useNavigate();
  const width = useViewportWidth();
  const toast = useToast();
  const { setConnectionId, setRunId, reset } = useCommitteeStore();

  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const [starting, setStarting] = useState(false);
  const [committeeDescription, setCommitteeDescription] = useState('');
  const [useSeedPersonas, setUseSeedPersonas] = useState(false);
  const [evaluationMode, setEvaluationMode] = useState<CommitteeEvaluationMode>('full_committee');
  const [industryProfileId, setIndustryProfileId] = useState('auto');
  const [doNoHarmFloor, setDoNoHarmFloor] = useState(-0.05);
  const [autoStopOnPlateau, setAutoStopOnPlateau] = useState(true);
  const [personaWeightingMode, setPersonaWeightingMode] = useState<'balanced' | 'authority' | 'skeptic_priority'>('authority');
  const [reactionMemoryWeight, setReactionMemoryWeight] = useState(0.25);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof api.connectCommittee>> | null>(null);
  const [error, setError] = useState<string | null>(null);

  const isStacked = width < 1220;
  const isNarrow = width < 860;
  const step = !file ? 1 : summary ? 3 : 2;

  const clearPreview = () => {
    setSummary(null);
    setConnectionId(null);
    setRunId(null);
    setError(null);
  };

  const updateFile = (nextFile: File | null) => {
    setFile(nextFile);
    clearPreview();
    if (nextFile) {
      toast.success(`Loaded ${nextFile.name}`);
    }
  };

  const handleDrop = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    setDragOver(false);
    const dropped = event.dataTransfer.files[0];
    if (dropped) {
      updateFile(dropped);
    }
  }, []);

  const connectCurrentDocument = useCallback(async () => {
    if (!file) {
      return null;
    }
    const response = await api.connectCommittee({
      file,
      evaluationMode,
      useSeedPersonas,
      committeeDescription,
      industryProfileId: industryProfileId === 'auto' ? undefined : industryProfileId,
    });
    setSummary(response);
    setConnectionId(response.connectionId);
    return response;
  }, [committeeDescription, evaluationMode, file, industryProfileId, setConnectionId, useSeedPersonas]);

  const handlePreview = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const response = await connectCurrentDocument();
      if (response) {
        toast.success(`Preview ready for ${response.summary.industryLabel}`);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to preview committee';
      setError(message);
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const handleStart = async () => {
    if (!file) return;
    setStarting(true);
    setError(null);
    try {
      const connection = summary ?? await connectCurrentDocument();
      if (!connection) {
        throw new Error('Document connection was not created');
      }
      const response = await api.startCommitteeRun(connection.connectionId, {
        maxRewrites: 30,
        durationMinutes: 4,
        autoStopOnPlateau,
        doNoHarmFloor,
        personaWeightingMode,
        reactionMemoryWeight,
      });
      setRunId(response.runId);
      toast.info('Committee run starting…');
      navigate(`/committee/run/${response.runId}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to start committee run';
      setError(message);
      setStarting(false);
      toast.error(message);
    }
  };

  const summaryWarnings = summary?.warnings ?? [];

  return (
    <ErrorBoundary title="Committee Setup Failed">
      <div
        style={{
          width: '100vw',
          minHeight: '100vh',
          background: '#05070B',
          color: '#EEF3FF',
          display: 'flex',
          flexDirection: isStacked ? 'column' : 'row',
        }}
      >
        <div
          style={{
            width: isStacked ? '100%' : 580,
            flexShrink: 0,
            padding: isNarrow ? '28px 20px 24px' : '40px 44px 48px',
            borderRight: isStacked ? 'none' : `1px solid ${PANEL_BORDER}`,
            borderBottom: isStacked ? `1px solid ${PANEL_BORDER}` : 'none',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, marginBottom: 28 }}>
              <div>
                <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 26, fontWeight: 700, lineHeight: 1.15 }}>
                  Simulated Buying Committee
                </div>
                <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#9AA4B2', marginTop: 7, lineHeight: 1.55, maxWidth: 460 }}>
                  Drop in a pitch or proposal, infer the room automatically, and watch the same ElastiTune loop optimize the document for consensus.
                </div>
              </div>
              <div style={{ display: 'flex', gap: 12, flexShrink: 0, marginTop: 4 }}>
                <Link
                  to="/committee/history"
                  style={{
                    color: '#9AA4B2',
                    fontFamily: 'Inter, sans-serif',
                    fontSize: 12,
                    textDecoration: 'none',
                  }}
                >
                  History
                </Link>
                <Link
                  to="/"
                  onClick={() => reset()}
                  style={{
                    color: '#4DA3FF',
                    fontFamily: 'Inter, sans-serif',
                    fontSize: 12,
                    textDecoration: 'none',
                  }}
                >
                  ← Search Mode
                </Link>
              </div>
            </div>

            <div style={{ display: 'flex', gap: 20, marginBottom: 22, flexWrap: 'wrap' }}>
              <StepBadge n={1} label="Upload" active={step >= 1} />
              <StepBadge n={2} label="Preview (Optional)" active={step >= 2} />
              <StepBadge n={3} label="Run Live" active={step >= 3} />
            </div>

            <div
              style={{
                marginBottom: 18,
                padding: '12px 14px',
                borderRadius: 12,
                background: 'rgba(77,163,255,0.06)',
                border: '1px solid rgba(77,163,255,0.15)',
                fontFamily: 'Inter, sans-serif',
                fontSize: 12,
                lineHeight: 1.5,
                color: '#CFE6FF',
              }}
            >
              Simplest path: choose a file and hit <span style={{ color: '#EEF3FF', fontWeight: 700 }}>Start Committee Run</span>. Preview is optional.
            </div>

            <div
              style={{
                padding: isNarrow ? 18 : 24,
                borderRadius: 16,
                background: 'rgba(10,14,20,0.72)',
                border: `1px solid ${PANEL_BORDER}`,
              }}
            >
              <div style={{ marginBottom: 18 }}>
                <FieldLabel>Document</FieldLabel>
                <div
                  onDragOver={(event) => {
                    event.preventDefault();
                    setDragOver(true);
                  }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={handleDrop}
                  onClick={() => document.getElementById('committee-file-input')?.click()}
                  style={{
                    padding: '22px 18px',
                    borderRadius: 12,
                    border: `1.5px dashed ${dragOver ? '#4DA3FF' : file ? 'rgba(74,222,128,0.35)' : 'rgba(255,255,255,0.12)'}`,
                    background: dragOver ? 'rgba(77,163,255,0.05)' : file ? 'rgba(74,222,128,0.04)' : 'rgba(5,7,11,0.6)',
                    cursor: 'pointer',
                    textAlign: 'center',
                    transition: 'all 0.2s',
                  }}
                >
                  <input
                    id="committee-file-input"
                    type="file"
                    accept=".pdf,.pptx,.docx,.txt,.md"
                    onChange={(event) => updateFile(event.target.files?.[0] ?? null)}
                    style={{ display: 'none' }}
                  />
                  {file ? (
                    <>
                      <div style={{ fontSize: 20, marginBottom: 4 }}>✓</div>
                      <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#4ADE80', fontWeight: 600 }}>
                        {file.name}
                      </div>
                      <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 11, color: '#9AA4B2', marginTop: 3 }}>
                        {(file.size / 1024).toFixed(0)} KB · Click to change
                      </div>
                    </>
                  ) : (
                    <>
                      <div style={{ fontSize: 24, marginBottom: 6, color: '#4B5563' }}>⬆</div>
                      <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#9AA4B2' }}>
                        Drag and drop or <span style={{ color: '#4DA3FF' }}>click to browse</span>
                      </div>
                      <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, color: '#4B5563', marginTop: 5, letterSpacing: '0.06em' }}>
                        PDF · PPTX · DOCX · TXT · MD
                      </div>
                    </>
                  )}
                </div>
              </div>

              <div style={{ marginBottom: 16 }}>
                <FieldLabel>Audience / Committee Input</FieldLabel>
                <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 11, color: '#6B7480', marginBottom: 7, lineHeight: 1.5 }}>
                  Paste the room if you know it. Otherwise leave this blank and the system will infer the best-fit buying committee from the document.
                </div>
                <textarea
                  value={committeeDescription}
                  onChange={(event) => {
                    setCommitteeDescription(event.target.value);
                    clearPreview();
                  }}
                  placeholder="Example:\nHartley Caldwell: CIO, final technical authority\nGeneral Counsel: legal domain owner, skeptical of AI overreach\nBudget Director: needs defensible ROI math"
                  rows={6}
                  style={{
                    width: '100%',
                    boxSizing: 'border-box',
                    borderRadius: 10,
                    border: `1px solid ${PANEL_BORDER}`,
                    background: 'rgba(5,7,11,0.8)',
                    color: '#EEF3FF',
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: 11,
                    lineHeight: 1.65,
                    padding: '12px 14px',
                    resize: 'vertical',
                    outline: 'none',
                  }}
                />
              </div>

              <label
                onClick={(event) => {
                  event.preventDefault();
                  setUseSeedPersonas((value) => !value);
                  clearPreview();
                }}
                style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14, cursor: 'pointer' }}
              >
                <div
                  style={{
                    width: 34,
                    height: 18,
                    borderRadius: 9,
                    background: useSeedPersonas ? '#4DA3FF' : 'rgba(255,255,255,0.12)',
                    position: 'relative',
                    flexShrink: 0,
                    transition: 'background 0.2s',
                  }}
                >
                  <div
                    style={{
                      position: 'absolute',
                      top: 3,
                      left: useSeedPersonas ? 19 : 3,
                      width: 12,
                      height: 12,
                      borderRadius: '50%',
                      background: '#fff',
                      transition: 'left 0.2s',
                    }}
                  />
                </div>
                <span style={{ fontFamily: 'Inter, sans-serif', fontSize: 12, color: '#C5CDD8' }}>
                  Use the seeded SBA committee instead of automatic audience inference
                </span>
              </label>

              <details
                style={{
                  marginBottom: 18,
                  borderRadius: 12,
                  border: `1px solid ${PANEL_BORDER}`,
                  background: 'rgba(5,7,11,0.42)',
                  overflow: 'hidden',
                }}
              >
                <summary
                  style={{
                    listStyle: 'none',
                    cursor: 'pointer',
                    padding: '12px 14px',
                    fontFamily: 'Inter, sans-serif',
                    fontSize: 12,
                    fontWeight: 600,
                    color: '#C5CDD8',
                  }}
                >
                  Advanced Settings
                </summary>
                <div style={{ padding: '0 14px 14px', display: 'grid', gap: 12 }}>
                  <div>
                    <FieldLabel>Evaluation Mode</FieldLabel>
                    <select
                      value={evaluationMode}
                      onChange={(event) => {
                        setEvaluationMode(event.target.value as CommitteeEvaluationMode);
                        clearPreview();
                      }}
                      style={selectStyle}
                    >
                      <option value="full_committee">Full Committee</option>
                      <option value="adversarial">Adversarial</option>
                      <option value="champion_only">Champion Only</option>
                    </select>
                  </div>
                  <div>
                    <FieldLabel>Industry Profile</FieldLabel>
                    <select
                      value={industryProfileId}
                      onChange={(event) => {
                        setIndustryProfileId(event.target.value);
                        clearPreview();
                      }}
                      style={selectStyle}
                    >
                      {INDUSTRY_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: isNarrow ? '1fr' : '1fr 1fr', gap: 12 }}>
                    <div>
                      <FieldLabel>Do No Harm Floor</FieldLabel>
                      <input
                        type="number"
                        min={-0.2}
                        max={0}
                        step={0.01}
                        value={doNoHarmFloor}
                        onChange={(event) => setDoNoHarmFloor(Number(event.target.value))}
                        style={inputStyle}
                      />
                    </div>
                    <label
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 10,
                        paddingTop: 18,
                        fontFamily: 'Inter, sans-serif',
                        fontSize: 12,
                        color: '#C5CDD8',
                        cursor: 'pointer',
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={autoStopOnPlateau}
                        onChange={(event) => setAutoStopOnPlateau(event.target.checked)}
                      />
                      Stop early when the score plateaus
                    </label>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: isNarrow ? '1fr' : '1fr 1fr', gap: 12 }}>
                    <div>
                      <FieldLabel>Persona Weighting</FieldLabel>
                      <select
                        value={personaWeightingMode}
                        onChange={(event) => setPersonaWeightingMode(event.target.value as 'balanced' | 'authority' | 'skeptic_priority')}
                        style={selectStyle}
                      >
                        <option value="authority">Preserve authority weighting</option>
                        <option value="balanced">Equal weighting</option>
                        <option value="skeptic_priority">Bias skeptical reviewers</option>
                      </select>
                    </div>
                    <div>
                      <FieldLabel>Reaction Memory</FieldLabel>
                      <input
                        type="number"
                        min={0}
                        max={0.8}
                        step={0.05}
                        value={reactionMemoryWeight}
                        onChange={(event) => setReactionMemoryWeight(Number(event.target.value))}
                        style={inputStyle}
                      />
                    </div>
                  </div>
                </div>
              </details>

              <div style={{ display: 'flex', gap: 10, flexDirection: isNarrow ? 'column' : 'row' }}>
                <button
                  onClick={handleStart}
                  disabled={!file || starting}
                  style={primaryButtonStyle(!file || starting)}
                >
                  {starting ? 'Starting committee…' : 'Start Committee Run →'}
                </button>

                <button
                  onClick={handlePreview}
                  disabled={!file || loading || starting}
                  style={secondaryButtonStyle(Boolean(file && !loading && !starting))}
                >
                  {loading ? 'Previewing…' : 'Preview Committee'}
                </button>
              </div>

              {error && (
                <div style={{ marginTop: 12, color: '#FB7185', fontFamily: 'Inter, sans-serif', fontSize: 12, lineHeight: 1.5 }}>
                  {error}
                </div>
              )}
            </div>
          </motion.div>
        </div>

        <div style={{ flex: 1, padding: isNarrow ? '24px 20px 36px' : '40px 36px 48px', overflowY: 'auto' }}>
          {summary ? (
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#4ADE80', boxShadow: '0 0 8px #4ADE80' }} />
                <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: 20 }}>Committee Preview</div>
              </div>

              {summaryWarnings.length > 0 && (
                <div style={{ marginBottom: 18, padding: '12px 14px', borderRadius: 12, background: 'rgba(251,191,36,0.08)', border: '1px solid rgba(251,191,36,0.18)', color: '#FCD34D', fontFamily: 'Inter, sans-serif', fontSize: 12, lineHeight: 1.5 }}>
                  {summaryWarnings.slice(0, 3).join(' ')}
                </div>
              )}

              <div style={{ display: 'grid', gridTemplateColumns: isNarrow ? '1fr 1fr' : 'repeat(5, minmax(0, 1fr))', gap: 10, marginBottom: 20 }}>
                {[
                  ['Document', summary.summary.documentName],
                  ['Sections', String(summary.summary.sectionsCount)],
                  ['Personas', String(summary.summary.personasCount)],
                  ['Industry', summary.summary.industryLabel],
                  ['Mode', MODE_LABELS[summary.summary.evaluationMode]],
                ].map(([label, value]) => (
                  <div
                    key={label}
                    style={{
                      padding: '12px 14px',
                      borderRadius: 12,
                      background: 'rgba(10,14,20,0.72)',
                      border: `1px solid ${PANEL_BORDER}`,
                    }}
                  >
                    <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#6B7480', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 6 }}>
                      {label}
                    </div>
                    <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#EEF3FF', fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {value}
                    </div>
                  </div>
                ))}
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: isNarrow ? '1fr' : '1.08fr 0.92fr', gap: 14 }}>
                <div style={{ padding: 16, borderRadius: 14, background: 'rgba(10,14,20,0.72)', border: `1px solid ${PANEL_BORDER}` }}>
                  <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#6B7480', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 12 }}>
                    Parsed Sections
                  </div>
                  <div style={{ display: 'grid', gap: 8 }}>
                    {summary.document.sections.slice(0, 8).map((section) => (
                      <div
                        key={section.id}
                        style={{
                          padding: '9px 11px',
                          borderRadius: 9,
                          background: 'rgba(255,255,255,0.03)',
                          borderLeft: '2px solid rgba(77,163,255,0.25)',
                        }}
                      >
                        <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 12, fontWeight: 600, color: '#EEF3FF', marginBottom: 3 }}>
                          {section.id}. {section.title}
                        </div>
                        <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 10, color: '#9AA4B2', lineHeight: 1.45 }}>
                          {section.content.slice(0, 160)}
                          {section.content.length > 160 ? '…' : ''}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                <div style={{ padding: 16, borderRadius: 14, background: 'rgba(10,14,20,0.72)', border: `1px solid ${PANEL_BORDER}` }}>
                  <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 9, color: '#6B7480', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 12 }}>
                    Inferred Committee
                  </div>
                  <div style={{ display: 'grid', gap: 8 }}>
                    {summary.personas.map((persona) => (
                      <div key={persona.id} style={{ padding: '9px 11px', borderRadius: 9, background: 'rgba(255,255,255,0.03)' }}>
                        <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 12, fontWeight: 600, color: '#EEF3FF' }}>
                          {persona.name}
                        </div>
                        <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 10, color: '#9AA4B2', marginTop: 2 }}>
                          {persona.title}
                        </div>
                        {persona.priorities[0] && (
                          <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 10, color: '#4DA3FF', marginTop: 4 }}>
                            → {persona.priorities[0]}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
          ) : (
            <div style={{ maxWidth: 760, margin: isStacked ? '0 auto' : '42px auto 0' }}>
              <div
                style={{
                  padding: '22px 24px',
                  borderRadius: 18,
                  background: 'rgba(10,14,20,0.54)',
                  border: `1px solid ${PANEL_BORDER}`,
                  marginBottom: 18,
                }}
              >
                <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 10, letterSpacing: '0.14em', color: '#6B7480', textTransform: 'uppercase', marginBottom: 10 }}>
                  What Happens On Start
                </div>
                <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 24, fontWeight: 700, color: '#EEF3FF', marginBottom: 8 }}>
                  Same visual language, new objective
                </div>
                <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 14, color: '#94A0AF', lineHeight: 1.6 }}>
                  The document is parsed, the room is inferred, a baseline consensus score is established, and then the optimizer starts testing rewrites live in the same left-stream, center-canvas, right-rail structure as the Elasticsearch tuner.
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: isNarrow ? '1fr' : 'repeat(3, minmax(0, 1fr))', gap: 12 }}>
                {[
                  ['1. Parse', 'Break the document into clean sections and detect claims, evidence, and calls to action.'],
                  ['2. Seat the room', 'Infer the committee or use your pasted audience description to build the buying room.'],
                  ['3. Optimize live', 'Test one rewrite at a time and keep only the changes that improve consensus without doing harm.'],
                ].map(([title, body]) => (
                  <div
                    key={title}
                    style={{
                      padding: '16px 18px',
                      borderRadius: 14,
                      background: 'rgba(10,14,20,0.42)',
                      border: `1px solid ${PANEL_BORDER}`,
                    }}
                  >
                    <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 15, fontWeight: 700, color: '#EEF3FF', marginBottom: 8 }}>
                      {title}
                    </div>
                    <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 12, lineHeight: 1.6, color: '#94A0AF' }}>
                      {body}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </ErrorBoundary>
  );
}

const selectStyle: React.CSSProperties = {
  width: '100%',
  borderRadius: 10,
  border: `1px solid ${PANEL_BORDER}`,
  background: 'rgba(5,7,11,0.8)',
  color: '#EEF3FF',
  fontFamily: 'Inter, sans-serif',
  fontSize: 12,
  padding: '10px 12px',
  outline: 'none',
};

const inputStyle: React.CSSProperties = {
  width: '100%',
  boxSizing: 'border-box',
  borderRadius: 10,
  border: `1px solid ${PANEL_BORDER}`,
  background: 'rgba(5,7,11,0.8)',
  color: '#EEF3FF',
  fontFamily: 'JetBrains Mono, monospace',
  fontSize: 12,
  padding: '10px 12px',
  outline: 'none',
};

function primaryButtonStyle(disabled: boolean): React.CSSProperties {
  return {
    flex: 1,
    padding: '13px 18px',
    borderRadius: 10,
    border: 'none',
    background: disabled ? 'rgba(77,163,255,0.3)' : '#4DA3FF',
    color: '#05070B',
    fontFamily: 'Inter, sans-serif',
    fontWeight: 700,
    fontSize: 13,
    cursor: disabled ? 'not-allowed' : 'pointer',
  };
}

function secondaryButtonStyle(enabled: boolean): React.CSSProperties {
  return {
    flex: 1,
    padding: '13px 18px',
    borderRadius: 10,
    border: `1px solid ${enabled ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.08)'}`,
    background: 'rgba(255,255,255,0.03)',
    color: enabled ? '#EEF3FF' : '#4B5563',
    fontFamily: 'Inter, sans-serif',
    fontWeight: 700,
    fontSize: 13,
    cursor: enabled ? 'pointer' : 'not-allowed',
  };
}
