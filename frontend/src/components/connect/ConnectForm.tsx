import React, { useEffect, useMemo, useState } from 'react';
import { ChevronDown, ChevronUp, Eye, EyeOff, Loader2 } from 'lucide-react';
import { api } from '@/lib/api';
import type {
  BenchmarkHealthPreset,
  ConnectionSummary,
  EvalCase,
  LlmConfig,
  SearchRunListItem,
} from '@/types/contracts';
import { PANEL_BORDER, ACCENT_BLUE } from '@/lib/theme';
import { ELASTIC_PRODUCT_STORE_EVAL_SET } from '@/demo/elasticProductStoreEvalSet';
import { BOOKS_CATALOG_EVAL_SET } from '@/demo/booksCatalogEvalSet';
import { WORKPLACE_DOCS_EVAL_SET } from '@/demo/workplaceDocsEvalSet';
import { SECURITY_SIEM_EVAL_SET } from '@/demo/securitySiemEvalSet';
import { TMDB_MOVIES_EVAL_SET } from '@/demo/tmdbMoviesEvalSet';

interface BenchmarkPreset {
  id: string;
  label: string;
  description: string;
  indexName: string;
  evalSet: EvalCase[];
  docCount: string;
  domain: string;
}

const BENCHMARK_PRESETS: BenchmarkPreset[] = [
  {
    id: 'products',
    label: 'Product Store',
    description: 'E-commerce beauty products — 931 docs, 8 queries',
    indexName: 'products-catalog',
    evalSet: ELASTIC_PRODUCT_STORE_EVAL_SET,
    docCount: '931',
    domain: 'E-commerce',
  },
  {
    id: 'books',
    label: 'Books Catalog',
    description: 'Classic & modern literature — 2,000 docs, 12 queries',
    indexName: 'books-catalog',
    evalSet: BOOKS_CATALOG_EVAL_SET,
    docCount: '2000',
    domain: 'Library',
  },
  {
    id: 'workplace',
    label: 'Workplace Docs',
    description: 'HR policies & company docs — 15 docs, 12 queries',
    indexName: 'workplace-docs',
    evalSet: WORKPLACE_DOCS_EVAL_SET,
    docCount: '15',
    domain: 'Enterprise',
  },
  {
    id: 'security',
    label: 'Security SIEM',
    description: 'Detection rules, alerts & threat intel — 301 docs, 18 queries',
    indexName: 'security-siem',
    evalSet: SECURITY_SIEM_EVAL_SET,
    docCount: '301',
    domain: 'Security',
  },
  {
    id: 'tmdb',
    label: 'TMDB Movies',
    description: 'Movie metadata & synopses — 8,516 docs, 12 queries',
    indexName: 'tmdb',
    evalSet: TMDB_MOVIES_EVAL_SET,
    docCount: '8516',
    domain: 'Media',
  },
];

interface ConnectFormProps {
  onConnected: (
    connectionId: string,
    summary: ConnectionSummary,
    autoRun?: boolean,
    previousRun?: SearchRunListItem | null,
  ) => void;
  onDemoStart: (runId: string) => void;
  isLoading: boolean;
  setIsLoading: (v: boolean) => void;
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '10px 12px',
  background: 'rgba(5,7,11,0.7)',
  border: '1px solid rgba(255,255,255,0.09)',
  borderRadius: 7,
  color: '#EEF3FF',
  fontFamily: 'Inter, sans-serif',
  fontSize: 13,
  outline: 'none',
  boxSizing: 'border-box',
  transition: 'border-color 0.15s',
};

const labelStyle: React.CSSProperties = {
  fontFamily: 'Inter, sans-serif',
  fontSize: 11,
  fontWeight: 500,
  color: '#6B7480',
  letterSpacing: '0.04em',
  marginBottom: 5,
  display: 'block',
};

function FormField({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div style={{ marginBottom: 14 }}>
      <label style={labelStyle}>{label}</label>
      {children}
    </div>
  );
}

