import React, { useMemo } from 'react';
import type { ReportPayload } from '@/types/contracts';
import { PANEL_BORDER } from '@/lib/theme';

interface MitreCoverageHeatmapProps {
  report: ReportPayload;
}

const TACTIC_RULES: Array<{ label: string; tokens: string[] }> = [
  { label: 'Initial Access', tokens: ['phishing', 'attachment', 'exploit'] },
  { label: 'Execution', tokens: ['powershell', 'macro', 'execution', 'command'] },
  { label: 'Persistence', tokens: ['persistence', 'scheduled', 'registry'] },
  { label: 'Privilege Escalation', tokens: ['privilege', 'token'] },
  { label: 'Defense Evasion', tokens: ['bypass', 'evasion', 'clear'] },
  { label: 'Credential Access', tokens: ['credential', 'lsass', 'password', 'kerberoast'] },
  { label: 'Lateral Movement', tokens: ['lateral', 'psexec', 'smb'] },
  { label: 'Command and Control', tokens: ['c2', 'beacon', 'dns'] },
  { label: 'Exfiltration', tokens: ['exfiltration', 'data theft', 'tunneling'] },
];

function bg(score: number): string {
  if (score >= 0.7) return 'rgba(74,222,128,0.22)';
  if (score >= 0.35) return 'rgba(251,191,36,0.18)';
  return 'rgba(251,113,133,0.18)';
}

function fg(score: number): string {
  if (score >= 0.7) return '#4ADE80';
  if (score >= 0.35) return '#FBBF24';
  return '#FB7185';
}

export default function MitreCoverageHeatmap({ report }: MitreCoverageHeatmapProps) {
  const tactics = useMemo(() => {
    return TACTIC_RULES.map((rule) => {
      const queries = report.queryBreakdown.filter((query) =>
        rule.tokens.some((token) => query.query.toLowerCase().includes(token))
      );
      const score = queries.length
        ? queries.reduce((sum, query) => sum + query.bestScore, 0) / queries.length
        : 0;
      return { ...rule, score, count: queries.length };
    }).filter((row) => row.count > 0);
  }, [report.queryBreakdown]);

  if (report.connection.indexName !== 'security-siem' || tactics.length === 0) {
    return null;
  }

  return (
    <div
      style={{
        marginBottom: 28,
        background: 'rgba(255,255,255,0.025)',
        border: `1px solid ${PANEL_BORDER}`,
        borderRadius: 10,
        padding: '16px 18px',
      }}
    >
      <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 16, fontWeight: 600, color: '#EEF3FF', marginBottom: 4 }}>
        MITRE ATT&CK coverage
      </div>
      <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 12, color: '#6B7480', lineHeight: 1.5, marginBottom: 14 }}>
        A quick tactic-level view of which security intents are now easy to find and which still need search work.
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 10 }}>
        {tactics.map((tactic) => (
          <div
            key={tactic.label}
            style={{
              padding: '12px',
              borderRadius: 8,
              border: `1px solid ${PANEL_BORDER}`,
              background: bg(tactic.score),
            }}
          >
            <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 12, fontWeight: 600, color: '#EEF3FF', marginBottom: 4 }}>
              {tactic.label}
            </div>
            <div style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 16, fontWeight: 700, color: fg(tactic.score), marginBottom: 4 }}>
              {(tactic.score * 100).toFixed(0)}%
            </div>
            <div style={{ fontFamily: 'Inter, sans-serif', fontSize: 10, color: '#9AA4B2' }}>
              {tactic.count} mapped queries
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
