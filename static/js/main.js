/* ═══════════════════════════════════════
   CloudPrint — Main Page JS
═══════════════════════════════════════ */

const socket = io();
let selectedFile = null;
let copies = 1;
let colorMode = 'bw';
let currentJobs = {};

// ── Connection Status ──────────────────
socket.on('connect', () => {
  document.getElementById('connectionDot').className = 'status-dot online';
  document.getElementById('connectionText').textContent = 'Connected';
});

socket.on('disconnect', () => {
  document.getElementById('connectionDot').className = 'status-dot offline';
  document.getElementById('connectionText').textContent = 'Disconnected';
});

// ── Real-time Job Updates ──────────────
socket.on('new_job', (job) => {
  currentJobs[job.id] = job;
  renderJobsList();
  updateQueueCount();
  showToast(`✓ Job #${job.id} sent to ${job.printer_name}`, 'success');
});

socket.on('job_updated', (job) => {
  currentJobs[job.id] = job;
  renderJobsList();
  if (job.status === 'completed') {
    showToast(`🖨 Job #${job.id} printed successfully!`, 'success');
  }
});

// ── File Drop Zone ──────────────────────
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');

dropZone.addEventListener('click', (e) => {
  if (!e.target.closest('.file-remove')) fileInput.click();
});

dropZone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropZone.classList.add('drag-over');
});

dropZone.addEventListener('dragleave', () => {
  dropZone.classList.remove('drag-over');
});

dropZone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) handleFile(file);
});

fileInput.addEventListener('change', () => {
  if (fileInput.files[0]) handleFile(fileInput.files[0]);
});

document.getElementById('fileRemove').addEventListener('click', (e) => {
  e.stopPropagation();
  clearFile();
});

function handleFile(file) {
  const allowed = ['application/pdf', 'image/jpeg', 'image/png'];
  const ext = file.name.split('.').pop().toLowerCase();
  const allowedExts = ['pdf', 'jpg', 'jpeg', 'png'];

  if (!allowedExts.includes(ext)) {
    showToast('✕ File type not supported. Use PDF, JPG, or PNG.', 'error');
    return;
  }

  if (file.size > 50 * 1024 * 1024) {
    showToast('✕ File too large. Maximum 50MB.', 'error');
    return;
  }

  selectedFile = file;

  const icons = { pdf: '📄', jpg: '🖼', jpeg: '🖼', png: '🖼' };
  document.getElementById('fileIcon').textContent = icons[ext] || '📄';
  document.getElementById('fileName').textContent = file.name;
  document.getElementById('fileSize').textContent = formatFileSize(file.size);
  document.getElementById('filePreview').style.display = 'flex';

  // Hide drop text
  dropZone.querySelectorAll('.drop-icon, .drop-text, .drop-formats').forEach(el => {
    el.style.display = 'none';
  });

  document.getElementById('printBtn').disabled = false;
}

function clearFile() {
  selectedFile = null;
  fileInput.value = '';
  document.getElementById('filePreview').style.display = 'none';

  dropZone.querySelectorAll('.drop-icon, .drop-text, .drop-formats').forEach(el => {
    el.style.display = '';
  });

  document.getElementById('printBtn').disabled = true;
}

// ── Copies Counter ─────────────────────
document.getElementById('decreaseCopies').addEventListener('click', () => {
  if (copies > 1) {
    copies--;
    document.getElementById('copiesVal').textContent = copies;
  }
});

document.getElementById('increaseCopies').addEventListener('click', () => {
  if (copies < 99) {
    copies++;
    document.getElementById('copiesVal').textContent = copies;
  }
});

// ── Color Toggle ───────────────────────
document.getElementById('bwBtn').addEventListener('click', () => {
  colorMode = 'bw';
  document.getElementById('bwBtn').classList.add('active');
  document.getElementById('colorBtn').classList.remove('active');
});

document.getElementById('colorBtn').addEventListener('click', () => {
  colorMode = 'color';
  document.getElementById('colorBtn').classList.add('active');
  document.getElementById('bwBtn').classList.remove('active');
});

