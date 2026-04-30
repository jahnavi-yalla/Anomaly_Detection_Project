/* ════════════════════════════════════════════════
   StreamSight — Main JavaScript
   ════════════════════════════════════════════════ */

/* ── Upload Dataset ── */
function uploadDataset(input) {
  if (!input.files[0]) return;
  const statusEl = document.getElementById('upload-status');
  statusEl.innerHTML = '<div class="badge-default">⏳ Uploading and analysing...</div>';
  const formData = new FormData();
  formData.append('file', input.files[0]);
  fetch('/upload', { method: 'POST', body: formData })
    .then(r => r.json())
    .then(d => {
      if (d.success) {
        statusEl.innerHTML = `
          <div class="badge-ok">${d.message} · ${d.anomalies} anomalies detected</div>
          <button onclick="location.reload()" style="margin-top:10px; padding:8px 16px; background:#4f46e5; color:white; border:none; border-radius:6px; cursor:pointer; font-weight:600; font-size:0.9rem;">
            🔄 Reload & View Anomalies
          </button>
        `;
      } else {
        statusEl.innerHTML = `<div class="alert alert-error" style="margin:0">❌ ${d.message}</div>`;
      }
    })
    .catch((e) => {
      console.error('Upload error:', e);
      statusEl.innerHTML = '<div class="alert alert-error" style="margin:0">❌ Upload failed. Please try again.</div>';
    });
}

/* ── Clear Upload ── */
function clearUpload() {
  fetch('/clear_upload', { method: 'POST' }).then(() => location.reload());
}

/* ── Set Business Type ── */
function setBiz(biz) {
  fetch('/set_biz', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ biz: biz })
  }).then(() => location.reload());
}

/* ── Range slider live update ── */
document.addEventListener('DOMContentLoaded', () => {
  const slider = document.getElementById('cont-slider');
  const valEl  = document.getElementById('cont-val');
  if (slider && valEl) {
    slider.addEventListener('input', () => {
      valEl.textContent = parseFloat(slider.value).toFixed(2);
    });
  }
});

/* ── Plotly default config ── */
const PLOTLY_CONFIG = { responsive: true, displayModeBar: false };
const PLOT_LAYOUT_BASE = {
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor:  'rgba(0,0,0,0)',
  font: { family: 'Inter', color: '#94a3b8', size: 11 },
  xaxis: { gridcolor: 'rgba(0,0,0,.05)', zeroline: false, showline: false },
  yaxis: { gridcolor: 'rgba(0,0,0,.05)', zeroline: false, showline: false },
  margin: { l: 4, r: 4, t: 36, b: 8 },
  hovermode: 'x unified',
  hoverlabel: { bgcolor: '#fff', bordercolor: '#e2e8f0', font: { family: 'Inter', size: 12, color: '#0f172a' } },
  legend: { bgcolor: 'rgba(0,0,0,0)', borderwidth: 0, orientation: 'h', yanchor: 'bottom', y: 1.02, xanchor: 'left', x: 0 }
};

function renderPlot(divId, jsonData) {
  if (!document.getElementById(divId)) return;
  const data = typeof jsonData === 'string' ? JSON.parse(jsonData) : jsonData;
  Plotly.newPlot(divId, data.data, data.layout, PLOTLY_CONFIG);
}
