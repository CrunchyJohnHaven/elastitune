import React from 'react';
import { PANEL_BORDER, PANEL_BG } from '@/lib/theme';

type SkeletonCardProps = {
  lines?: number;
  height?: number;
  compact?: boolean;
  titleWidth?: number | string;
};

export default function SkeletonCard({
  lines = 3,
  height = 88,
  compact = false,
  titleWidth = 160,
}: SkeletonCardProps) {
  return (
    <div
      aria-busy="true"
      aria-live="polite"
      style={{
        padding: compact ? '14px 16px' : '18px 20px',
        borderRadius: 14,
        border: `1px solid ${PANEL_BORDER}`,
        background: PANEL_BG,
        minHeight: height,
      }}
    >
      <style>{`
        @keyframes elastituneSkeleton {
          0% { background-position: 200% 0; }
          100% { background-position: -20% 0; }
        }
      `}</style>
      <div
        style={{
          height: 14,
          width: titleWidth,
          borderRadius: 999,
          background:
            'linear-gradient(90deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.10) 50%, rgba(255,255,255,0.04) 100%)',
          backgroundSize: '220% 100%',
          animation: 'elastituneSkeleton 1.15s ease-in-out infinite',
        }}
      />
      <div style={{ display: 'grid', gap: 10, marginTop: 14 }}>
        {Array.from({ length: lines }).map((_, index) => (
          <div
            key={index}
            style={{
              height: index === lines - 1 ? 10 : 12,
              width: index === lines - 1 ? '78%' : '100%',
              borderRadius: 999,
              background:
                'linear-gradient(90deg, rgba(255,255,255,0.03) 0%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.03) 100%)',
              backgroundSize: '220% 100%',
              animation: 'elastituneSkeleton 1.15s ease-in-out infinite',
              animationDelay: `${index * 0.08}s`,
            }}
          />
        ))}
      </div>
    </div>
  );
}
