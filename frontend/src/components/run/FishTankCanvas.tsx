import React, { useRef, useEffect, useCallback, useState } from 'react';
import { useAppStore } from '@/store/useAppStore';
import { useCanvasSize } from '@/hooks/useCanvasSize';
import { useReducedMotion } from '@/hooks/useReducedMotion';
import { FONT_MONO, FONT_UI, STATE_COLORS, STATE_GLOW_COLORS } from '@/lib/theme';
import type { PersonaViewModel } from '@/types/contracts';
import TooltipPortal from './TooltipPortal';

interface Wave {
  startTime: number;
  type: 'accepted' | 'rejected';
}

/** Client-side animation event that persists with a visible duration */
interface AnimEvent {
  personaId: string;
  type: 'beam' | 'success' | 'failure' | 'partial';
  startTime: number;   // performance.now() / 1000
  duration: number;     // seconds
  query?: string;
}

/** Floating query term that drifts near the center after a beam lands */
interface QueryGhost {
  text: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  startTime: number;
  duration: number;
  color: string;
}

const BASE_RADIUS_RATIO = 0.12;
const RING_GAP = 54;
const NUM_RINGS = 6;
const BEAM_DURATION = 1.6;
const FLASH_DURATION = 1.2;
const DEPARTMENT_ORDER = [
  'Security',
  'Engineering',
  'IT',
  'Executive',
  'Legal',
  'DevOps',
  'Compliance',
  'HR',
  'Product',
  'External',
];

function isFiniteNumber(value: number) {
  return Number.isFinite(value);
}

function beginCircle(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  radius: number
) {
  if (!isFiniteNumber(x) || !isFiniteNumber(y) || !isFiniteNumber(radius) || radius <= 0) {
    return false;
  }

  ctx.beginPath();
  ctx.arc(x, y, radius, 0, Math.PI * 2);
  return true;
}

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number
) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.lineTo(x + w - r, y);
  ctx.quadraticCurveTo(x + w, y, x + w, y + r);
  ctx.lineTo(x + w, y + h - r);
  ctx.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  ctx.lineTo(x + r, y + h);
  ctx.quadraticCurveTo(x, y + h, x, y + h - r);
  ctx.lineTo(x, y + r);
  ctx.quadraticCurveTo(x, y, x + r, y);
  ctx.closePath();
}

function stableHash(value: string) {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = ((hash << 5) - hash + value.charCodeAt(index)) | 0;
  }
  return Math.abs(hash);
}

function formatQueriesTested(evalCaseCount: number, experimentsRun: number) {
  if (evalCaseCount <= 0) return '—';
  const cumulative = evalCaseCount * Math.max(experimentsRun + 1, 1);
  return `${Intl.NumberFormat('en-US').format(cumulative)}/${Intl.NumberFormat('en-US').format(evalCaseCount)}`;
}

function compareDepartments(a: string, b: string) {
  const aIndex = DEPARTMENT_ORDER.indexOf(a);
  const bIndex = DEPARTMENT_ORDER.indexOf(b);
  const normalizedA = aIndex === -1 ? DEPARTMENT_ORDER.length + stableHash(a) : aIndex;
  const normalizedB = bIndex === -1 ? DEPARTMENT_ORDER.length + stableHash(b) : bIndex;
  return normalizedA - normalizedB;
}

function buildClusterLayout(
  personas: PersonaViewModel[],
  cx: number,
  cy: number,
  width: number,
  height: number,
  timeSeconds: number,
  reducedMotion: boolean
) {
  const byDepartment = new Map<string, PersonaViewModel[]>();
  personas.forEach((persona) => {
    const key = persona.department || 'General';
    const bucket = byDepartment.get(key) ?? [];
    bucket.push(persona);
    byDepartment.set(key, bucket);
  });

  const departments = Array.from(byDepartment.keys()).sort(compareDepartments);
  const anchorRadius = Math.max(118, Math.min(width, height) * 0.3);
  const anchors = departments.map((department, index) => {
    const angle = (-Math.PI / 2) + (index / Math.max(departments.length, 1)) * Math.PI * 2;
    return {
      department,
      angle,
      x: cx + Math.cos(angle) * anchorRadius,
      y: cy + Math.sin(angle) * anchorRadius,
      count: byDepartment.get(department)?.length ?? 0,
    };
  });

  const positions: Array<{ x: number; y: number; persona: PersonaViewModel }> = [];
  anchors.forEach((anchor) => {
    const cluster = (byDepartment.get(anchor.department) ?? []).slice().sort((left, right) => (
      left.name.localeCompare(right.name)
    ));
    const cols = Math.min(4, Math.max(2, Math.ceil(Math.sqrt(cluster.length))));
    const rows = Math.max(1, Math.ceil(cluster.length / cols));
    const tangentAngle = anchor.angle + Math.PI / 2;

    cluster.forEach((persona, clusterIndex) => {
      const col = clusterIndex % cols;
      const row = Math.floor(clusterIndex / cols);
      const tangentOffset = (col - (cols - 1) / 2) * 28;
      const radialOffset = (row - (rows - 1) / 2) * 28;
      const activityOffset = reducedMotion || persona.state === 'idle'
        ? 0
        : Math.sin(timeSeconds * 6 + persona.colorSeed) * 2.5;
      const x = anchor.x
        + Math.cos(tangentAngle) * tangentOffset
        + Math.cos(anchor.angle) * (radialOffset + activityOffset);
      const y = anchor.y
        + Math.sin(tangentAngle) * tangentOffset
        + Math.sin(anchor.angle) * (radialOffset + activityOffset);

      positions.push({ x, y, persona });
    });
  });

  return { positions, anchors };
}

