import React, { createContext, useCallback, useContext, useRef, useState } from 'react';

/* ─────────────────────────────────────────────────────
   Minimal toast notification system.
   Usage:
     const toast = useToast();
     toast.success('New best score!');
     toast.error('Connection lost');
     toast.info('Run started');
   ───────────────────────────────────────────────────── */

type ToastVariant = 'success' | 'error' | 'warning' | 'info';

interface Toast {
  id: number;
  message: string;
  variant: ToastVariant;
  exiting?: boolean;
}

interface ToastContextValue {
  success: (message: string) => void;
  error: (message: string) => void;
  warning: (message: string) => void;
  info: (message: string) => void;
}

const VARIANT_STYLES: Record<ToastVariant, { bg: string; border: string; color: string; icon: string }> = {
  success: { bg: 'rgba(74,222,128,0.10)', border: 'rgba(74,222,128,0.3)', color: '#4ADE80', icon: '\u2713' },
  error:   { bg: 'rgba(251,113,133,0.10)', border: 'rgba(251,113,133,0.3)', color: '#FB7185', icon: '\u2717' },
  warning: { bg: 'rgba(251,191,36,0.10)', border: 'rgba(251,191,36,0.3)', color: '#FBBF24', icon: '\u26A0' },
  info:    { bg: 'rgba(77,163,255,0.10)', border: 'rgba(77,163,255,0.3)', color: '#4DA3FF', icon: '\u2139' },
};

const DURATION = 4000;
const EXIT_DURATION = 300;

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within <ToastProvider>');
  return ctx;
}

export default function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(0);

  const dismiss = useCallback((id: number) => {
    setToasts(prev => prev.map(t => t.id === id ? { ...t, exiting: true } : t));
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), EXIT_DURATION);
  }, []);

  const push = useCallback((message: string, variant: ToastVariant) => {
    const id = nextId.current++;
    setToasts(prev => [...prev.slice(-4), { id, message, variant }]);
    setTimeout(() => dismiss(id), DURATION);
  }, [dismiss]);

  const value: ToastContextValue = {
    success: useCallback((m: string) => push(m, 'success'), [push]),
    error:   useCallback((m: string) => push(m, 'error'), [push]),
    warning: useCallback((m: string) => push(m, 'warning'), [push]),
    info:    useCallback((m: string) => push(m, 'info'), [push]),
  };

  return (
    <ToastContext.Provider value={value}>
      {children}

      {/* Toast container — fixed bottom-right */}
      <div
        style={{
          position: 'fixed',
          bottom: 24,
          right: 24,
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
          zIndex: 9999,
          pointerEvents: 'none',
          maxWidth: 380,
        }}
      >
        {toasts.map(toast => {
          const s = VARIANT_STYLES[toast.variant];
          return (
            <div
              key={toast.id}
              style={{
                padding: '10px 14px',
                borderRadius: 9,
                background: s.bg,
                border: `1px solid ${s.border}`,
                backdropFilter: 'blur(12px)',
                display: 'flex',
                alignItems: 'center',
                gap: 9,
                pointerEvents: 'auto',
                cursor: 'pointer',
                opacity: toast.exiting ? 0 : 1,
                transform: toast.exiting ? 'translateX(20px)' : 'translateX(0)',
                transition: `opacity ${EXIT_DURATION}ms ease, transform ${EXIT_DURATION}ms ease`,
                animation: toast.exiting ? 'none' : 'toastSlideIn 0.25s ease-out',
              }}
              onClick={() => dismiss(toast.id)}
            >
              <span style={{ fontSize: 14, color: s.color, flexShrink: 0, lineHeight: 1 }}>
                {s.icon}
              </span>
              <span
                style={{
                  fontFamily: 'Inter, sans-serif',
                  fontSize: 12,
                  fontWeight: 500,
                  color: '#EEF3FF',
                  lineHeight: 1.4,
                }}
              >
                {toast.message}
              </span>
            </div>
          );
        })}
      </div>

      <style>{`
        @keyframes toastSlideIn {
          from { opacity: 0; transform: translateX(30px); }
          to   { opacity: 1; transform: translateX(0); }
        }
      `}</style>
    </ToastContext.Provider>
  );
}
