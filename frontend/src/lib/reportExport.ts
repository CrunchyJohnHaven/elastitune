import type { ReportPayload } from '@/types/contracts';

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function buildShareableReportHtml(report: ReportPayload): string {
  const metrics = [
    ['Baseline nDCG@10', report.summary.baselineScore.toFixed(3)],
    ['Best nDCG@10', report.summary.bestScore.toFixed(3)],
    ['Improvement', `${report.summary.improvementPct >= 0 ? '+' : ''}${report.summary.improvementPct.toFixed(1)}%`],
    ['Experiments', String(report.summary.experimentsRun)],
  ];

  const diffRows = report.diff.length
    ? report.diff.map((change) => `
      <tr>
        <td>${escapeHtml(change.path)}</td>
        <td>${escapeHtml(String(change.before ?? '—'))}</td>
        <td>${escapeHtml(String(change.after ?? '—'))}</td>
      </tr>
    `).join('')
    : `<tr><td colspan="3">No profile changes were accepted in this run.</td></tr>`;

  const queryRows = report.queryBreakdown.map((row) => `
    <tr>
      <td>${escapeHtml(row.query)}</td>
      <td>${row.baselineScore.toFixed(3)}</td>
      <td>${row.bestScore.toFixed(3)}</td>
      <td>${row.deltaPct >= 0 ? '+' : ''}${row.deltaPct.toFixed(1)}%</td>
    </tr>
  `).join('');

  const nextSteps = report.summary.nextSteps.map((step) => `<li>${escapeHtml(step)}</li>`).join('');

  return `<!doctype html>
  <html lang="en">
    <head>
      <meta charset="utf-8" />
      <title>ElastiTune Report ${escapeHtml(report.runId)}</title>
      <style>
        body { font-family: Inter, Arial, sans-serif; margin: 0; background: #f5f7fb; color: #172033; }
        .page { max-width: 980px; margin: 0 auto; padding: 40px 32px 72px; }
        .header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 28px; }
        .brand { font-size: 28px; font-weight: 700; margin: 0 0 6px; }
        .subtle { color: #5f6b7a; font-size: 13px; }
        .headline { background: #ffffff; border: 1px solid #d9e2f0; border-radius: 14px; padding: 18px 20px; margin-bottom: 24px; font-size: 16px; line-height: 1.6; }
        .grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-bottom: 24px; }
        .card { background: #ffffff; border: 1px solid #d9e2f0; border-radius: 14px; padding: 18px; }
        .metric-label { color: #5f6b7a; font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 8px; }
        .metric-value { font-family: 'JetBrains Mono', monospace; font-size: 28px; font-weight: 700; color: #172033; }
        h2 { font-size: 18px; margin: 28px 0 12px; }
        table { width: 100%; border-collapse: collapse; background: #ffffff; border: 1px solid #d9e2f0; border-radius: 14px; overflow: hidden; }
        th, td { padding: 11px 12px; border-bottom: 1px solid #e7edf5; text-align: left; font-size: 13px; vertical-align: top; }
        th { background: #f8fbff; color: #5f6b7a; text-transform: uppercase; letter-spacing: 0.08em; font-size: 11px; }
        ul { margin: 10px 0 0; padding-left: 20px; }
        li { margin: 0 0 8px; line-height: 1.5; }
        .two-up { display: grid; grid-template-columns: 1.3fr 0.9fr; gap: 14px; }
        @media print {
          body { background: #ffffff; }
          .page { padding: 24px; }
        }
      </style>
    </head>
    <body>
      <div class="page">
        <div class="header">
          <div>
            <div class="brand">ElastiTune Optimization Report</div>
            <div class="subtle">Run ${escapeHtml(report.runId)} · Generated ${escapeHtml(new Date(report.generatedAt).toLocaleString())}</div>
            <div class="subtle">Index ${escapeHtml(report.connection.indexName)} · Cluster ${escapeHtml(report.connection.clusterName)}</div>
          </div>
          <div class="subtle">${escapeHtml(report.mode.toUpperCase())}</div>
        </div>

        <div class="headline">${escapeHtml(report.summary.headline)}</div>

        <div class="grid">
          ${metrics.map(([label, value]) => `
            <div class="card">
              <div class="metric-label">${escapeHtml(label)}</div>
              <div class="metric-value">${escapeHtml(value)}</div>
            </div>
          `).join('')}
        </div>

        <div class="two-up">
          <div class="card">
            <h2 style="margin-top:0">What happened</h2>
            <div style="line-height:1.6">${escapeHtml(report.summary.overview)}</div>
          </div>
          <div class="card">
            <h2 style="margin-top:0">Recommended next steps</h2>
            <ul>${nextSteps}</ul>
          </div>
        </div>

        <h2>Profile changes</h2>
        <table>
          <thead><tr><th>Parameter</th><th>Before</th><th>After</th></tr></thead>
          <tbody>${diffRows}</tbody>
        </table>

        <h2>Per-query results</h2>
        <table>
          <thead><tr><th>Query</th><th>Before</th><th>After</th><th>Delta</th></tr></thead>
          <tbody>${queryRows}</tbody>
        </table>
      </div>
    </body>
  </html>`;
}