export default function FishTankCanvas() {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const bgCanvasRef = useRef<HTMLCanvasElement | null>(null); // offscreen bg cache
  const bgSizeRef = useRef({ w: 0, h: 0 }); // track when to redraw bg
  const rafRef = useRef<number>(0);
  const wavesRef = useRef<Wave[]>([]);
  const animEventsRef = useRef<AnimEvent[]>([]);
  const queryGhostsRef = useRef<QueryGhost[]>([]);
  const prevStatesRef = useRef<Map<string, string>>(new Map());
  const nextAmbientRef = useRef(0); // next time to spawn an ambient particle
  const prevExperimentsLengthRef = useRef(0);
  const mouseRef = useRef<{ x: number; y: number } | null>(null);
  const hoveredIdRef = useRef<string | null>(null);
  const personaPositionsRef = useRef<Map<string, { x: number; y: number }>>(new Map());
  const personaLookupRef = useRef<Map<string, PersonaViewModel>>(new Map());
  const tooltipThrottleRef = useRef(0);

  const size = useCanvasSize(containerRef as React.RefObject<HTMLElement>);
  const reducedMotion = useReducedMotion();

  const {
    runSnapshot,
    selectedPersonaId,
    hoveredPersonaId,
    setSelectedPersona,
    setHoveredPersona,
  } = useAppStore();

  // Tooltip state (only updated ~10fps to avoid render spam)
  const [tooltipState, setTooltipState] = useState<{
    persona: PersonaViewModel | null;
    x: number;
    y: number;
    visible: boolean;
  }>({ persona: null, x: 0, y: 0, visible: false });

  const personas = runSnapshot?.personas ?? [];
  const experiments = runSnapshot?.experiments ?? [];

  useEffect(() => {
    personaLookupRef.current = new Map(personas.map(persona => [persona.id, persona]));
  }, [personas]);

  // Watch for new kept experiments → trigger wave
  useEffect(() => {
    const newLen = experiments.length;
    if (newLen > prevExperimentsLengthRef.current) {
      const newest = experiments[newLen - 1];
      if (newest) {
        const type = newest.decision === 'kept' ? 'accepted' : 'rejected';
        wavesRef.current.push({
          startTime: performance.now() / 1000,
          type,
        });
      }
    }
    prevExperimentsLengthRef.current = newLen;
  }, [experiments]);

  // Handle canvas resize
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || size.width === 0 || size.height === 0) return;
    canvas.width = Math.round(size.width * size.dpr);
    canvas.height = Math.round(size.height * size.dpr);
    canvas.style.width = `${size.width}px`;
    canvas.style.height = `${size.height}px`;
  }, [size]);

  // Mouse move handler — throttled store update
  const handleMouseMove = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;
      mouseRef.current = { x: mx, y: my };

      // Throttle store update and tooltip update to ~10fps
      const now = performance.now();
      if (now - tooltipThrottleRef.current < 100) return;
      tooltipThrottleRef.current = now;

      // Find closest persona within 30px
      let closestId: string | null = null;
      let closestDist = 30;
      personaPositionsRef.current.forEach((pos, id) => {
        const dx = pos.x - mx;
        const dy = pos.y - my;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < closestDist) {
          closestDist = dist;
          closestId = id;
        }
      });

      if (closestId !== hoveredIdRef.current) {
        hoveredIdRef.current = closestId;
        setHoveredPersona(closestId);
      }

      if (closestId) {
        const p = personaLookupRef.current.get(closestId);
        const pos = personaPositionsRef.current.get(closestId);
        if (p && pos) {
          setTooltipState({
            persona: p,
            x: e.clientX,
            y: e.clientY,
            visible: true,
          });
        }
      } else {
        setTooltipState(prev => ({ ...prev, visible: false }));
      }
    },
    [setHoveredPersona]
  );

  const handleMouseLeave = useCallback(() => {
    mouseRef.current = null;
    hoveredIdRef.current = null;
    setHoveredPersona(null);
    setTooltipState(prev => ({ ...prev, visible: false }));
  }, [setHoveredPersona]);

  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLCanvasElement>) => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left;
      const my = e.clientY - rect.top;

      let closestId: string | null = null;
      let closestDist = 30;
      personaPositionsRef.current.forEach((pos, id) => {
        const dx = pos.x - mx;
        const dy = pos.y - my;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < closestDist) {
          closestDist = dist;
          closestId = id;
        }
      });

      setSelectedPersona(closestId === selectedPersonaId ? null : closestId);
    },
    [selectedPersonaId, setSelectedPersona]
  );

  // Animation loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const animate = (timestamp: number) => {
      try {
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
        const baseRadius = Math.min(width, height) * BASE_RADIUS_RATIO;

        // --- Pre-render static background to offscreen canvas (once per resize) ---
        if (!bgCanvasRef.current || bgSizeRef.current.w !== width || bgSizeRef.current.h !== height) {
          const bg = document.createElement('canvas');
          bg.width = Math.round(width * dpr);
          bg.height = Math.round(height * dpr);
          const bgCtx = bg.getContext('2d')!;
          bgCtx.setTransform(dpr, 0, 0, dpr, 0, 0);

        // Background fill
        bgCtx.fillStyle = '#05070B';
        bgCtx.fillRect(0, 0, width, height);

        // Vignette
        const vignette = bgCtx.createRadialGradient(
          cx, cy, Math.min(width, height) * 0.2,
          cx, cy, Math.max(width, height) * 0.8
        );
        vignette.addColorStop(0, 'rgba(0,0,0,0)');
        vignette.addColorStop(1, 'rgba(0,0,0,0.55)');
        bgCtx.fillStyle = vignette;
        bgCtx.fillRect(0, 0, width, height);

        // Dot grid
        bgCtx.fillStyle = 'rgba(255,255,255,0.025)';
        const gridSpacing = 40;
        for (let gx = 0; gx < width; gx += gridSpacing) {
          for (let gy = 0; gy < height; gy += gridSpacing) {
            bgCtx.beginPath();
            bgCtx.arc(gx, gy, 0.75, 0, Math.PI * 2);
            bgCtx.fill();
          }
        }

        // Orbit rings
        for (let i = 0; i < NUM_RINGS; i++) {
          const r = baseRadius + i * RING_GAP;
          bgCtx.beginPath();
          bgCtx.arc(cx, cy, r, 0, Math.PI * 2);
          bgCtx.strokeStyle = 'rgba(255,255,255,0.05)';
          bgCtx.lineWidth = 0.5;
          bgCtx.setLineDash([4, 8]);
          bgCtx.stroke();
          bgCtx.setLineDash([]);
        }

          bgCanvasRef.current = bg;
          bgSizeRef.current = { w: width, h: height };
        }

        // Blit cached background (single drawImage instead of ~600 arcs)
        ctx.drawImage(bgCanvasRef.current, 0, 0, width, height);

      // --- Compute persona positions ---
      const storeState = useAppStore.getState();
      const currentSnapshot = storeState.runSnapshot;
      const currentPersonas = storeState.runSnapshot?.personas ?? [];
      const currentSelectedId = storeState.selectedPersonaId;
      const currentHoveredId = storeState.hoveredPersonaId;
      const currentStage = currentSnapshot?.stage ?? 'idle';
      const currentEvalCaseCount = currentSnapshot?.summary?.baselineEvalCount ?? 0;
      const currentExperimentsRun = currentSnapshot?.metrics?.experimentsRun ?? 0;
        const { positions, anchors } = buildClusterLayout(
          currentPersonas,
          cx,
          cy,
          width,
          height,
          t,
          reducedMotion
        );

        // Update position cache for mouse hit-testing
        personaPositionsRef.current.clear();
        positions.forEach(({ x, y, persona }) => {
          personaPositionsRef.current.set(persona.id, { x, y });
        });

      // --- Department pods / operational spokes ---
      ctx.save();
      anchors.forEach((anchor) => {
        const labelX = cx + Math.cos(anchor.angle) * (baseRadius + NUM_RINGS * RING_GAP + 20);
        const labelY = cy + Math.sin(anchor.angle) * (baseRadius + NUM_RINGS * RING_GAP + 20);
        const clusterRadius = 26 + anchor.count * 4;

        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(anchor.x, anchor.y);
        ctx.strokeStyle = 'rgba(255,255,255,0.045)';
        ctx.lineWidth = 1;
        ctx.setLineDash([3, 10]);
        ctx.stroke();
        ctx.setLineDash([]);

        if (beginCircle(ctx, anchor.x, anchor.y, clusterRadius)) {
          ctx.strokeStyle = 'rgba(255,255,255,0.05)';
          ctx.lineWidth = 0.8;
          ctx.stroke();
        }

        ctx.font = '9px JetBrains Mono, monospace';
        ctx.fillStyle = 'rgba(154,164,178,0.55)';
        ctx.textAlign = labelX < cx ? 'right' : 'left';
        ctx.fillText(anchor.department.toUpperCase(), labelX, labelY);
      });
      ctx.restore();

      // --- Detect persona state transitions → create staggered animation events ---
      const prevStates = prevStatesRef.current;
      let staggerIndex = 0;
      currentPersonas.forEach(p => {
        const prev = prevStates.get(p.id) ?? 'idle';
        if (p.state !== prev && p.state !== 'idle') {
          if (p.state === 'success' || p.state === 'failure' || p.state === 'partial' || p.state === 'searching') {
            // Stagger each persona's beam by 0.4s so they fire sequentially
            const staggerDelay = staggerIndex * 0.4;
            staggerIndex++;
            animEventsRef.current.push({
              personaId: p.id,
              type: 'beam',
              startTime: t + staggerDelay,
              duration: BEAM_DURATION,
              query: p.lastQuery ?? undefined,
            });
            if (p.state === 'success' || p.state === 'failure' || p.state === 'partial') {
              animEventsRef.current.push({
                personaId: p.id,
                type: p.state as 'success' | 'failure' | 'partial',
                startTime: t + staggerDelay + BEAM_DURATION * 0.6,
                duration: FLASH_DURATION,
                query: p.lastQuery ?? undefined,
              });
            }
          }
        }
        prevStates.set(p.id, p.state);
      });

      // --- Ambient particles: occasional request dots between experiment batches ---
      const runStage = storeState.runSnapshot?.stage;
      if (runStage === 'running' && currentPersonas.length > 0
          && t > nextAmbientRef.current && animEventsRef.current.length < 16) {
        const hash = (seed: number) => ((Math.sin(seed * 9301.7 + 4973.1) * 49297.3) % 1 + 1) % 1;
        const idx = Math.floor(hash(t) * currentPersonas.length);
        const ambientP = currentPersonas[idx];
        const qIdx = Math.floor(hash(t + 777) * (ambientP.queries?.length ?? 1));
        animEventsRef.current.push({
          personaId: ambientP.id,
          type: 'beam',
          startTime: t,
          duration: BEAM_DURATION * 0.7,
          query: ambientP.queries?.[qIdx] ?? undefined,
        });
        // Next ambient in 1.0-2.0s
        nextAmbientRef.current = t + 1.0 + hash(t + 333) * 1.0;
      }

      // Prune expired animation events
      animEventsRef.current = animEventsRef.current.filter(
        ev => t < ev.startTime + ev.duration
      );

      // Spawn query ghost when a result flash starts (beam just landed at core)
      if (!reducedMotion && queryGhostsRef.current.length < 12) {
        animEventsRef.current.forEach(ev => {
          if ((ev.type === 'success' || ev.type === 'failure' || ev.type === 'partial')
              && ev.query && Math.abs(t - ev.startTime) < 0.05) {
            const angle = Math.random() * Math.PI * 2;
            const speed = 8 + Math.random() * 12;
            const color = ev.type === 'success'
              ? 'rgba(74,222,128,0.55)'
              : ev.type === 'failure'
              ? 'rgba(251,113,133,0.45)'
              : 'rgba(251,191,36,0.5)';
            queryGhostsRef.current.push({
              text: ev.query,
              x: cx + (Math.random() - 0.5) * 20,
              y: cy + (Math.random() - 0.5) * 20,
              vx: Math.cos(angle) * speed,
              vy: Math.sin(angle) * speed,
              startTime: t,
              duration: 2.5,
              color,
            });
          }
        });
      }

      // Update and prune query ghosts
      queryGhostsRef.current = queryGhostsRef.current.filter(g => t < g.startTime + g.duration);
      queryGhostsRef.current.forEach(g => {
        const dt = 1 / 60; // approx frame time
        g.x += g.vx * dt;
        g.y += g.vy * dt;
        g.vx *= 0.97; // dampen
        g.vy *= 0.97;
      });

      // --- Animation events: search beams and result flashes (client-side timed) ---
      if (!reducedMotion) {
        const posMap = new Map(positions.map(p => [p.persona.id, p]));
        const activeBeamByPersonaId = new Map<string, AnimEvent>();
        const activeResultByPersonaId = new Map<string, AnimEvent>();
        const activeAnimIds = new Set<string>();

        for (const event of animEventsRef.current) {
          if (t < event.startTime || t >= event.startTime + event.duration) continue;
          activeAnimIds.add(event.personaId);
          if (event.type === 'beam') {
            activeBeamByPersonaId.set(event.personaId, event);
          } else if (!activeResultByPersonaId.has(event.personaId)) {
            activeResultByPersonaId.set(event.personaId, event);
          }
        }

        animEventsRef.current.forEach(ev => {
          const pos = posMap.get(ev.personaId);
          if (!pos) return;
          const { x, y } = pos;
          const elapsed = t - ev.startTime;
          if (elapsed < 0) return; // not started yet (delayed flash)
          const progress = Math.min(elapsed / ev.duration, 1);

          if (ev.type === 'beam') {
            // Search beam: dashed line from persona to core with traveling dot
            const dx = cx - x;
            const dy = cy - y;
            const beamProgress = Math.min(progress * 1.5, 1); // beam reaches core at 67% of duration
            const fadeAlpha = progress > 0.7 ? (1 - progress) / 0.3 : 1;

            // Dashed line (growing toward core)
            const endX = x + dx * beamProgress;
            const endY = y + dy * beamProgress;
            ctx.save();
            ctx.beginPath();
            ctx.moveTo(x, y);
            ctx.lineTo(endX, endY);
            ctx.strokeStyle = `rgba(77,163,255,${0.25 * fadeAlpha})`;
            ctx.lineWidth = 1.2;
            ctx.setLineDash([5, 8]);
            ctx.lineDashOffset = -t * 40;
            ctx.stroke();
            ctx.setLineDash([]);
            ctx.restore();

            // Bright leading dot (no gradient — cheaper)
            const dotX = x + dx * beamProgress;
            const dotY = y + dy * beamProgress;
            if (beginCircle(ctx, dotX, dotY, 3.5)) {
              ctx.fillStyle = `rgba(77,163,255,${0.9 * fadeAlpha})`;
              ctx.fill();
            }
            // Soft halo via larger semi-transparent circle
            if (beginCircle(ctx, dotX, dotY, 7)) {
              ctx.fillStyle = `rgba(77,163,255,${0.15 * fadeAlpha})`;
              ctx.fill();
            }

            // Query text floating near the dot (first half of beam only)
            if (ev.query && beamProgress < 0.7 && beamProgress > 0.1) {
              const qText = ev.query.length > 18 ? ev.query.substring(0, 18) + '…' : ev.query;
              ctx.font = '9px JetBrains Mono, monospace';
              ctx.fillStyle = `rgba(77,163,255,${0.7 * fadeAlpha})`;
              ctx.textAlign = 'center';
              ctx.fillText(`"${qText}"`, dotX, dotY - 10);
            }
          } else if (ev.type === 'success') {
            // Green expanding ring
            const r = 4 + progress * 22;
            const alpha = (1 - progress) * 0.75;
            if (beginCircle(ctx, x, y, r)) {
              ctx.strokeStyle = `rgba(74,222,128,${alpha})`;
              ctx.lineWidth = 2;
              ctx.stroke();
            }
            // Inner flash
            if (progress < 0.3) {
              const flashAlpha = (1 - progress / 0.3) * 0.4;
              if (beginCircle(ctx, x, y, 6)) {
                ctx.fillStyle = `rgba(74,222,128,${flashAlpha})`;
                ctx.fill();
              }
            }
          } else if (ev.type === 'failure') {
            // Red expanding ring
            const r = 4 + progress * 16;
            const alpha = (1 - progress) * 0.65;
            if (beginCircle(ctx, x, y, r)) {
              ctx.strokeStyle = `rgba(251,113,133,${alpha})`;
              ctx.lineWidth = 2;
              ctx.stroke();
            }
          } else if (ev.type === 'partial') {
            // Amber expanding ring
            const r = 4 + progress * 18;
            const alpha = (1 - progress) * 0.6;
            if (beginCircle(ctx, x, y, r)) {
              ctx.strokeStyle = `rgba(251,191,36,${alpha})`;
              ctx.lineWidth = 1.5;
              ctx.stroke();
            }
          }
        });
      }

      // --- Draw glow halos (simple circles, no gradients for perf) ---
      positions.forEach(({ x, y, persona }) => {
        const isSelected = persona.id === currentSelectedId;
        const isHovered = persona.id === currentHoveredId;
        const hue = (persona.colorSeed * 137.508) % 360;

        // Ambient breathing glow for idle — slow per-persona sine wave
        const breathe = 0.5 + 0.5 * Math.sin(t * 0.9 + persona.colorSeed * 2.4);
        const idleGlowAlpha = 0.06 + breathe * 0.1;
        if (beginCircle(ctx, x, y, isSelected || isHovered ? 36 : 18)) {
          ctx.fillStyle = persona.state === 'idle'
            ? `hsla(${hue.toFixed(0)}, 65%, 60%, ${idleGlowAlpha})`
            : STATE_GLOW_COLORS[persona.state];
          ctx.fill();
        }

        // Extra large ring for selected/hovered
        if (isSelected || isHovered) {
          if (beginCircle(ctx, x, y, 42)) {
            ctx.fillStyle = `hsla(${hue.toFixed(0)}, 65%, 60%, 0.04)`;
            ctx.fill();
          }
        }
      });

      // --- Pulse rings for personas with active beam events ---
      if (!reducedMotion) {
        const activeBeamIds = new Set<string>();
        for (const event of animEventsRef.current) {
          if (event.type === 'beam' && t >= event.startTime && t < event.startTime + event.duration) {
            activeBeamIds.add(event.personaId);
          }
        }
        positions.forEach(({ x, y, persona }) => {
          if (!activeBeamIds.has(persona.id)) return;
          const progress = (t % 0.9) / 0.9;
          const pulseR = 5 + progress * 22;
          const alpha = (1 - progress) * 0.55;
          if (beginCircle(ctx, x, y, pulseR)) {
            ctx.strokeStyle = `rgba(77, 163, 255, ${alpha})`;
            ctx.lineWidth = 1.5;
            ctx.stroke();
          }
        });
      }

      // --- Draw agent cores ---
      positions.forEach(({ x, y, persona }) => {
        const isSelected = persona.id === currentSelectedId;
        const isHovered = persona.id === currentHoveredId;
        // Use persona's unique color when idle, state color when active
        const hue = (persona.colorSeed * 137.508) % 360;
        const sat = 65 + (persona.colorSeed % 20);
        const lit = 55 + (persona.colorSeed % 15);
        const coreColor = persona.state === 'idle'
          ? `hsla(${hue.toFixed(0)}, ${sat}%, ${lit}%, 0.85)`
          : STATE_COLORS[persona.state];
        const coreR = isSelected ? 7 : isHovered ? 6 : 5;

        // Hover ring
        if (isHovered || isSelected) {
          if (beginCircle(ctx, x, y, coreR + 5)) {
            ctx.strokeStyle = 'rgba(255,255,255,0.35)';
            ctx.lineWidth = 1.5;
            ctx.stroke();
          }
        }

        if (beginCircle(ctx, x, y, coreR)) {
          ctx.fillStyle = coreColor;
          ctx.fill();
        }

        // Highlight fleck on every dot
        if (beginCircle(ctx, x - coreR * 0.25, y - coreR * 0.25, coreR * 0.3)) {
          ctx.fillStyle = isSelected || isHovered ? 'rgba(255,255,255,0.7)' : 'rgba(255,255,255,0.35)';
          ctx.fill();
        }
      });

      // --- Wave effects ---
      wavesRef.current = wavesRef.current.filter(w => {
        if (reducedMotion) return false;
        const elapsed = t - w.startTime;
        const duration = 0.9;
        if (elapsed >= duration) return false;

        const progress = elapsed / duration;
        const maxR = baseRadius + (NUM_RINGS - 1) * RING_GAP + 30;
        const r = progress * maxR;
        const alpha = (1 - progress) * 0.38;
        const color =
          w.type === 'accepted'
            ? `rgba(74, 222, 128, ${alpha})`
            : `rgba(251, 113, 133, ${alpha})`;

        if (beginCircle(ctx, cx, cy, r)) {
          ctx.strokeStyle = color;
          ctx.lineWidth = 2;
          ctx.stroke();
        }

        // Second trailing ring
        const r2 = Math.max(0, progress * maxR - 20);
        const alpha2 = (1 - progress) * 0.18;
        const color2 =
          w.type === 'accepted'
            ? `rgba(74, 222, 128, ${alpha2})`
            : `rgba(251, 113, 133, ${alpha2})`;
        if (beginCircle(ctx, cx, cy, r2)) {
          ctx.strokeStyle = color2;
          ctx.lineWidth = 3;
          ctx.stroke();
        }

        return true;
      });

      // --- Query ghosts: floating query terms that drift away from core after landing ---
      if (!reducedMotion) {
        ctx.save();
        ctx.font = '8px JetBrains Mono, monospace';
        ctx.textAlign = 'center';
        queryGhostsRef.current.forEach(g => {
          const elapsed = t - g.startTime;
          const progress = elapsed / g.duration;
          const fadeAlpha = progress < 0.2
            ? progress / 0.2
            : progress > 0.6
            ? (1 - progress) / 0.4
            : 1;
          // Inline alpha replacement for the color string
          const baseColor = g.color.replace(/[\d.]+\)$/, `${(0.6 * fadeAlpha).toFixed(2)})`);
          ctx.fillStyle = baseColor;
          ctx.fillText(g.text.length > 20 ? g.text.substring(0, 20) + '…' : g.text, g.x, g.y);
        });
        ctx.restore();
      }

      // --- Center core orb (no gradients for perf) ---
      // Outer glow
      if (beginCircle(ctx, cx, cy, 45)) {
        ctx.fillStyle = 'rgba(77,163,255,0.06)';
        ctx.fill();
      }

      // Mid glow
      ctx.fillStyle = 'rgba(200,220,255,0.15)';
      if (beginCircle(ctx, cx, cy, 28)) {
        ctx.fill();
      }

      // Core dot
      if (beginCircle(ctx, cx, cy, 9)) {
        ctx.fillStyle = 'rgba(255,255,255,0.95)';
        ctx.fill();
      }

      // Inner highlight
      if (beginCircle(ctx, cx - 2.5, cy - 2.5, 3)) {
        ctx.fillStyle = 'rgba(255,255,255,1)';
        ctx.fill();
      }

      // "INDEX CORE" label
      ctx.font = `9px ${FONT_MONO}`;
      ctx.fillStyle = 'rgba(154,164,178,0.65)';
      ctx.textAlign = 'center';
      ctx.fillText('INDEX CORE', cx, cy + 26);

      // Stage line
      ctx.font = `9px ${FONT_MONO}`;
      if (currentStage === 'completed') {
        ctx.fillStyle = 'rgba(74,222,128,0.6)';
        ctx.fillText('OPTIMIZED', cx, cy + 38);
      } else if (currentStage === 'analyzing') {
        ctx.fillStyle = 'rgba(77,163,255,0.6)';
        ctx.fillText('ANALYZING', cx, cy + 38);
      } else if (currentStage === 'running') {
        ctx.fillStyle = 'rgba(107,116,128,0.55)';
        ctx.fillText(
          `Queries tested: ${formatQueriesTested(currentEvalCaseCount, currentExperimentsRun)}`,
          cx,
          cy + 38
        );
      } else {
        ctx.fillStyle = 'rgba(107,116,128,0.55)';
        ctx.fillText(`${currentEvalCaseCount} test queries`, cx, cy + 38);
      }

      // Current hypothesis display — appears above the core
      const latestExp = storeState.latestExperiment;
      if (latestExp && currentStage === 'running') {
        const maxHypLen = 42;
        const hyp = latestExp.hypothesis.length > maxHypLen
          ? latestExp.hypothesis.substring(0, maxHypLen) + '…'
          : latestExp.hypothesis;
        const isKept = latestExp.decision === 'kept';
        const labelColor = isKept ? 'rgba(74,222,128,0.7)' : 'rgba(251,113,133,0.6)';

        // Draw hypothesis text above core
        ctx.save();
        ctx.font = `9px ${FONT_UI}`;
        ctx.textAlign = 'center';
        const hypW = Math.min(ctx.measureText(hyp).width + 16, 200);
        const hypX = cx - hypW / 2;
        const hypY = cy - 44;

        // Background pill
        ctx.fillStyle = 'rgba(5,7,11,0.75)';
        roundRect(ctx, hypX, hypY, hypW, 16, 3);
        ctx.fill();
        ctx.strokeStyle = isKept ? 'rgba(74,222,128,0.2)' : 'rgba(251,113,133,0.15)';
        ctx.lineWidth = 0.7;
        roundRect(ctx, hypX, hypY, hypW, 16, 3);
        ctx.stroke();

        // Hypothesis text
        ctx.fillStyle = labelColor;
        ctx.fillText(hyp, cx, hypY + 11);
        ctx.restore();

        // Delta score badge
        const deltaStr = (latestExp.deltaAbsolute >= 0 ? '+' : '') +
          (latestExp.deltaAbsolute * 100).toFixed(1) + '%';
        ctx.save();
        ctx.font = '700 11px JetBrains Mono, monospace';
        ctx.fillStyle = labelColor;
        ctx.textAlign = 'center';
        ctx.fillText(deltaStr, cx, cy - 56);
        ctx.restore();
      }

      // --- Labels: selected, hovered, and up to 2 recently active personas ---
      // Collect label-eligible personas to avoid overlap
      const labelCandidates: Set<string> = new Set();
      if (currentSelectedId) labelCandidates.add(currentSelectedId);
      if (currentHoveredId) labelCandidates.add(currentHoveredId);
      // Add up to 2 personas with active animation events
      const activeAnimIds = new Set<string>();
      const activeBeamByPersonaId = new Map<string, AnimEvent>();
      const activeResultByPersonaId = new Map<string, AnimEvent>();
      for (const event of animEventsRef.current) {
        if (t < event.startTime || t >= event.startTime + event.duration) continue;
        activeAnimIds.add(event.personaId);
        if (event.type === 'beam') {
          activeBeamByPersonaId.set(event.personaId, event);
        } else if (!activeResultByPersonaId.has(event.personaId)) {
          activeResultByPersonaId.set(event.personaId, event);
        }
      }
      const animating = currentPersonas.filter(
        p => activeAnimIds.has(p.id) && !labelCandidates.has(p.id)
      );
      for (const p of animating.slice(0, 2)) labelCandidates.add(p.id);
      // If still fewer than 3, add top performers
      if (labelCandidates.size < 3) {
        const sorted = [...currentPersonas].sort((a, b) => b.successRate - a.successRate);
        for (const p of sorted) {
          if (labelCandidates.size >= 3) break;
          labelCandidates.add(p.id);
        }
      }

      // Simple collision avoidance: track placed label rects
      const placedLabels: Array<{ x: number; y: number; w: number; h: number }> = [];
      const labelsCollide = (lx: number, ly: number, lw: number, lh: number) =>
        placedLabels.some(
          prev =>
            lx < prev.x + prev.w &&
            lx + lw > prev.x &&
            ly < prev.y + prev.h &&
            ly + lh > prev.y
        );

      ctx.save();
      positions.forEach(({ x, y, persona }) => {
        if (!labelCandidates.has(persona.id)) return;
        const isSelected = persona.id === currentSelectedId;
        const isHovered = persona.id === currentHoveredId;
        const isAnimating = activeAnimIds.has(persona.id);
        // Find active beam event for this persona (for query display)
        const activeBeam = activeBeamByPersonaId.get(persona.id);
        const activeResult = activeResultByPersonaId.get(persona.id);

        const labelY = y - 18;
        const nameLine = persona.name;

        ctx.font = `${isSelected ? 'bold ' : ''}11px Inter, sans-serif`;
        const nameW = ctx.measureText(nameLine).width;
        const roleW = ctx.measureText(persona.role).width;
        const pillW = Math.max(nameW, roleW) + 20;
        const pillH = 30;
        const pillX = x - pillW / 2;
        const pillY = labelY - pillH - 2;

        // Skip if overlapping a previously placed label (unless selected/hovered)
        if (!isSelected && !isHovered && labelsCollide(pillX, pillY, pillW, pillH)) return;
        placedLabels.push({ x: pillX, y: pillY, w: pillW, h: pillH });

        // Pill background
        ctx.fillStyle = 'rgba(10,14,20,0.88)';
        roundRect(ctx, pillX, pillY, pillW, pillH, 5);
        ctx.fill();

        // Pill border
        ctx.strokeStyle = isSelected
          ? 'rgba(77,163,255,0.5)'
          : isAnimating
          ? 'rgba(77,163,255,0.3)'
          : 'rgba(255,255,255,0.1)';
        ctx.lineWidth = 0.8;
        roundRect(ctx, pillX, pillY, pillW, pillH, 5);
        ctx.stroke();

        // Name
        ctx.font = `${isSelected || isHovered ? '600 ' : ''}11px Inter, sans-serif`;
        ctx.fillStyle = isSelected ? '#EEF3FF' : isAnimating ? '#4DA3FF' : '#C5CDD8';
        ctx.textAlign = 'center';
        ctx.fillText(nameLine, x, pillY + 13);

        // Second line: show query when beam active, result when flash active, role otherwise
        ctx.font = '9px Inter, sans-serif';
        if (activeBeam?.query && !activeResult) {
          const maxQueryLen = 22;
          const queryText = activeBeam.query.length > maxQueryLen
            ? activeBeam.query.substring(0, maxQueryLen) + '…'
            : activeBeam.query;
          ctx.fillStyle = 'rgba(77,163,255,0.8)';
          ctx.fillText(`"${queryText}"`, x, pillY + 25);
        } else if (activeResult?.type === 'success') {
          ctx.fillStyle = 'rgba(74,222,128,0.75)';
          ctx.fillText('✓ found', x, pillY + 25);
        } else if (activeResult?.type === 'failure') {
          ctx.fillStyle = 'rgba(251,113,133,0.75)';
          ctx.fillText('✗ no result', x, pillY + 25);
        } else if (activeResult?.type === 'partial') {
          ctx.fillStyle = 'rgba(251,191,36,0.75)';
          ctx.fillText('◐ partial', x, pillY + 25);
        } else {
          ctx.fillStyle = 'rgba(154,164,178,0.65)';
          ctx.fillText(persona.role, x, pillY + 25);
        }
      });
      ctx.restore();

      // --- Active query floating text for animating personas not in label pills ---
      if (!reducedMotion) {
        positions.forEach(({ x, y, persona }) => {
          if (labelCandidates.has(persona.id)) return; // already shown in pill
          const beam = activeBeamByPersonaId.get(persona.id);
          if (!beam?.query) return;
          const maxLen = 20;
          const q = beam.query.length > maxLen
            ? beam.query.substring(0, maxLen) + '…'
            : beam.query;
          const queryText = `"${q}"`;
          ctx.font = '9px JetBrains Mono, monospace';
          const tw = ctx.measureText(queryText).width;
          const qx = x;
          const qy = y + 18;
          const fadeAlpha = Math.min(1, (t - beam.startTime) / 0.3) * Math.min(1, (beam.startTime + beam.duration - t) / 0.3);
          ctx.fillStyle = `rgba(5,7,11,${0.7 * fadeAlpha})`;
          roundRect(ctx, qx - tw / 2 - 5, qy - 9, tw + 10, 14, 3);
          ctx.fill();
          ctx.fillStyle = `rgba(77,163,255,${0.65 * fadeAlpha})`;
          ctx.textAlign = 'center';
          ctx.fillText(queryText, qx, qy);
        });
      }

        rafRef.current = requestAnimationFrame(animate);
      } catch (error) {
        console.error('FishTankCanvas frame error', error);
        rafRef.current = requestAnimationFrame(animate);
      }
    };

    rafRef.current = requestAnimationFrame(animate);
    return () => {
      cancelAnimationFrame(rafRef.current);
    };
  }, [size, reducedMotion]);

  return (
    <div
      ref={containerRef}
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        overflow: 'hidden',
        cursor: hoveredPersonaId ? 'pointer' : 'default',
      }}
    >
      <canvas
        ref={canvasRef}
        style={{ display: 'block', width: '100%', height: '100%' }}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        onClick={handleClick}
      />
      <TooltipPortal
        persona={tooltipState.persona}
        x={tooltipState.x}
        y={tooltipState.y}
        visible={tooltipState.visible}
      />
    </div>
  );
}
