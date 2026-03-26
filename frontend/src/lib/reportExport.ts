import type { ReportCodeSnippet, ReportPayload } from '@/types/contracts';

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function confidenceLabel(value?: number | null): string | null {
  if (value == null || Number.isNaN(value)) return null;
  const normalized = value <= 1 ? value * 100 : value;
  return `${Math.max(0, Math.min(100, Math.round(normalized)))}% confidence`;
}

function renderParagraph(value?: string | null): string {
  if (!value) return '';
  return `<div style="line-height:1.65">${escapeHtml(value)}</div>`;
}

function renderList(items?: string[] | null): string {
  if (!items || items.length === 0) return '';
  return `<ul>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`;
}

function renderSnippetLines(lines: ReportCodeSnippet['beforeLines']): string {
  if (!lines.length) {
    return `<div style="color:#6B7480;font-family:Inter,Arial,sans-serif;font-size:11px;">No snippet lines were supplied.</div>`;
  }

  return lines
    .map(
      (line) => `
        <div style="display:grid;grid-template-columns:52px 1fr;gap:10px;align-items:start;">
          <div style="color:#6B7480;text-align:right;padding-right:4px;user-select:none;">${line.lineNumber}</div>
          <div style="color:${line.changed ? '#EEF3FF' : '#D7DEE8'};white-space:pre-wrap;word-break:break-word;">
            ${escapeHtml(line.content || ' ')}
            ${line.explanation ? `<div style="margin-top:4px;font-family:Inter,Arial,sans-serif;font-size:10px;line-height:1.45;color:#9AA4B2;">${escapeHtml(line.explanation)}</div>` : ''}
          </div>
        </div>
      `,
    )
    .join('');
}

function renderSnippetBlock(snippet: ReportCodeSnippet, tone: 'before' | 'after'): string {
  const color = tone === 'before' ? '#FB7185' : '#4ADE80';
  const bg = tone === 'before' ? 'rgba(251,113,133,0.04)' : 'rgba(74,222,128,0.04)';
  const border = tone === 'before' ? 'rgba(251,113,133,0.18)' : 'rgba(74,222,128,0.18)';
  const lines = tone === 'before' ? snippet.beforeLines : snippet.afterLines;

  return `
    <div style="border:1px solid ${border};background:${bg};border-radius:10px;padding:10px 12px;min-width:0;">
      <div style="display:flex;justify-content:space-between;gap:10px;align-items:baseline;flex-wrap:wrap;margin-bottom:8px;">
        <div style="font-family:'JetBrains Mono', monospace;font-size:10px;color:${color};letter-spacing:0.1em;text-transform:uppercase;">
          ${tone === 'before' ? 'Before' : 'After'}
        </div>
        <div style="font-family:Inter,Arial,sans-serif;font-size:11px;color:#9AA4B2;">${escapeHtml(snippet.summary)}</div>
      </div>
      <div style="font-family:'JetBrains Mono', monospace;font-size:11px;color:#EEF3FF;line-height:1.6;display:grid;gap:4px;">
        ${renderSnippetLines(lines)}
      </div>
    </div>
  `;
}

