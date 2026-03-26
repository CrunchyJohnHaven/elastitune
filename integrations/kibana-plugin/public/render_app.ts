const DEFAULT_BASE_URL = 'http://localhost:8000';

export async function renderApp(core: any, params: any) {
  const container = params.element as HTMLElement;
  container.innerHTML = `
    <div style="padding:24px;font-family:Inter,Arial,sans-serif;color:#dfe5ef;background:#0b1117;min-height:100%">
      <h2 style="margin:0 0 8px">ElastiTune Run History</h2>
      <p style="margin:0 0 18px;color:#9aa4b2">Recent search runs from the ElastiTune control plane.</p>
      <div id="elastitune-history">Loading…</div>
    </div>
  `;

  const target = container.querySelector('#elastitune-history');
  if (!target) {
    return () => {};
  }

  try {
    const response = await fetch(`${DEFAULT_BASE_URL}/api/runs?limit=10&completedOnly=true`);
    const payload = await response.json();
    const rows = Array.isArray(payload?.runs) ? payload.runs : [];
    target.innerHTML = rows.length
      ? `
        <table style="width:100%;border-collapse:collapse">
          <thead>
            <tr>
              <th style="text-align:left;padding:8px 0;color:#9aa4b2">Index</th>
              <th style="text-align:left;padding:8px 0;color:#9aa4b2">Improvement</th>
              <th style="text-align:left;padding:8px 0;color:#9aa4b2">Experiments</th>
            </tr>
          </thead>
          <tbody>
            ${rows.map((row: any) => `
              <tr>
                <td style="padding:8px 0;border-top:1px solid rgba(255,255,255,0.08)">${row.index_name ?? 'Saved run'}</td>
                <td style="padding:8px 0;border-top:1px solid rgba(255,255,255,0.08)">${Number(row.improvement_pct ?? 0).toFixed(1)}%</td>
                <td style="padding:8px 0;border-top:1px solid rgba(255,255,255,0.08)">${row.experiments_run ?? 0}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `
      : '<div style="color:#9aa4b2">No completed runs were returned from the ElastiTune backend.</div>';
  } catch (error) {
    target.innerHTML = `<div style="color:#fca5a5">Failed to load ElastiTune history. Configure the backend URL and authentication before using this plugin in production.</div>`;
    // eslint-disable-next-line no-console
    console.error('ElastiTune Kibana plugin fetch failed', error);
  }

  return () => {
    container.innerHTML = '';
  };
}
