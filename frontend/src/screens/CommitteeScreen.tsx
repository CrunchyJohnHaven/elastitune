import React, { useCallback, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { api } from '@/lib/api';
import { PANEL_BORDER } from '@/lib/theme';
import { useCommitteeStore } from '@/store/useCommitteeStore';
import ErrorBoundary from '@/components/ErrorBoundary';

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

export default function CommitteeScreen() {
  const navigate = useNavigate();
  const { setConnectionId, setRunId, reset } = useCommitteeStore();

  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const [starting, setStarting] = useState(false);
  const [committeeDescription, setCommitteeDescription] = useState('');
  const [useSeedPersonas, setUseSeedPersonas] = useState(false);
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof api.connectCommittee>> | null>(null);
  const [error, setError] = useState<string | null>(null);

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
      evaluationMode: 'full_committee',
      useSeedPersonas,
      committeeDescription,
    });
    setSummary(response);
    setConnectionId(response.connectionId);
    return response;
  }, [committeeDescription, file, setConnectionId, useSeedPersonas]);

  const handlePreview = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      await connectCurrentDocument();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to preview committee');
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
      });
      setRunId(response.runId);
      navigate(`/committee/run/${response.runId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start committee run');
      setStarting(false);
    }
  };

  return (
    <ErrorBoundary title="Committee Setup Failed">
    <div style={{ width: '100vw', minHeight: '100vh', background: '#05070B', color: '#EEF3FF', display: 'flex' }}>
      <div
        style={{
          width: 580,
          flexShrink: 0,
          padding: '44px 52px 56px',
          borderRight: `1px solid ${PANEL_BORDER}`,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 28 }}>
            <div>
              <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 26, fontWeight: 700, lineHeight: 1.15 }}>
                Simulated Buying Committee
              </div>
              <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 13, color: '#9AA4B2', marginTop: 7, lineHeight: 1.5 }}>
                Upload a pitch or proposal and run the same ElastiTune-style optimization loop against a live stakeholder committee.
              </div>
            </div>
            <Link
              to="/"
              onClick={() => reset()}
              style={{
                color: '#4DA3FF',
                fontFamily: 'Inter, sans-serif',
                fontSize: 12,
                textDecoration: 'none',
                flexShrink: 0,
                marginTop: 4,
              }}
            >
              ← Search Mode
            </Link>
          </div>

          <div style={{ display: 'flex', gap: 20, marginBottom: 24 }}>
            <StepBadge n={1} label="Upload" active={step >= 1} />
            <StepBadge n={2} label="Preview" active={step >= 2} />
            <StepBadge n={3} label="Run Live" active={step >= 3} />
          </div>

          <div
            style={{
              padding: 24,
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
                Paste the room if you know it. Otherwise leave this blank and the system will infer the ideal buying committee from the document.
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
              style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20, cursor: 'pointer' }}
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

            <div style={{ display: 'flex', gap: 10 }}>
              <button
                onClick={handleStart}
                disabled={!file || starting}
                style={{
                  flex: 1,
                  padding: '13px 18px',
                  borderRadius: 10,
                  border: 'none',
                  background: !file || starting ? 'rgba(77,163,255,0.3)' : '#4DA3FF',
                  color: '#05070B',
                  fontFamily: 'Inter, sans-serif',
                  fontWeight: 700,
                  fontSize: 13,
                  cursor: !file || starting ? 'not-allowed' : 'pointer',
                }}
              >
                {starting ? 'Starting committee…' : 'Start Committee Run →'}
              </button>

              <button
                onClick={handlePreview}
                disabled={!file || loading || starting}
                style={{
                  flex: 1,
                  padding: '13px 18px',
                  borderRadius: 10,
                  border: `1px solid ${file ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.08)'}`,
                  background: 'rgba(255,255,255,0.03)',
                  color: file ? '#EEF3FF' : '#4B5563',
                  fontFamily: 'Inter, sans-serif',
                  fontWeight: 700,
                  fontSize: 13,
                  cursor: !file || loading || starting ? 'not-allowed' : 'pointer',
                }}
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

      <div style={{ flex: 1, padding: '44px 40px 56px', overflowY: 'auto' }}>
        {summary ? (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#4ADE80', boxShadow: '0 0 8px #4ADE80' }} />
              <div style={{ fontFamily: 'Inter, sans-serif', fontWeight: 700, fontSize: 20 }}>Committee Preview</div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 10, marginBottom: 20 }}>
              {[
                ['Document', summary.summary.documentName],
                ['Sections', String(summary.summary.sectionsCount)],
                ['Personas', String(summary.summary.personasCount)],
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

            <div style={{ display: 'grid', gridTemplateColumns: '1.08fr 0.92fr', gap: 14 }}>
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
          <div style={{ maxWidth: 720, margin: '56px auto 0' }}>
            <div
              style={{
                padding: 24,
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
                Same ElastiTune loop, new objective
              </div>
              <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 14, color: '#94A0AF', lineHeight: 1.6 }}>
                The document is parsed, the committee is generated, a baseline consensus score is established, and then the system starts testing rewrites live in the same left-stream / center-canvas / right-rail workflow as the Elasticsearch tuner.
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 12 }}>
              {[
                ['1. Parse', 'Break the document into sections and isolate stats, claims, proof points, and CTAs.'],
                ['2. Seat the room', 'Infer or load personas, then score the baseline version from each stakeholder point of view.'],
                ['3. Optimize live', 'Test rewrites one section at a time and keep only the changes that improve consensus without hurting one buyer too much.'],
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
