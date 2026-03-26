import React from 'react';
import { PANEL_BORDER, FONT_UI, FONT_MONO } from '@/lib/theme';

/* ─────────────────────────────────────────────────────
   Catches render errors and shows a recovery message.
   For stale chunk errors (after a new deployment has
   rotated asset hashes), auto-reloads once so the user
   gets the fresh bundle without needing to click.
   ───────────────────────────────────────────────────── */

interface Props {
  children: React.ReactNode;
  fallbackTitle?: string;
  onRetry?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  autoReloading: boolean;
}

function isChunkError(err: Error | null): boolean {
  if (!err) return false;
  const msg = err.message ?? '';
  return (
    msg.includes('Failed to fetch dynamically imported module') ||
    msg.includes('Importing a module script failed') ||
    msg.includes('error loading dynamically imported module') ||
    /Loading chunk \d+ failed/.test(msg)
  );
}

const RELOAD_KEY = 'eb_chunk_reload';

export default class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, autoReloading: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error, autoReloading: false };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('ErrorBoundary caught:', error, info);

    if (isChunkError(error)) {
      const alreadyReloaded = sessionStorage.getItem(RELOAD_KEY) === '1';
      if (!alreadyReloaded) {
        sessionStorage.setItem(RELOAD_KEY, '1');
        this.setState({ autoReloading: true });
        window.location.reload();
        return;
      }
    }
    sessionStorage.removeItem(RELOAD_KEY);
  }

  render() {
    if (this.state.hasError) {
      if (this.state.autoReloading) {
        return (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              minHeight: '100vh',
              background: '#05070B',
              color: '#9AA4B2',
              fontFamily: 'Inter, sans-serif',
              fontSize: 13,
            }}
          >
            Refreshing to latest version...
          </div>
        );
      }

      const retry = () => {
        sessionStorage.removeItem(RELOAD_KEY);
        this.setState({ hasError: false, error: null, autoReloading: false });
        if (this.props.onRetry) {
          this.props.onRetry();
          return;
        }
        window.location.reload();
      };

      return (
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            minHeight: '100vh',
            padding: 40,
            background: '#05070B',
            color: '#EEF3FF',
            fontFamily: 'Inter, sans-serif',
          }}
        >
          <div
            style={{
              maxWidth: 420,
              textAlign: 'center',
              padding: '32px 28px',
              borderRadius: 14,
              background: 'rgba(10,14,20,0.8)',
              border: `1px solid ${PANEL_BORDER}`,
            }}
          >
            <div style={{ fontSize: 28, marginBottom: 12 }}>
              {'!'}
            </div>
            <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 8 }}>
              {this.props.fallbackTitle ?? 'Something went wrong'}
            </div>
            <div style={{ fontSize: 13, color: '#9AA4B2', lineHeight: 1.5, marginBottom: 16 }}>
              {this.state.error?.message ?? 'An unexpected error occurred.'}
            </div>
            <pre
              style={{
                margin: '0 0 18px',
                padding: '12px 14px',
                borderRadius: 10,
                textAlign: 'left',
                background: 'rgba(255,255,255,0.03)',
                border: `1px solid ${PANEL_BORDER}`,
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                fontFamily: FONT_MONO,
                fontSize: 11,
                color: '#FCA5A5',
                overflowX: 'auto',
              }}
            >
              {this.state.error?.stack ?? this.state.error?.message ?? 'No stack trace available.'}
            </pre>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'center', flexWrap: 'wrap' }}>
              <button
                onClick={retry}
                style={{
                  padding: '10px 20px',
                  borderRadius: 8,
                  border: 'none',
                  background: 'linear-gradient(135deg, #4DA3FF 0%, #3D8BFF 100%)',
                  color: '#fff',
                  fontFamily: FONT_UI,
                  fontWeight: 600,
                  fontSize: 13,
                  cursor: 'pointer',
                  boxShadow: '0 0 16px rgba(77,163,255,0.3)',
                }}
              >
                Retry
              </button>
              <button
                onClick={() => window.location.assign('/')}
                style={{
                  padding: '10px 20px',
                  borderRadius: 8,
                  border: `1px solid ${PANEL_BORDER}`,
                  background: 'rgba(255,255,255,0.03)',
                  color: '#EEF3FF',
                  fontFamily: FONT_UI,
                  fontWeight: 600,
                  fontSize: 13,
                  cursor: 'pointer',
                }}
              >
                Go Home
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