function renderNarrative(report: ReportPayload): string {
  const narrative = report.narrative ?? [];
  const lead = narrative[0];
  const sections = narrative.slice(1);
  const personaSummary = report.personaSummary;
  const validationNotes = report.validationNotes ?? [];
  const changeNarratives = report.changeNarratives ?? [];
  const confidence = confidenceLabel(lead?.confidence ?? report.summary.confidenceScore);

  if (
    !lead &&
    sections.length === 0 &&
    !personaSummary &&
    validationNotes.length === 0 &&
    changeNarratives.length === 0 &&
    report.summary.personaCount == null &&
    report.summary.confidenceScore == null
  ) {
    return '';
  }

  return `
    <h2>Plain-English Summary</h2>
    <div class="card" style="margin-bottom:14px;border:1px solid rgba(77,163,255,0.15);background:linear-gradient(180deg, rgba(77,163,255,0.07), rgba(255,255,255,0.02));">
      <div style="display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap;margin-bottom:10px;">
        <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.08em;color:#172033;">What this run means</div>
        <div style="font-family:'JetBrains Mono', monospace;font-size:11px;color:#4DA3FF;">
          ${escapeHtml(confidence ?? 'Confidence not provided')}
          ${report.summary.personaCount != null ? ` · ${escapeHtml(String(report.summary.personaCount))} personas` : ''}
        </div>
      </div>
      ${renderParagraph(lead?.body ?? 'This run included the technical report fields, but no additional narrative summary was available.')}
    </div>

    ${
      sections.length > 0
        ? `<div class="narrative-grid">
            ${sections
              .map(
                (section) => `
                  <div class="card" style="background:${
                    section.audience === 'technical'
                      ? 'rgba(77,163,255,0.04)'
                      : section.audience === 'operator'
                      ? 'rgba(74,222,128,0.03)'
                      : '#ffffff'
                  };">
                    <div style="font-size:12px;font-weight:700;color:#172033;margin-bottom:8px;">${escapeHtml(section.title)}</div>
                    <div style="line-height:1.6;color:#334155;white-space:pre-wrap;">${escapeHtml(section.body)}</div>
                  </div>
                `,
              )
              .join('')}
          </div>`
        : ''
    }

    ${
      personaSummary || validationNotes.length > 0 || changeNarratives.length > 0
        ? `<div class="narrative-grid narrative-grid-wide" style="margin-top:14px;">
            ${
              personaSummary
                ? `
                  <div class="card">
                    <h2 style="margin-top:0">Personas used</h2>
                    <div class="subtle" style="margin-bottom:10px;">${escapeHtml(personaSummary.explanation)}</div>
                    <div class="metric-label" style="margin-bottom:12px;">${escapeHtml(String(personaSummary.personaCount))} total personas</div>
                    ${
                      personaSummary.topRoles.length > 0
                        ? `<div style="padding:10px 12px;border-radius:8px;background:rgba(77,163,255,0.06);border:1px solid rgba(77,163,255,0.12);color:#1D4ED8;margin-bottom:12px;line-height:1.5;">Top roles represented: ${escapeHtml(personaSummary.topRoles.join(', '))}</div>`
                        : ''
                    }
                    ${
                      Object.entries(personaSummary.archetypeCounts)
                        .map(
                          ([archetype, count]) => `
                            <div style="padding:10px 12px;border-radius:8px;background:rgba(255,255,255,0.02);border:1px solid #d9e2f0;margin-bottom:10px;">
                              <div style="display:flex;justify-content:space-between;gap:10px;align-items:baseline;margin-bottom:4px;">
                                <div style="font-weight:600;color:#172033;">${escapeHtml(archetype)}</div>
                                <div class="subtle">${escapeHtml(String(count))}</div>
                              </div>
                              <div style="line-height:1.55;color:#334155;">Simulated personas in this archetype were used to test whether the tuned profile helps more than one style of search behavior.</div>
                            </div>
                          `,
                        )
                        .join('') || '<div class="subtle">Detailed persona category counts were not provided for this run.</div>'
                    }
                  </div>
                `
                : ''
            }
            ${
              changeNarratives.length > 0
                ? `
                  <div class="card">
                    <h2 style="margin-top:0">What changed and why</h2>
                    ${changeNarratives
                      .map(
                        (change) => `
                          <div style="padding:10px 12px;border-radius:8px;background:rgba(255,255,255,0.02);border:1px solid #d9e2f0;margin-bottom:10px;">
                            <div style="display:flex;justify-content:space-between;gap:10px;align-items:baseline;margin-bottom:6px;">
                              <div style="font-weight:600;color:#172033;">${escapeHtml(change.title)}</div>
                              ${change.confidence != null ? `<div style="font-family:'JetBrains Mono', monospace;font-size:10px;color:#16A34A;">${escapeHtml(confidenceLabel(change.confidence) ?? '')}</div>` : ''}
                            </div>
                            <div style="line-height:1.55;color:#334155;margin-bottom:6px;">${escapeHtml(change.plainEnglish)}</div>
                            <div style="line-height:1.55;color:#5f6b7a;margin-bottom:6px;">${escapeHtml(change.expectedEffect)}</div>
                            <div style="line-height:1.55;color:#0F766E;">${escapeHtml(change.whyItHelped)}</div>
                          </div>
                        `,
                      )
                      .join('')}
                  </div>
                `
                : ''
            }
            ${
              validationNotes.length > 0
                ? `
                  <div class="card">
                    <h2 style="margin-top:0">Validation notes</h2>
                    ${validationNotes
                      .map((note) => {
                        const color =
                          note.severity === 'success'
                            ? '#4ADE80'
                            : note.severity === 'warning'
                            ? '#FBBF24'
                            : '#4DA3FF';
                        const bg =
                          note.severity === 'success'
                            ? 'rgba(74,222,128,0.05)'
                            : note.severity === 'warning'
                            ? 'rgba(251,191,36,0.05)'
                            : 'rgba(77,163,255,0.05)';
                        return `
                          <div style="padding:10px 12px;border-radius:8px;border:1px solid ${color}40;background:${bg};margin-bottom:10px;">
                            <div style="display:flex;justify-content:space-between;gap:10px;align-items:baseline;margin-bottom:4px;">
                              <div style="font-weight:600;color:#172033;">${escapeHtml(note.title)}</div>
                              <div style="font-family:'JetBrains Mono', monospace;font-size:10px;text-transform:uppercase;letter-spacing:0.1em;color:${color};">${escapeHtml(note.severity)}</div>
                            </div>
                            <div style="line-height:1.55;color:#334155;">${escapeHtml(note.body)}</div>
                          </div>
                        `;
                      })
                      .join('')}
                  </div>
                `
                : ''
            }
          </div>`
        : ''
    }
  `;
}

