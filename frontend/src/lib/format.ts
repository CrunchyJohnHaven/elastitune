export function formatScore(score: number): string {
  return score.toFixed(4);
}

export function formatPercent(pct: number, sign = true): string {
  const str = Math.abs(pct).toFixed(1) + '%';
  if (!sign) return str;
  return pct >= 0 ? `+${str}` : `-${str}`;
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.floor(seconds)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}m ${s.toString().padStart(2, '0')}s`;
}

export function getDisplayElapsedSeconds({
  metricsElapsedSeconds,
  startedAt,
  completedAt,
  stage,
  nowMs = Date.now(),
}: {
  metricsElapsedSeconds: number;
  startedAt?: string | null;
  completedAt?: string | null;
  stage?: string | null;
  nowMs?: number;
}): number {
  const fallback = Math.max(0, metricsElapsedSeconds || 0);

  const parse = (value?: string | null) => {
    if (!value) return null;
    const parsed = Date.parse(value);
    return Number.isFinite(parsed) ? parsed : null;
  };

  const startedMs = parse(startedAt);
  const completedMs = parse(completedAt);

  if (startedMs != null && completedMs != null && (stage === 'completed' || stage === 'error')) {
    return Math.max(fallback, (completedMs - startedMs) / 1000);
  }

  if (startedMs != null && stage && ['starting', 'running', 'stopping'].includes(stage)) {
    return Math.max(fallback, (nowMs - startedMs) / 1000);
  }

  return fallback;
}

export function formatBytes(bytes: number): string {
  if (bytes >= 1e9) return `${(bytes / 1e9).toFixed(2)} GB`;
  if (bytes >= 1e6) return `${(bytes / 1e6).toFixed(1)} MB`;
  if (bytes >= 1e3) return `${(bytes / 1e3).toFixed(0)} KB`;
  return `${bytes} B`;
}

export function formatDollars(usd: number): string {
  return `$${usd.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function formatDocCount(n: number): string {
  if (n >= 1e6) return `${(n / 1e6).toFixed(n % 1e6 === 0 ? 0 : 1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(n % 1e3 === 0 ? 0 : 1)}K`;
  return n.toLocaleString('en-US');
}

export function formatTimestamp(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export function truncate(s: string, max = 40): string {
  if (s.length <= max) return s;
  return s.slice(0, max - 1) + '\u2026';
}

export function initials(name: string): string {
  return name.split(' ').slice(0, 2).map(n => n[0]).join('').toUpperCase();
}
