import React, { useRef, useEffect } from 'react';
import { useCanvasSize } from '@/hooks/useCanvasSize';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { PREVIEW_PERSONAS } from '@/demo/previewSeed';
import { personaColor, personaGlowColor } from '@/lib/theme';

const POSITION_MAP = [
  { x: 0.24, y: 0.22 },
  { x: 0.75, y: 0.18 },
  { x: 0.84, y: 0.56 },
  { x: 0.34, y: 0.78 },
  { x: 0.54, y: 0.7 },
] as const;

const QUERY_LABELS = [
  '"baseline recall"',
  '"title boost"',
  '"hybrid rerank"',
  '"exact intent"',
  '"no-harm cohort"',
] as const;

export default function DemoPreviewCanvas() {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef = useRef<number>(0);
  const reducedMotion = useReducedMotion();

  const size = useCanvasSize(containerRef as React.RefObject<HTMLElement>);

  // Resize canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || size.width === 0 || size.height === 0) return;
    canvas.width = Math.round(size.width * size.dpr);
    canvas.height = Math.round(size.height * size.dpr);
    canvas.style.width = `${size.width}px`;
    canvas.style.height = `${size.height}px`;
  }, [size]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const animate = (timestamp: number) => {
      const t = timestamp / 1000;
      const ctx = canvas.getContext('2d');
      if (!ctx || size.width === 0 || size.height === 0) {
        rafRef.current = requestAnimationFrame(animate);
        return;
      }

      const { width, height, dpr } = size;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      const cx = width / 2;
      const cy = height / 2;
      const systemRadius = Math.min(width, height) * 0.32;
      const activeIndex = Math.floor(t * 0.52) % PREVIEW_PERSONAS.length;
      const pulse = reducedMotion ? 0.65 : 0.55 + Math.sin(t * 1.7) * 0.1;

      // Clear
      ctx.fillStyle = '#05070B';
      ctx.fillRect(0, 0, width, height);

      const bgGradient = ctx.createRadialGradient(
        cx,
        cy,
        Math.min(width, height) * 0.05,
        cx,
        cy,
        Math.max(width, height) * 0.78,
      );
      bgGradient.addColorStop(0, 'rgba(13,18,28,0.08)');
      bgGradient.addColorStop(0.55, 'rgba(8,11,17,0.15)');
      bgGradient.addColorStop(1, 'rgba(0,0,0,0.62)');
      ctx.fillStyle = bgGradient;
      ctx.fillRect(0, 0, width, height);

      for (let i = 1; i <= 5; i++) {
        const r = systemRadius * (i / 5);
        ctx.beginPath();
        ctx.arc(cx, cy, r, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(255,255,255,0.045)';
        ctx.lineWidth = i === 5 ? 0.8 : 0.6;
        ctx.setLineDash([3, 7]);
        ctx.stroke();
        ctx.setLineDash([]);
      }

      const nodePositions = PREVIEW_PERSONAS.map((persona, index) => {
        const mapped = POSITION_MAP[index] ?? POSITION_MAP[POSITION_MAP.length - 1];
        const driftX = reducedMotion ? 0 : Math.sin(t * 0.35 + index) * 4;
        const driftY = reducedMotion ? 0 : Math.cos(t * 0.28 + index * 0.8) * 3;
        return {
          persona,
          x: width * mapped.x + driftX,
          y: height * mapped.y + driftY,
        };
      });

      nodePositions.forEach((node, index) => {
        const isActive = index === activeIndex;
        const beamProgress = reducedMotion ? 1 : (Math.sin(t * 2.4) + 1) / 2;

        ctx.beginPath();
        ctx.moveTo(node.x, node.y);
        ctx.lineTo(cx, cy);
        ctx.strokeStyle = isActive ? 'rgba(77,163,255,0.42)' : 'rgba(255,255,255,0.06)';
        ctx.lineWidth = isActive ? 1.2 : 0.8;
        ctx.setLineDash(isActive ? [4, 6] : [2, 10]);
        ctx.stroke();
        ctx.setLineDash([]);

        if (isActive) {
          const px = node.x + (cx - node.x) * beamProgress;
          const py = node.y + (cy - node.y) * beamProgress;
          const trail = ctx.createRadialGradient(px, py, 0, px, py, 18);
          trail.addColorStop(0, 'rgba(255,255,255,0.75)');
          trail.addColorStop(0.35, 'rgba(77,163,255,0.45)');
          trail.addColorStop(1, 'rgba(77,163,255,0)');
          ctx.fillStyle = trail;
          ctx.beginPath();
          ctx.arc(px, py, 18, 0, Math.PI * 2);
          ctx.fill();

          ctx.font = '11px JetBrains Mono, monospace';
          ctx.fillStyle = 'rgba(124,231,255,0.88)';
          ctx.textAlign = 'center';
          ctx.fillText(
            QUERY_LABELS[index] ?? '"query intent"',
            (node.x + cx) / 2,
            (node.y + cy) / 2 - 12,
          );
        }

        const halo = ctx.createRadialGradient(node.x, node.y, 0, node.x, node.y, isActive ? 26 : 20);
        halo.addColorStop(0, isActive ? 'rgba(255,255,255,0.18)' : personaGlowColor(node.persona.colorSeed));
        halo.addColorStop(1, 'rgba(0,0,0,0)');
        ctx.fillStyle = halo;
        ctx.beginPath();
        ctx.arc(node.x, node.y, isActive ? 26 : 20, 0, Math.PI * 2);
        ctx.fill();

        if (isActive && !reducedMotion) {
          ctx.beginPath();
          ctx.arc(node.x, node.y, 9 + pulse * 14, 0, Math.PI * 2);
          ctx.strokeStyle = `rgba(77,163,255,${0.18 + pulse * 0.22})`;
          ctx.lineWidth = 1.1;
          ctx.stroke();
        }

        ctx.beginPath();
        ctx.arc(node.x, node.y, isActive ? 6.6 : 5.2, 0, Math.PI * 2);
        ctx.fillStyle = isActive ? 'rgba(255,255,255,0.94)' : personaColor(node.persona.colorSeed, 0.88);
        ctx.fill();

        ctx.font = '9px JetBrains Mono, monospace';
        ctx.fillStyle = isActive ? 'rgba(238,243,255,0.8)' : 'rgba(154,164,178,0.55)';
        ctx.textAlign = 'center';
        ctx.fillText(node.persona.role.toUpperCase(), node.x, node.y + 18);
      });

      // Center orb
      const coreG = ctx.createRadialGradient(cx, cy, 0, cx, cy, 28);
      coreG.addColorStop(0, 'rgba(255,255,255,0.9)');
      coreG.addColorStop(0.35, 'rgba(200,220,255,0.5)');
      coreG.addColorStop(1, 'rgba(77,163,255,0)');
      ctx.fillStyle = coreG;
      ctx.beginPath();
      ctx.arc(cx, cy, 22, 0, Math.PI * 2);
      ctx.fill();

      ctx.beginPath();
      ctx.arc(cx, cy, 8, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(255,255,255,0.95)';
      ctx.fill();

      // Center label
      ctx.font = '9px JetBrains Mono, monospace';
      ctx.fillStyle = 'rgba(154,164,178,0.6)';
      ctx.textAlign = 'center';
      ctx.fillText('ES', cx, cy + 24);

      ctx.font = '10px JetBrains Mono, monospace';
      ctx.fillStyle = 'rgba(74,222,128,0.65)';
      ctx.fillText('live benchmark', cx, cy - 26);

      rafRef.current = requestAnimationFrame(animate);
    };

    rafRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(rafRef.current);
  }, [size, reducedMotion]);

  return (
    <div
      ref={containerRef}
      style={{
        width: '100%',
        height: '100%',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <canvas
        ref={canvasRef}
        style={{ display: 'block', width: '100%', height: '100%' }}
      />
    </div>
  );
}