function renderImplementationGuide(report: ReportPayload): string {
  const guide = report.implementationGuide;
  if (!guide || guide.snippets.length === 0) return '';

  return `
    <h2>Implementation Guide</h2>
    <div class="card" style="margin-bottom:14px;">
      ${renderParagraph(guide.summary)}
      ${
        guide.representativeQuery
          ? `<div class="subtle" style="margin-top:10px;">Representative query: ${escapeHtml(guide.representativeQuery)}</div>`
          : ''
      }
      ${renderList(guide.applyInstructions)}
    </div>
    <div style="display:grid;gap:14px;">
      ${guide.snippets
        .map(
          (snippet) => `
            <div class="card">
              <div style="display:flex;justify-content:space-between;gap:14px;align-items:flex-start;flex-wrap:wrap;margin-bottom:10px;">
                <div style="min-width:0;flex:1 1 360px;">
                  <div style="font-size:12px;font-weight:700;color:#172033;margin-bottom:4px;">${escapeHtml(snippet.title)}</div>
                  <div style="font-family:'JetBrains Mono', monospace;font-size:11px;color:#2563EB;word-break:break-word;">${escapeHtml(snippet.target)}</div>
                </div>
              </div>
              <div style="line-height:1.65;color:#334155;margin-bottom:12px;">${escapeHtml(snippet.summary)}</div>
              <div style="display:grid;grid-template-columns:repeat(auto-fit, minmax(280px, 1fr));gap:12px;">
                ${renderSnippetBlock(snippet, 'before')}
                ${renderSnippetBlock(snippet, 'after')}
              </div>
            </div>
          `,
        )
        .join('')}
    </div>
    ${guide.note ? `<div class="subtle" style="margin-top:14px;">${escapeHtml(guide.note)}</div>` : ''}
  `;
}

export function buildShareableReportHtml(report: ReportPayload): string {
  const metrics = [
    ['Baseline nDCG@10', report.summary.baselineScore.toFixed(3)],
    ['Best nDCG@10', report.summary.bestScore.toFixed(3)],
    [
      'Improvement',
      `${report.summary.improvementPct >= 0 ? '+' : ''}${report.summary.improvementPct.toFixed(1)}%`,
    ],
    ['Experiments', String(report.summary.experimentsRun)],
  ];

  const confidence = confidenceLabel(report.summary.confidenceScore);
  if (confidence) {
    metrics.push(['Confidence', confidence]);
  }
  if (report.summary.personaCount != null && report.summary.personaCount > 0) {
    metrics.push(['Personas', String(report.summary.personaCount)]);
  }

  const diffRows = report.diff.length
    ? report.diff
        .map(
          (change) => `
      <tr>
        <td>${escapeHtml(change.path)}</td>
        <td>${escapeHtml(String(change.before ?? '—'))}</td>
        <td>${escapeHtml(String(change.after ?? '—'))}</td>
      </tr>
    `,
        )
        .join('')
    : `<tr><td colspan="3">No profile changes were accepted in this run.</td></tr>`;

  const queryRows = report.queryBreakdown
    .map(
      (row) => `
    <tr>
      <td>${escapeHtml(row.query)}</td>
      <td>${row.baselineScore.toFixed(3)}</td>
      <td>${row.bestScore.toFixed(3)}</td>
      <td>${row.deltaPct >= 0 ? '+' : ''}${row.deltaPct.toFixed(1)}%</td>
    </tr>
  `,
    )
    .join('');

  const nextSteps = report.summary.nextSteps
    .map((step) => `<li>${escapeHtml(step)}</li>`)
    .join('');
  const narrativeHtml = renderNarrative(report);
  const implementationGuideHtml = renderImplementationGuide(report);

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
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: 24px; }
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
        .narrative-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 14px; }
        .narrative-grid-wide { grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }
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
          ${metrics
            .map(
              ([label, value]) => `
            <div class="card">
              <div class="metric-label">${escapeHtml(label)}</div>
              <div class="metric-value">${escapeHtml(value)}</div>
            </div>
          `,
            )
            .join('')}
        </div>

        ${narrativeHtml}

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

        ${implementationGuideHtml}

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
