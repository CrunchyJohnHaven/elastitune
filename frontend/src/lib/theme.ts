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

export const PANEL_BG = 'rgba(10, 14, 20, 0.78)';
export const PANEL_BORDER = 'rgba(255,255,255,0.08)';
export const TEXT_PRIMARY = '#EEF3FF';
export const TEXT_SECONDARY = '#9AA4B2';
export const TEXT_DIM = '#6B7480';
export const ACCENT_BLUE = '#4DA3FF';
export const ACCENT_CYAN = '#7CE7FF';
export const SUCCESS = '#4ADE80';
export const WARNING = '#FBBF24';
export const DANGER = '#FB7185';

export const SURFACE_ELEVATED = 'rgba(10,14,20,0.72)';
