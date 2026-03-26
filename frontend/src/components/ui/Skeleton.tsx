import React from 'react';
import { PANEL_BORDER, SURFACE_ELEVATED } from '@/lib/theme';

export function SkeletonBlock({
  height = 14,
  width = '100%',
  radius = 8,
}: {
  height?: number;
  width?: number | string;
  radius?: number;
}) {
  return (
    <div
      aria-hidden="true"
      style={{
        height,
        width,
        borderRadius: radius,
        background:
          'linear-gradient(90deg, rgba(255,255,255,0.02) 0%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.02) 100%)',
        backgroundSize: '220% 100%',
        animation: 'skeletonPulse 1.2s ease-in-out infinite',
      }}
    />
  );
}

export function SkeletonCard({
  children,
  minHeight = 180,
}: {
  children?: React.ReactNode;
  minHeight?: number;
}) {
  return (
    <div
      style={{
        minHeight,
        padding: 18,
        borderRadius: 14,
        background: SURFACE_ELEVATED,
        border: `1px solid ${PANEL_BORDER}`,
      }}
    >
      {children}
    </div>
  );
}

export function SkeletonPage({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children?: React.ReactNode;
}) {
  return (
    <div
      style={{
        minHeight: '100vh',
        background: '#05070B',
        color: '#EEF3FF',
        padding: '0 0 56px',
      }}
    >
      <style>{`
        @keyframes skeletonPulse {
          0% { background-position: 200% 0; }
          100% { background-position: -20% 0; }
        }
      `}</style>
      <div
        style={{
          padding: '22px 32px',
          borderBottom: `1px solid ${PANEL_BORDER}`,
          background: 'rgba(10,14,20,0.85)',
        }}
      >
        <SkeletonBlock height={24} width={260} />
        {subtitle ? (
          <div style={{ marginTop: 10 }}>
            <SkeletonBlock height={12} width={420} />
          </div>
        ) : null}
        <div style={{ marginTop: 6, fontFamily: 'Inter, sans-serif', fontSize: 12, color: '#9AA4B2' }}>
          {title}
        </div>
      </div>
      <div style={{ padding: '24px 32px' }}>{children}</div>
    </div>
  );
}