function StyledInput({
  type = 'text',
  value,
  onChange,
  placeholder,
  autoComplete,
  showToggle,
}: {
  type?: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  autoComplete?: string;
  showToggle?: boolean;
}) {
  const [show, setShow] = useState(false);
  const actualType = showToggle && !show ? 'password' : type === 'password' && !show ? 'password' : 'text';

  return (
    <div style={{ position: 'relative' }}>
      <input
        type={showToggle ? (show ? 'text' : 'password') : type}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        autoComplete={autoComplete}
        style={inputStyle}
        onFocus={e => {
          e.currentTarget.style.borderColor = 'rgba(77,163,255,0.4)';
        }}
        onBlur={e => {
          e.currentTarget.style.borderColor = 'rgba(255,255,255,0.09)';
        }}
      />
      {showToggle && (
        <button
          type="button"
          onClick={() => setShow(s => !s)}
          style={{
            position: 'absolute',
            right: 10,
            top: '50%',
            transform: 'translateY(-50%)',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            color: '#6B7480',
            padding: 0,
            display: 'flex',
            alignItems: 'center',
          }}
          tabIndex={-1}
        >
          {show ? <EyeOff size={14} /> : <Eye size={14} />}
        </button>
      )}
    </div>
  );
}

export default function ConnectForm({
  onConnected,
  onDemoStart,
  isLoading,
  setIsLoading,
}: ConnectFormProps) {
  const benchmarkUrl = 'http://127.0.0.1:9200';
  const benchmarkIndex = 'products-catalog';
  const [esUrl, setEsUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [indexName, setIndexName] = useState('');
  const [autoEval, setAutoEval] = useState(true);
  const [customOpen, setCustomOpen] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadedEvalSet, setUploadedEvalSet] = useState<EvalCase[] | null>(null);
  const [uploadedEvalName, setUploadedEvalName] = useState<string | null>(null);
  const [previousRun, setPreviousRun] = useState<SearchRunListItem | null>(null);
  const [benchmarkHealth, setBenchmarkHealth] = useState<Record<string, BenchmarkHealthPreset>>({});
  const [benchmarkReachable, setBenchmarkReachable] = useState<boolean | null>(null);

  // LLM settings
  const [llmProvider, setLlmProvider] = useState<LlmConfig['provider']>('openai_compatible');
  const [llmBaseUrl, setLlmBaseUrl] = useState('');
  const [llmModel, setLlmModel] = useState('');
  const [llmApiKey, setLlmApiKey] = useState('');
  const [selectedPreset, setSelectedPreset] = useState<string | null>(null);
  const benchmarkLoaded =
    esUrl.trim() === benchmarkUrl &&
    BENCHMARK_PRESETS.some(p => p.indexName === indexName.trim()) &&
    uploadedEvalName === 'Built-in Elastic benchmark eval set';
  const customFieldsOpen =
    customOpen || (!benchmarkLoaded && (!!esUrl || !!indexName || !!apiKey || !!uploadedEvalSet || advancedOpen));
  const showBenchmarkConnectionHelp =
    benchmarkLoaded && error?.includes('Cannot reach Elasticsearch cluster');
  const previousRunLookupIndex = useMemo(() => indexName.trim() || null, [indexName]);

  useEffect(() => {
    let cancelled = false;

    if (!previousRunLookupIndex) {
      setPreviousRun(null);
      return undefined;
    }

    api.listRuns({ limit: 5, indexName: previousRunLookupIndex, completedOnly: true })
      .then(({ runs }) => {
        if (cancelled) return;
        setPreviousRun(runs[0] ?? null);
      })
      .catch(() => {
        if (!cancelled) {
          setPreviousRun(null);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [previousRunLookupIndex]);

  useEffect(() => {
    let cancelled = false;

    api.getBenchmarkHealth(benchmarkUrl)
      .then((health) => {
        if (cancelled) return;
        setBenchmarkReachable(health.reachable);
        setBenchmarkHealth(
          Object.fromEntries(health.presets.map((preset) => [preset.indexName, preset]))
        );
      })
      .catch(() => {
        if (!cancelled) {
          setBenchmarkReachable(false);
          setBenchmarkHealth({});
        }
      });

    return () => {
      cancelled = true;
    };
  }, [benchmarkUrl]);

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();

    // Auto-load benchmark preset if no custom URL is provided
    let effectiveUrl = esUrl.trim();
    let effectiveIndex = indexName.trim();
    let effectiveApiKey = apiKey.trim();
    let effectiveEvalSet = uploadedEvalSet;
    let effectiveAutoEval = autoEval;
    let isBenchmarkAutoRun = false;

    if (!effectiveUrl) {
      // Nothing filled in — use the selected benchmark preset (or default to products)
      const preset = BENCHMARK_PRESETS.find(p => p.id === selectedPreset) ?? BENCHMARK_PRESETS[0];
      effectiveUrl = benchmarkUrl;
      effectiveIndex = preset.indexName;
      effectiveApiKey = '';
      effectiveEvalSet = preset.evalSet;
      effectiveAutoEval = false;
      isBenchmarkAutoRun = true;
      // Also update state so UI reflects what we're connecting to
      setEsUrl(benchmarkUrl);
      setApiKey('');
      setIndexName(preset.indexName);
      setUploadedEvalSet(preset.evalSet);
      setUploadedEvalName('Built-in Elastic benchmark eval set');
      setAutoEval(false);
    }

    // If benchmark preset was already loaded, also auto-run
    if (!isBenchmarkAutoRun && benchmarkLoaded) {
      isBenchmarkAutoRun = true;
    }

    setError(null);
    setIsLoading(true);

    try {
      const llm: LlmConfig = {
        provider: llmProvider,
        baseUrl: llmBaseUrl || undefined,
        model: llmModel || undefined,
        apiKey: llmApiKey || undefined,
      };

      const resp = await api.connect({
        mode: 'live',
        esUrl: effectiveUrl,
        apiKey: effectiveApiKey || undefined,
        indexName: effectiveIndex || undefined,
        uploadedEvalSet: effectiveEvalSet ?? undefined,
        autoGenerateEval: effectiveAutoEval,
        llm,
      });

      let matchedPreviousRun =
        previousRun && previousRun.index_name === effectiveIndex ? previousRun : null;
      if (!matchedPreviousRun && effectiveIndex) {
        try {
          const previous = await api.listRuns({
            limit: 1,
            indexName: effectiveIndex,
            completedOnly: true,
          });
          matchedPreviousRun = previous.runs[0] ?? null;
        } catch {
          matchedPreviousRun = null;
        }
      }

      // For benchmark preset: connect + start optimization in one click
      // For custom index: show summary card so user can review before starting
      onConnected(resp.connectionId, resp.summary, isBenchmarkAutoRun, matchedPreviousRun);
    } catch (err) {
      setError(normalizeErrorMessage(err, 'Could not analyze this search index.'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleDemo = async () => {
    setError(null);
    setIsLoading(true);
    try {
      const resp = await api.connect({ mode: 'demo' });
      const runResp = await api.startRun(resp.connectionId);
      onDemoStart(runResp.runId);
    } catch (err) {
      setError(normalizeErrorMessage(err, 'Could not start the demo.'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleEvalUpload = async (file: File | null) => {
    if (!file) return;
    try {
      const text = await file.text();
      const parsed = JSON.parse(text);
      if (!Array.isArray(parsed)) {
        throw new Error('Expected a JSON array of evaluation cases.');
      }
      const normalized: EvalCase[] = parsed.map((item, index) => ({
        id: String(item.id ?? `eval_${index + 1}`),
        query: String(item.query ?? ''),
        relevantDocIds: Array.isArray(item.relevantDocIds)
          ? item.relevantDocIds.map((id: unknown) => String(id))
          : [],
        difficulty: item.difficulty === 'easy' || item.difficulty === 'medium' || item.difficulty === 'hard'
          ? item.difficulty
          : undefined,
        personaHint: item.personaHint ? String(item.personaHint) : undefined,
      })).filter(item => item.query.length > 0 && item.relevantDocIds.length > 0);

      if (normalized.length === 0) {
        throw new Error('No valid evaluation cases were found in that file.');
      }

      setUploadedEvalSet(normalized);
      setUploadedEvalName(file.name);
      setAutoEval(false);
      setError(null);
    } catch (err) {
      setUploadedEvalSet(null);
      setUploadedEvalName(null);
      setError(err instanceof Error ? err.message : 'Failed to parse evaluation set');
    }
  };

  const handleLoadBenchmarkPreset = (presetId?: string) => {
    const preset = BENCHMARK_PRESETS.find(p => p.id === (presetId ?? 'products')) ?? BENCHMARK_PRESETS[0];
    setEsUrl(benchmarkUrl);
    setApiKey('');
    setIndexName(preset.indexName);
    setUploadedEvalSet(preset.evalSet);
    setUploadedEvalName('Built-in Elastic benchmark eval set');
    setAutoEval(false);
    setCustomOpen(false);
    setAdvancedOpen(false);
    setSelectedPreset(preset.id);
    setError(null);
  };

  return (
    <form onSubmit={handleAnalyze} noValidate>
      <div
        style={{
          marginBottom: 16,
          padding: '14px 14px 12px',
          background: 'linear-gradient(180deg, rgba(77,163,255,0.08) 0%, rgba(77,163,255,0.02) 100%)',
          borderRadius: 9,
          border: '1px solid rgba(77,163,255,0.16)',
          boxShadow: benchmarkLoaded ? '0 0 24px rgba(77,163,255,0.12)' : 'none',
        }}
      >
        <div style={{ marginBottom: 10 }}>
          <div
            style={{
              fontFamily: 'Inter, sans-serif',
              fontSize: 12,
              fontWeight: 600,
              color: '#EEF3FF',
              marginBottom: 3,
            }}
          >
            Choose a benchmark system to optimize
          </div>
          <div
            style={{
              fontFamily: 'Inter, sans-serif',
              fontSize: 11,
              color: '#9AA4B2',
              lineHeight: 1.45,
            }}
          >
            Select any Elasticsearch index below to run a one-click optimization and see measurable improvements.
          </div>
        </div>

      {previousRun && previousRunLookupIndex && (
        <div
          style={{
            marginBottom: 16,
            padding: '12px 14px',
            background: 'rgba(74,222,128,0.06)',
            borderRadius: 9,
            border: '1px solid rgba(74,222,128,0.16)',
          }}
        >
          <div
            style={{
              fontFamily: 'Inter, sans-serif',
              fontSize: 12,
              fontWeight: 600,
              color: '#EEF3FF',
              marginBottom: 4,
            }}
          >
            Previous run found
          </div>
          <div
            style={{
              fontFamily: 'Inter, sans-serif',
              fontSize: 11,
              color: '#9AA4B2',
              lineHeight: 1.5,
            }}
          >
            nDCG improved from {previousRun.baseline_score.toFixed(3)} to {previousRun.best_score.toFixed(3)} on this index.
            ElastiTune will offer to continue from that stronger baseline.
          </div>
        </div>
      )}

        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 6,
          }}
        >
          {benchmarkReachable === false && (
            <div
              style={{
                marginBottom: 4,
                padding: '8px 10px',
                borderRadius: 8,
                border: '1px solid rgba(251,113,133,0.18)',
                background: 'rgba(251,113,133,0.06)',
                fontFamily: 'Inter, sans-serif',
                fontSize: 11,
                color: '#FCA5A5',
                lineHeight: 1.45,
              }}
            >
              Local Elasticsearch is not reachable at {benchmarkUrl}. Start Elasticsearch first, then these benchmark presets will become runnable.
            </div>
          )}
          {BENCHMARK_PRESETS.map(preset => {
            const isSelected = selectedPreset === preset.id || (!selectedPreset && indexName === preset.indexName && benchmarkLoaded);
            const health = benchmarkHealth[preset.indexName];
            const setupRequired = health ? !health.ready : false;
            return (
              <button
                key={preset.id}
                type="button"
                onClick={() => handleLoadBenchmarkPreset(preset.id)}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr auto',
                  gap: 8,
                  alignItems: 'center',
                  width: '100%',
                  padding: '10px 12px',
                  background: isSelected ? 'rgba(77,163,255,0.12)' : 'rgba(255,255,255,0.03)',
                  border: `1px solid ${isSelected ? 'rgba(77,163,255,0.35)' : 'rgba(255,255,255,0.06)'}`,
                  borderRadius: 8,
                  cursor: 'pointer',
                  textAlign: 'left',
                  transition: 'border-color 0.15s, background 0.15s',
                }}
              >
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
                    <span
                      style={{
                        fontFamily: 'Inter, sans-serif',
                        fontSize: 12,
                        fontWeight: 600,
                        color: isSelected ? '#7CE7FF' : '#EEF3FF',
                      }}
                    >
                      {preset.label}
                    </span>
                    <span
                      style={{
                        fontFamily: 'JetBrains Mono, monospace',
                        fontSize: 9,
                        color: '#6B7480',
                        background: 'rgba(255,255,255,0.05)',
                        padding: '1px 6px',
                        borderRadius: 3,
                      }}
                    >
                      {preset.domain}
                    </span>
                    {setupRequired && (
                      <span
                        style={{
                          fontFamily: 'Inter, sans-serif',
                          fontSize: 9,
                          fontWeight: 600,
                          color: '#FBBF24',
                          background: 'rgba(251,191,36,0.1)',
                          border: '1px solid rgba(251,191,36,0.18)',
                          padding: '1px 6px',
                          borderRadius: 999,
                        }}
                      >
                        Setup required
                      </span>
                    )}
                  </div>
                  <div
                    style={{
                      fontFamily: 'Inter, sans-serif',
                      fontSize: 10,
                      color: '#6B7480',
                    }}
                  >
                    {preset.description}
                  </div>
                  {health && (
                    <div
                      style={{
                        marginTop: 4,
                        fontFamily: 'JetBrains Mono, monospace',
                        fontSize: 9,
                        color: setupRequired ? '#FBBF24' : '#4ADE80',
                      }}
                    >
                      {setupRequired
                        ? `ready after ${health.expectedDocCount} docs · current ${health.docCount}`
                        : `ready · ${health.docCount} docs indexed`}
                    </div>
                  )}
                  {setupRequired && (
                    <div
                      style={{
                        marginTop: 4,
                        fontFamily: 'Inter, sans-serif',
                        fontSize: 10,
                        color: '#9AA4B2',
                      }}
                    >
                      Fix with: <span style={{ color: '#EEF3FF' }}>{health.setupCommand}</span>
                    </div>
                  )}
                </div>
                <div
                  style={{
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: 10,
                    color: isSelected ? '#4ADE80' : setupRequired ? '#FBBF24' : '#4B5563',
                    fontWeight: 600,
                  }}
                >
                  {isSelected ? 'SELECTED' : setupRequired ? 'SETUP' : 'SELECT'}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      <div style={{ marginBottom: 16 }}>
        <button
          type="button"
          onClick={() => setCustomOpen(o => !o)}
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'none',
            border: '1px solid rgba(255,255,255,0.07)',
            borderRadius: 7,
            padding: '10px 12px',
            cursor: 'pointer',
            color: '#EEF3FF',
            fontFamily: 'Inter, sans-serif',
            fontSize: 12,
            fontWeight: 600,
          }}
        >
          <span>Use my own Elasticsearch index</span>
          {customFieldsOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>

        {!customFieldsOpen && (
          <div
            style={{
              marginTop: 8,
              fontFamily: 'Inter, sans-serif',
              fontSize: 11,
              color: '#6B7480',
              lineHeight: 1.5,
            }}
          >
            Optional. Open this only if you want to test your own cluster instead of the built-in sample benchmark.
          </div>
        )}

        {customFieldsOpen && (
          <div
            style={{
              marginTop: 10,
              padding: '14px 14px 12px',
              background: 'rgba(255,255,255,0.025)',
              borderRadius: 9,
              border: '1px solid rgba(255,255,255,0.06)',
            }}
          >
            <FormField label="ELASTICSEARCH URL">
              <StyledInput
                type="url"
                value={esUrl}
                onChange={setEsUrl}
                placeholder="http://127.0.0.1:9200 or your Elastic URL"
                autoComplete="url"
              />
            </FormField>

            <FormField label="API KEY">
              <StyledInput
                type="password"
                value={apiKey}
                onChange={setApiKey}
                placeholder="Optional for local benchmark"
                autoComplete="current-password"
                showToggle
              />
              {benchmarkLoaded && (
                <div
                  style={{
                    marginTop: 6,
                    fontFamily: 'Inter, sans-serif',
                    fontSize: 11,
                    color: '#6B7480',
                    lineHeight: 1.45,
                  }}
                >
                  Leave this blank for the local sample benchmark.
                </div>
              )}
            </FormField>

            <FormField label="INDEX NAME">
              <StyledInput
                value={indexName}
                onChange={setIndexName}
                placeholder="The Elasticsearch index you want to improve"
              />
            </FormField>

            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: 14,
                padding: '10px 12px',
                background: 'rgba(255,255,255,0.025)',
                borderRadius: 7,
                border: '1px solid rgba(255,255,255,0.06)',
                cursor: 'pointer',
              }}
              onClick={() => setAutoEval(v => !v)}
            >
              <div>
                <div
                  style={{
                    fontFamily: 'Inter, sans-serif',
                    fontSize: 12,
                    fontWeight: 500,
                    color: '#EEF3FF',
                    marginBottom: 1,
                  }}
                >
                  Create test searches automatically
                </div>
                <div
                  style={{
                    fontFamily: 'Inter, sans-serif',
                    fontSize: 11,
                    color: '#6B7480',
                  }}
                >
                  Let ElastiTune build a starter test set from your sample documents
                </div>
              </div>
              <div
                style={{
                  width: 38,
                  height: 22,
                  borderRadius: 11,
                  background: autoEval ? ACCENT_BLUE : 'rgba(255,255,255,0.1)',
                  position: 'relative',
                  transition: 'background 0.2s',
                  flexShrink: 0,
                }}
              >
                <div
                  style={{
                    position: 'absolute',
                    top: 3,
                    left: autoEval ? 19 : 3,
                    width: 16,
                    height: 16,
                    borderRadius: '50%',
                    background: '#fff',
                    transition: 'left 0.2s',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
                  }}
                />
              </div>
            </div>

            <div
              style={{
                marginBottom: 12,
                padding: '12px',
                background: 'rgba(255,255,255,0.025)',
                borderRadius: 7,
                border: '1px solid rgba(255,255,255,0.06)',
              }}
            >
              <div
                style={{
                  fontFamily: 'Inter, sans-serif',
                  fontSize: 12,
                  fontWeight: 500,
                  color: '#EEF3FF',
                  marginBottom: 4,
                }}
              >
                Test search set
              </div>
              <div
                style={{
                  fontFamily: 'Inter, sans-serif',
                  fontSize: 11,
                  color: '#6B7480',
                  marginBottom: 10,
                  lineHeight: 1.45,
                }}
              >
                Upload known searches and expected results, or keep automatic generation on.
              </div>

              <label
                style={{
                  display: 'block',
                  padding: '10px 12px',
                  borderRadius: 7,
                  border: '1px dashed rgba(77,163,255,0.28)',
                  background: 'rgba(77,163,255,0.04)',
                  color: '#9AA4B2',
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: 11,
                  cursor: 'pointer',
                  marginBottom: 8,
                }}
              >
                <input
                  type="file"
                  accept=".json,application/json"
                  style={{ display: 'none' }}
                  onChange={e => {
                    void handleEvalUpload(e.target.files?.[0] ?? null);
                    e.currentTarget.value = '';
                  }}
                />
                {uploadedEvalName
                  ? `Loaded ${uploadedEvalSet?.length ?? 0} test searches from ${uploadedEvalName}`
                  : 'Upload test-search JSON'}
              </label>

              {uploadedEvalSet && (
                <button
                  type="button"
                  onClick={() => {
                    setUploadedEvalSet(null);
                    setUploadedEvalName(null);
                    setAutoEval(true);
                  }}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#4DA3FF',
                    fontFamily: 'Inter, sans-serif',
                    fontSize: 11,
                    cursor: 'pointer',
                    padding: 0,
                  }}
                >
                  Clear uploaded test set and go back to automatic generation
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      <div style={{ marginBottom: 16 }}>
        <button
          type="button"
          onClick={() => setAdvancedOpen(o => !o)}
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'none',
            border: '1px solid rgba(255,255,255,0.07)',
            borderRadius: 7,
            padding: '8px 12px',
            cursor: 'pointer',
            color: '#6B7480',
            fontFamily: 'Inter, sans-serif',
            fontSize: 11,
            fontWeight: 500,
          }}
        >
          <span>Advanced — LLM Settings</span>
          {advancedOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>

        {advancedOpen && (
          <div
            style={{
              marginTop: 8,
              padding: '14px',
              background: 'rgba(5,7,11,0.5)',
              borderRadius: 7,
              border: '1px solid rgba(255,255,255,0.06)',
              display: 'flex',
              flexDirection: 'column',
              gap: 12,
            }}
          >
            <div>
              <label style={labelStyle}>PROVIDER</label>
              <select
                value={llmProvider}
                onChange={e => setLlmProvider(e.target.value as LlmConfig['provider'])}
                style={{
                  ...inputStyle,
                  cursor: 'pointer',
                  appearance: 'none',
                }}
              >
                <option value="openai_compatible">OpenAI-Compatible</option>
                <option value="openai">OpenAI</option>
                <option value="anthropic">Anthropic</option>
                <option value="disabled">Disabled</option>
              </select>
            </div>

            {llmProvider !== 'disabled' && (
              <>
                <div>
                  <label style={labelStyle}>BASE URL</label>
                  <StyledInput
                    value={llmBaseUrl}
                    onChange={setLlmBaseUrl}
                    placeholder="https://api.openai.com/v1"
                  />
                </div>
                <div>
                  <label style={labelStyle}>MODEL</label>
                  <StyledInput
                    value={llmModel}
                    onChange={setLlmModel}
                    placeholder="gpt-4o-mini"
                  />
                </div>
                <div>
                  <label style={labelStyle}>LLM API KEY</label>
                  <StyledInput
                    type="password"
                    value={llmApiKey}
                    onChange={setLlmApiKey}
                    placeholder="sk-••••"
                    showToggle
                  />
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* Error message */}
      {error && (
        <div
          style={{
            padding: '10px 12px',
            background: 'rgba(251,113,133,0.08)',
            border: '1px solid rgba(251,113,133,0.2)',
            borderRadius: 7,
            fontFamily: 'Inter, sans-serif',
            fontSize: 12,
            color: '#FB7185',
            marginBottom: 14,
          }}
        >
          {error}
        </div>
      )}

      {showBenchmarkConnectionHelp && (
        <div
          style={{
            padding: '12px 14px',
            background: 'rgba(255,255,255,0.025)',
            border: '1px solid rgba(255,255,255,0.08)',
            borderRadius: 8,
            marginBottom: 14,
          }}
        >
          <div
            style={{
              fontFamily: 'Inter, sans-serif',
              fontSize: 12,
              fontWeight: 600,
              color: '#EEF3FF',
              marginBottom: 6,
            }}
          >
            Benchmark setup checklist
          </div>
          <div
            style={{
              fontFamily: 'Inter, sans-serif',
              fontSize: 11,
              color: '#9AA4B2',
              lineHeight: 1.5,
            }}
          >
            1. Start Elasticsearch with Docker Compose from the benchmark pack.
            <br />
            2. Leave the API key blank for this local target.
            <br />
            3. Create and ingest the <span style={{ color: '#EEF3FF' }}>products-catalog</span> index before analyzing.
          </div>
        </div>
      )}

      {/* Buttons */}
      <div style={{ display: 'flex', gap: 10 }}>
        <button
          type="submit"
          disabled={isLoading}
          style={{
            flex: 1,
            padding: '12px',
            background: isLoading
              ? 'rgba(77,163,255,0.35)'
              : 'linear-gradient(135deg, #4DA3FF 0%, #3A8FFF 100%)',
            color: '#fff',
            border: 'none',
            borderRadius: 8,
            fontFamily: 'Inter, sans-serif',
            fontWeight: 600,
            fontSize: 13,
            cursor: isLoading ? 'not-allowed' : 'pointer',
            boxShadow: isLoading ? 'none' : '0 0 20px rgba(77,163,255,0.35)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 7,
            transition: 'box-shadow 0.2s, transform 0.1s',
            opacity: isLoading ? 0.7 : 1,
          }}
          onMouseEnter={e => {
            if (!isLoading) {
              (e.currentTarget as HTMLButtonElement).style.boxShadow =
                '0 0 32px rgba(77,163,255,0.55)';
              (e.currentTarget as HTMLButtonElement).style.transform = 'translateY(-1px)';
            }
          }}
          onMouseLeave={e => {
            if (!isLoading) {
              (e.currentTarget as HTMLButtonElement).style.boxShadow =
                '0 0 20px rgba(77,163,255,0.35)';
              (e.currentTarget as HTMLButtonElement).style.transform = 'translateY(0)';
            }
          }}
        >
          {isLoading && <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />}
          {customFieldsOpen ? 'Analyze Search Index' : 'Run Benchmark'}
        </button>

        <button
          type="button"
          onClick={handleDemo}
          disabled={isLoading}
          style={{
            flex: 1,
            padding: '12px',
            background: 'transparent',
            color: '#9AA4B2',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 8,
            fontFamily: 'Inter, sans-serif',
            fontWeight: 500,
            fontSize: 13,
            cursor: isLoading ? 'not-allowed' : 'pointer',
            transition: 'color 0.15s, border-color 0.15s, background 0.15s',
            opacity: isLoading ? 0.5 : 1,
          }}
          onMouseEnter={e => {
            if (!isLoading) {
              (e.currentTarget as HTMLButtonElement).style.color = '#EEF3FF';
              (e.currentTarget as HTMLButtonElement).style.borderColor = 'rgba(255,255,255,0.2)';
              (e.currentTarget as HTMLButtonElement).style.background = 'rgba(255,255,255,0.04)';
            }
          }}
          onMouseLeave={e => {
            if (!isLoading) {
              (e.currentTarget as HTMLButtonElement).style.color = '#9AA4B2';
              (e.currentTarget as HTMLButtonElement).style.borderColor = 'rgba(255,255,255,0.1)';
              (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
            }
          }}
        >
          Launch Demo
        </button>
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </form>
  );
}

function normalizeErrorMessage(error: unknown, fallback: string): string {
  if (!(error instanceof Error)) {
    return fallback;
  }

  if (error.message.includes('Cannot reach the ElastiTune backend')) {
    return 'The ElastiTune backend is not reachable right now. Start the API server, then try again.';
  }

  if (error.message.includes('Cannot reach Elasticsearch cluster')) {
    return 'ElastiTune reached its own backend, but Elasticsearch is not responding at the cluster URL you entered.';
  }

  return error.message || fallback;
}
