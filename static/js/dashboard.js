/* ═══════════════════════════════════════
   CloudPrint — Dashboard JS
═══════════════════════════════════════ */

const socket = io();
let allJobs = {};
let activeFilter = 'all';

// ── Connection ─────────────────────────
socket.on('connect', () => {
  document.getElementById('connectionDot').className = 'status-dot online';
  document.getElementById('connectionText').textContent = 'Connected';
});

socket.on('disconnect', () => {
  document.getElementById('connectionDot').className = 'status-dot offline';
  document.getElementById('connectionText').textContent = 'Disconnected';
});

socket.on('new_job', (job) => {
  allJobs[job.id] = job;
  renderTable();
  loadStats();
});

socket.on('job_updated', (job) => {
  allJobs[job.id] = job;
  renderTable();
  loadStats();
});

socket.on('printer_updated', (printer) => {
  loadPrinters();
});

// ── Live Clock ─────────────────────────
function updateClock() {
  const now = new Date();
  document.getElementById('dashTime').textContent = now.toLocaleTimeString('en-US', {
    hour: '2-digit', minute: '2-digit', second: '2-digit'
  });
}
setInterval(updateClock, 1000);
updateClock();

// ── Stats ──────────────────────────────
async function loadStats() {
  try {
    const res = await fetch('/api/stats');
    const stats = await res.json();
    document.getElementById('statTotal').textContent = stats.total;
    document.getElementById('statWaiting').textContent = stats.waiting;
    document.getElementById('statPrinting').textContent = stats.printing;
    document.getElementById('statCompleted').textContent = stats.completed;
  } catch(e) {}
}

// ── Printers ───────────────────────────
async function loadPrinters() {
  try {
    const res = await fetch('/api/printers');
    const printers = await res.json();
    renderPrinters(printers);
  } catch(e) {}
}

function renderPrinters(printers) {
  const list = document.getElementById('printersList');
  list.innerHTML = printers.map(p => `
    <div class="printer-card ${p.status}">
      <div class="printer-name">${escHtml(p.name)}</div>
      <div class="printer-meta">
        <span class="printer-status ${p.status}">${p.status}</span>
        <span class="printer-queue">${p.jobs} job${p.jobs !== 1 ? 's' : ''}</span>
      </div>
      <div class="printer-type">${p.color ? '🎨 Color' : '⬛ B&W'}</div>
    </div>
  `).join('');
}

// ── Jobs Table ─────────────────────────
async function loadJobs() {
  try {
    const res = await fetch('/api/jobs');
    const jobs = await res.json();
    jobs.forEach(j => allJobs[j.id] = j);
    renderTable();
  } catch(e) {}
}

function renderTable() {
  const tbody = document.getElementById('jobsTableBody');
  let jobs = Object.values(allJobs).sort((a, b) =>
    new Date(b.created_at) - new Date(a.created_at)
  );

  if (activeFilter !== 'all') {
    jobs = jobs.filter(j => j.status === activeFilter);
  }

  if (jobs.length === 0) {
    tbody.innerHTML = `
      <tr class="empty-row">
        <td colspan="8">No ${activeFilter === 'all' ? '' : activeFilter + ' '}print jobs. <a href="/">Upload a file</a> to get started.</td>
      </tr>`;
    return;
  }

  tbody.innerHTML = jobs.map(j => `
    <tr>
      <td class="td-jobid">#${j.id}</td>
      <td class="td-filename">${escHtml(j.file)}</td>
      <td>${escHtml(j.printer_name)}</td>
      <td>${j.copies}×</td>
      <td>${j.color === 'color' ? '🎨' : '⬛'}</td>
      <td><span class="job-badge badge-${j.status}">${j.status}</span></td>
      <td class="td-time">${formatTime(j.created_at)}</td>
      <td>
        ${j.status === 'waiting' ? `
          <button class="cancel-btn" onclick="cancelJob('${j.id}')">Cancel</button>
        ` : '—'}
      </td>
    </tr>
  `).join('');
}

// ── Cancel Job ─────────────────────────
async function cancelJob(jobId) {
  try {
    const res = await fetch(`/api/jobs/${jobId}/cancel`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      allJobs[jobId] = data.job;
      renderTable();
      loadStats();
    }
  } catch(e) {}
}

// ── Filter Tabs ────────────────────────
document.querySelectorAll('.filter-tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-tab').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activeFilter = btn.dataset.filter;
    renderTable();
  });
});

// ── Helpers ────────────────────────────
function formatTime(iso) {
  const d = new Date(iso);
  return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

function escHtml(str = '') {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Init ───────────────────────────────
loadStats();
loadPrinters();
loadJobs();

// Auto-refresh every 10s
setInterval(() => {
  loadStats();
  loadPrinters();
}, 10000);