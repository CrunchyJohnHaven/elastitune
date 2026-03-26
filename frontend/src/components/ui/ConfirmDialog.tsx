import React from 'react';
import { PANEL_BORDER } from '@/lib/theme';

/* ─────────────────────────────────────────────────────
   Minimal modal confirmation dialog.
   ───────────────────────────────────────────────────── */

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  confirmColor?: string;
  cancelLabel?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel = 'Confirm',
  confirmColor = '#FB7185',
  cancelLabel = 'Cancel',
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  if (!open) return null;

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onCancel}
        style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0,0,0,0.55)',
          backdropFilter: 'blur(4px)',
          zIndex: 9000,
          animation: 'confirmFadeIn 0.15s ease-out',
        }}
      />

      {/* Dialog */}
      <div
        style={{
          position: 'fixed',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: 380,
          maxWidth: 'calc(100vw - 48px)',
          background: 'rgba(10,14,20,0.96)',
          border: `1px solid ${PANEL_BORDER}`,
          borderRadius: 14,
          padding: '24px',
          zIndex: 9001,
          boxShadow: '0 16px 48px rgba(0,0,0,0.5)',
          animation: 'confirmScaleIn 0.2s ease-out',
        }}
      >
        <div
          style={{
            fontFamily: 'Inter, sans-serif',
            fontWeight: 700,
            fontSize: 16,
            color: '#EEF3FF',
            marginBottom: 8,
          }}
        >
          {title}
        </div>
        <div
          style={{
            fontFamily: 'Inter, sans-serif',
            fontSize: 13,
            color: '#9AA4B2',
            lineHeight: 1.55,
            marginBottom: 20,
          }}
        >
          {description}
        </div>
        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
          <button
            onClick={onCancel}
            style={{
              padding: '8px 16px',
              borderRadius: 7,
              border: `1px solid ${PANEL_BORDER}`,
              background: 'transparent',
              color: '#9AA4B2',
              fontFamily: 'Inter, sans-serif',
              fontSize: 12,
              fontWeight: 500,
              cursor: 'pointer',
              transition: 'background 0.15s',
            }}
            onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = 'rgba(255,255,255,0.05)'; }}
            onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = 'transparent'; }}
          >
            {cancelLabel}
          </button>
          <button
            onClick={onConfirm}
            style={{
              padding: '8px 16px',
              borderRadius: 7,
              border: 'none',
              background: `${confirmColor}20`,
              color: confirmColor,
              fontFamily: 'Inter, sans-serif',
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'background 0.15s',
            }}
            onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.background = `${confirmColor}35`; }}
            onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.background = `${confirmColor}20`; }}
          >
            {confirmLabel}
          </button>
        </div>
      </div>

      <style>{`
        @keyframes confirmFadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes confirmScaleIn { from { opacity: 0; transform: translate(-50%, -50%) scale(0.95); } to { opacity: 1; transform: translate(-50%, -50%) scale(1); } }
      `}</style>
    </>
  );
}
