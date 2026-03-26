import React from 'react';
import { FONT_MONO, FONT_UI, PANEL_BORDER } from '@/lib/theme';

interface ErrorBoundaryState {
  hasError: boolean;
  errorMessage: string;
}

export default class ErrorBoundary extends React.Component<
  { children: React.ReactNode; title?: string; onRetry?: () => void },
  ErrorBoundaryState
> {
  constructor(props: { children: React.ReactNode; title?: string; onRetry?: () => void }) {
    super(props);
    this.state = { hasError: false, errorMessage: '' };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      errorMessage: error?.message || 'Unknown render error',
    };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught render error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div
          style={{
            width: '100vw',
            minHeight: '100vh',
            background: '#05070B',
            color: '#EEF3FF',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 32,
          }}
        >
          <div
            style={{
              maxWidth: 680,
              width: '100%',
              borderRadius: 14,
              border: '1px solid rgba(251,113,133,0.22)',
              background: 'rgba(251,113,133,0.05)',
              padding: 24,
              boxShadow: '0 20px 60px rgba(0,0,0,0.35)',
            }}
          >
            <div
              style={{
                fontFamily: 'Inter, sans-serif',
                fontWeight: 700,
                fontSize: 20,
                marginBottom: 10,
              }}
            >
              {this.props.title ?? 'Screen Error'}
            </div>
            <div
              style={{
                fontFamily: 'Inter, sans-serif',
                fontSize: 13,
                color: '#C5CDD8',
                marginBottom: 14,
                lineHeight: 1.5,
              }}
            >
              This screen hit a client-side render error instead of loading normally.
            </div>
            <pre
              style={{
                margin: '0 0 16px',
                padding: '12px 14px',
                borderRadius: 10,
                border: `1px solid ${PANEL_BORDER}`,
                background: 'rgba(255,255,255,0.03)',
                whiteSpace: 'pre-wrap',
                wordBreak: 'break-word',
                fontFamily: FONT_MONO,
                fontSize: 12,
                color: '#FCA5A5',
                textAlign: 'left',
                overflowX: 'auto',
              }}
            >
              {this.state.errorMessage}
            </pre>
            <div style={{ display: 'flex', justifyContent: 'center', gap: 10, flexWrap: 'wrap' }}>
              <button
                onClick={() => {
                  if (this.props.onRetry) {
                    this.setState({ hasError: false, errorMessage: '' });
                    this.props.onRetry();
                    return;
                  }
                  window.location.reload();
                }}
                style={{
                  padding: '10px 18px',
                  borderRadius: 8,
                  border: 'none',
                  background: 'linear-gradient(135deg, #4DA3FF 0%, #3D8BFF 100%)',
                  color: '#fff',
                  fontFamily: FONT_UI,
                  fontWeight: 600,
                  fontSize: 13,
                  cursor: 'pointer',
                }}
              >
                Retry
              </button>
              <button
                onClick={() => window.location.assign('/')}
                style={{
                  padding: '10px 18px',
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