// ── Custom Page Range ─────────────────
document.getElementById('pageRange').addEventListener('change', function () {
  const wrap = document.getElementById('customRangeWrap');
  const input = document.getElementById('customRangeInput');
  if (this.value === 'custom') {
    wrap.classList.add('visible');
    input.focus();
  } else {
    wrap.classList.remove('visible');
    input.value = '';
  }
});

// ── Upload & Print ─────────────────────
document.getElementById('printBtn').addEventListener('click', async () => {
  if (!selectedFile) return;

  const overlay = document.getElementById('uploadOverlay');
  const fill = document.getElementById('progressFill');
  overlay.style.display = 'flex';

  // Simulate progress
  let progress = 0;
  const progressInterval = setInterval(() => {
    progress = Math.min(progress + Math.random() * 15, 90);
    fill.style.width = progress + '%';
  }, 200);

  const formData = new FormData();
  formData.append('file', selectedFile);
  formData.append('copies', copies);
  formData.append('printer_id', document.getElementById('printerSelect').value);
  formData.append('color', colorMode);
  const pageRangeSelect = document.getElementById('pageRange');
  const customRangeInput = document.getElementById('customRangeInput');
  const pageRangeValue = pageRangeSelect.value === 'custom'
    ? (customRangeInput.value.trim() || 'all')
    : pageRangeSelect.value;
  formData.append('page_range', pageRangeValue);

  try {
    const res = await fetch('/api/upload', { method: 'POST', body: formData });
    const data = await res.json();

    clearInterval(progressInterval);
    fill.style.width = '100%';

    setTimeout(() => {
      overlay.style.display = 'none';
      fill.style.width = '0%';
    }, 600);

    if (data.success) {
      clearFile();
    } else {
      showToast('✕ ' + (data.error || 'Upload failed'), 'error');
    }
  } catch (err) {
    clearInterval(progressInterval);
    overlay.style.display = 'none';
    fill.style.width = '0%';
    showToast('✕ Network error. Please try again.', 'error');
  }
});

// ── Load Initial Jobs ──────────────────
async function loadJobs() {
  try {
    const res = await fetch('/api/jobs');
    const jobs = await res.json();
    jobs.forEach(j => currentJobs[j.id] = j);
    renderJobsList();
    updateQueueCount();
  } catch(e) {}
}

// ── Render Jobs ────────────────────────
function renderJobsList() {
  const list = document.getElementById('jobsList');
  const jobs = Object.values(currentJobs).sort((a, b) =>
    new Date(b.created_at) - new Date(a.created_at)
  ).slice(0, 20);

  if (jobs.length === 0) {
    list.innerHTML = '<div class="jobs-empty"><span>No print jobs yet</span></div>';
    return;
  }

  list.innerHTML = jobs.map(j => `
    <div class="job-item status-${j.status}" id="job-${j.id}">
      <div class="job-top">
        <span class="job-file-name">${escHtml(j.file)}</span>
        <span class="job-id">#${j.id}</span>
      </div>
      <div class="job-meta">
        <span class="job-badge badge-${j.status}">${j.status}</span>
        <span class="job-printer">${escHtml(j.printer_name)}</span>
      </div>
      ${j.status === 'printing' ? `
        <div class="job-progress">
          <div class="job-progress-fill" style="width: 60%; animation: progressAnim 2s infinite;"></div>
        </div>` : ''}
      ${j.status === 'completed' ? `
        <div class="job-progress">
          <div class="job-progress-fill" style="width: 100%;"></div>
        </div>` : ''}
    </div>
  `).join('');
}

function updateQueueCount() {
  const active = Object.values(currentJobs).filter(
    j => j.status === 'waiting' || j.status === 'printing'
  ).length;
  document.getElementById('queueCount').textContent = active;
}

// ── Toast Notification ─────────────────
function showToast(msg, type = 'success') {
  const toast = document.getElementById('toast');
  const icon = document.getElementById('toastIcon');
  const msgEl = document.getElementById('toastMsg');

  icon.textContent = type === 'error' ? '✕' : '✓';
  msgEl.textContent = msg;
  toast.style.borderColor = type === 'error' ? 'rgba(255,77,107,0.4)' : 'rgba(77,255,145,0.2)';
  toast.classList.add('show');

  setTimeout(() => toast.classList.remove('show'), 3500);
}

// ── Helpers ────────────────────────────
function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function escHtml(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ── Init ───────────────────────────────
loadJobs();