// Persona color generation from colorSeed
export function personaColor(colorSeed: number, alpha = 1): string {
  // Generate a hue from the seed
  const hue = (colorSeed * 137.508) % 360; // golden angle
  const saturation = 65 + (colorSeed % 20);
  const lightness = 55 + (colorSeed % 15);
  return `hsla(${hue.toFixed(0)}, ${saturation}%, ${lightness}%, ${alpha})`;
}

export function personaGlowColor(colorSeed: number): string {
  const hue = (colorSeed * 137.508) % 360;
  return `hsla(${hue.toFixed(0)}, 70%, 60%, 0.4)`;
}

export const FONT_UI =
  '"Inter", "Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif';

export const SURFACE_BG = 'rgba(10, 14, 20, 0.78)';
export const SURFACE_BG_STRONG = 'rgba(5, 7, 11, 0.92)';
export const SURFACE_BORDER = 'rgba(255,255,255,0.08)';
export const FOCUS_RING = '0 0 0 2px rgba(77, 163, 255, 0.35)';

export const SPACE = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
} as const;

// State colors
export const STATE_COLORS = {
  idle: 'rgba(154, 164, 178, 0.7)',
  searching: 'rgba(77, 163, 255, 0.9)',
  success: 'rgba(74, 222, 128, 0.9)',
  partial: 'rgba(251, 191, 36, 0.9)',
  failure: 'rgba(251, 113, 133, 0.9)',
  reacting: 'rgba(255, 255, 255, 0.95)',
} as const;

export const STATE_GLOW_COLORS = {
  idle: 'rgba(154, 164, 178, 0.15)',
  searching: 'rgba(77, 163, 255, 0.25)',
  success: 'rgba(74, 222, 128, 0.3)',
  partial: 'rgba(251, 191, 36, 0.25)',
  failure: 'rgba(251, 113, 133, 0.2)',
  reacting: 'rgba(255, 255, 255, 0.4)',
} as const;

export const PANEL_BG = SURFACE_BG;
export const PANEL_BORDER = SURFACE_BORDER;
export const TEXT_PRIMARY = '#EEF3FF';
export const TEXT_SECONDARY = '#9AA4B2';
export const TEXT_DIM = '#6B7480';
export const ACCENT_BLUE = '#4DA3FF';
export const ACCENT_CYAN = '#7CE7FF';
export const SUCCESS = '#4ADE80';
export const WARNING = '#FBBF24';
export const DANGER = '#FB7185';

export const FONT_SANS = 'Inter, system-ui, sans-serif';
export const FONT_MONO = '"JetBrains Mono", ui-monospace, SFMono-Regular, monospace';

export const SURFACE_BASE = '#05070B';
export const SURFACE_ELEVATED = 'rgba(10,14,20,0.72)';
export const SURFACE_STRONG = 'rgba(11,15,21,0.96)';
export const SURFACE_SUBTLE = 'rgba(255,255,255,0.03)';

export const RADIUS_MD = 8;
export const RADIUS_LG = 12;

export const TRANSITION_FAST = '0.15s ease';
export const TRANSITION_MEDIUM = '0.22s ease';
