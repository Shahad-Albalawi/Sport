const API_BASE = window.location.origin;

let currentJobId = null;
let lastReport = null;
let eventSource = null;
let analysisComplete = false;
let cameraStream = null;

const sportSelect = document.getElementById('sportSelect');
const uploadZone = document.getElementById('uploadZone');
const uploadText = document.getElementById('uploadText');
const videoFile = document.getElementById('videoFile');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const videoArea = document.getElementById('videoArea');
const overlayCanvas = document.getElementById('overlayCanvas');
const videoPlaceholder = document.getElementById('videoPlaceholder');
const progressSection = document.getElementById('progressSection');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const liveFeedbackPanel = document.getElementById('liveFeedbackPanel');
const liveMovement = document.getElementById('liveMovement');
const liveScore = document.getElementById('liveScore');
const liveErrors = document.getElementById('liveErrors');
const liveStrengths = document.getElementById('liveStrengths');
const liveImprovement = document.getElementById('liveImprovement');
const liveObjects = document.getElementById('liveObjects');
const resultSection = document.getElementById('resultSection');
const sportResult = document.getElementById('sportResult');
const scoreResult = document.getElementById('scoreResult');
const movementsResult = document.getElementById('movementsResult');
const errorsList = document.getElementById('errorsList');
const strengthsList = document.getElementById('strengthsList');
const improvementsList = document.getElementById('improvementsList');
const injuryRiskScore = document.getElementById('injuryRiskScore');
const injuryRiskDetails = document.getElementById('injuryRiskDetails');
const possibleInjuriesList = document.getElementById('possibleInjuriesList');

// Load sports with loading state
async function loadSports() {
  const sportLoading = document.getElementById('sportLoading');
  sportSelect.setAttribute('aria-busy', 'true');
  if (sportLoading) sportLoading.textContent = 'Loading...';
  try {
    const res = await fetch(`${API_BASE}/api/sports`);
    const data = await res.json();
    sportSelect.innerHTML = '<option value="">-- Choose sport --</option>';
    data.sports.forEach(s => {
      const opt = document.createElement('option');
      opt.value = s.id;
      opt.textContent = s.name;
      sportSelect.appendChild(opt);
    });
  } catch (e) {
    console.error('Failed to load sports:', e);
    if (sportLoading) sportLoading.textContent = 'Failed to load. Refresh to retry.';
  } finally {
    sportSelect.setAttribute('aria-busy', 'false');
    if (sportLoading) sportLoading.textContent = '';
  }
}
loadSports();

document.querySelectorAll('input[name="source"]').forEach(r => {
  r.addEventListener('change', e => {
    uploadZone.style.display = e.target.value === 'upload' ? 'block' : 'none';
    updateStartDisabled();
  });
});

uploadZone.addEventListener('click', () => videoFile.click());
uploadZone.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' || e.key === ' ') {
    e.preventDefault();
    videoFile.click();
  }
});
uploadZone.addEventListener('dragover', e => { e.preventDefault(); uploadZone.classList.add('has-file'); });
uploadZone.addEventListener('dragleave', () => { if (!videoFile.files.length) uploadZone.classList.remove('has-file'); });
uploadZone.addEventListener('drop', e => {
  e.preventDefault();
  const f = e.dataTransfer.files[0];
  if (f && f.type.startsWith('video/')) {
    const dt = new DataTransfer();
    dt.items.add(f);
    videoFile.files = dt.files;
    updateUploadUI(f);
  }
});

videoFile.addEventListener('change', e => {
  const f = e.target.files[0];
  if (f) updateUploadUI(f);
});

function updateUploadUI(file) {
  if (file) {
    uploadText.textContent = file.name;
    uploadZone.classList.add('has-file');
  }
  updateStartDisabled();
}

function updateStartDisabled() {
  const source = document.querySelector('input[name="source"]:checked')?.value;
  const hasSport = sportSelect.value;
  const hasFile = source === 'camera' || videoFile.files.length > 0;
  startBtn.disabled = !(hasSport && hasFile);
}

sportSelect.addEventListener('change', updateStartDisabled);

function parseError(err) {
  if (typeof err === 'string') return err;
  if (Array.isArray(err)) return err.map(e => e.msg || e.message || JSON.stringify(e)).join('; ');
  return err?.detail ? parseError(err.detail) : JSON.stringify(err);
}

function setProgress(pct) {
  progressFill.style.width = Math.min(100, pct || 0) + '%';
}

function renderResultSummary(r, isError = false) {
  sportResult.textContent = isError ? 'Error' : (r.sport_name_en || r.sport_name || r.sport || '-') + (r.sport_was_auto ? ' (auto)' : '');
  scoreResult.textContent = isError ? '-' : (r.overall_score != null ? r.overall_score : '-');
  movementsResult.textContent = isError ? '-' : ((r.movements_analyzed || []).map(m => `${m.name_en || m.id}: ${m.score}/10`).join('; ') || '-');
  if (isError) {
    errorsList.innerHTML = '<li class="error-msg">' + (r.error || 'Analysis failed') + '</li>';
    strengthsList.innerHTML = '';
    improvementsList.innerHTML = '';
    injuryRiskScore.textContent = '-';
    if (injuryRiskDetails) injuryRiskDetails.innerHTML = '';
    if (possibleInjuriesList) possibleInjuriesList.innerHTML = '';
  } else {
    const errs = r.errors || [];
    errorsList.innerHTML = errs.length ? errs.map(e => '<li>' + e + '</li>').join('') : '<li class="none">None</li>';
    const str = r.strengths || [];
    strengthsList.innerHTML = str.length ? str.map(s => '<li>' + s + '</li>').join('') : '<li class="none">-</li>';
    const imps = (r.coaching_feedback || []).map(c => c.feedback).filter(Boolean);
    improvementsList.innerHTML = imps.length ? imps.map(i => '<li>' + i + '</li>').join('') : '<li class="none">See PDF report</li>';
    // Injury Risk / مخاطر الإصابات
    const score = r.injury_risk_score;
    injuryRiskScore.className = 'injury-risk-score';
    if (score != null && score >= 0) {
      const label = score >= 50 ? 'High / عالي' : score >= 25 ? 'Moderate / متوسط' : 'Low / منخفض';
      injuryRiskScore.textContent = `${score}/100 (${label})`;
      if (score >= 50) injuryRiskScore.classList.add('risk-high');
      else if (score >= 25) injuryRiskScore.classList.add('risk-moderate');
      else injuryRiskScore.classList.add('risk-low');
    } else {
      injuryRiskScore.textContent = '-';
    }
    const details = r.injury_risk_with_corrections || [];
    const warnings = r.injury_risk_warnings || [];
    if (injuryRiskDetails) {
      if (details.length) {
        injuryRiskDetails.innerHTML = details.map(d => {
          const inj = (d.possible_injuries || []).length ? '<br><small>إصابات محتملة: ' + d.possible_injuries.join(', ') + '</small>' : '';
          return `<div class="injury-detail-card"><strong>⚠ ${d.warning}</strong><p class="correction">→ ${d.correction}</p>${inj}</div>`;
        }).join('');
      } else if (warnings.length) {
        injuryRiskDetails.innerHTML = '<ul class="result-list">' + warnings.map(w => '<li class="warning">⚠ ' + w + '</li>').join('') + '</ul>';
      } else {
        injuryRiskDetails.innerHTML = '<p class="none">None</p>';
      }
    }
    const possible = r.possible_injuries || [];
    if (possibleInjuriesList) possibleInjuriesList.innerHTML = possible.length ? possible.map(i => '<li>• ' + i + '</li>').join('') : '<li class="none">None</li>';
  }
}

function connectStream(jobId) {
  if (eventSource) eventSource.close();
  eventSource = new EventSource(`${API_BASE}/api/stream/${jobId}`);
  videoArea.classList.add('live');
  videoPlaceholder.classList.add('hidden');
  liveFeedbackPanel.classList.remove('hidden');
  progressSection.classList.remove('hidden');

  eventSource.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      if (data.event === 'done') {
        analysisComplete = true;
        eventSource.close();
        eventSource = null;
        videoArea.classList.remove('live');
        setProgress(100);
        const res = data.result;
        if (res) {
          if (res.status === 'error') {
            renderResultSummary({ error: res.error || 'Analysis failed' }, true);
            resultSection.classList.remove('hidden');
          } else {
            const r = res.result || res;
            lastReport = r;
            renderResultSummary(r);
            resultSection.classList.remove('hidden');
          }
        }
        progressSection.classList.add('hidden');
        startBtn.disabled = false;
        startBtn.setAttribute('aria-busy', 'false');
        stopBtn.disabled = true;
        if (cameraStream) {
          cameraStream.getTracks().forEach(t => t.stop());
          cameraStream = null;
        }
        return;
      }
      // Live frame
      if (data.img) {
        const img = new Image();
        img.onload = () => {
          const ctx = overlayCanvas.getContext('2d');
          overlayCanvas.width = img.width;
          overlayCanvas.height = img.height;
          ctx.drawImage(img, 0, 0);
        };
        img.src = 'data:image/jpeg;base64,' + data.img;
      }
      setProgress(data.pct);
      progressText.textContent = `Analyzing... ${data.pct || 0}%`;
      liveMovement.textContent = (data.movement || '-').replace(/_/g, ' ');
      liveScore.textContent = data.score != null ? (data.score / 10).toFixed(1) + '/10' : '-/10';
      liveErrors.textContent = (data.errors || []).length ? data.errors.slice(0, 2).join('; ') : 'None';
      liveStrengths.textContent = (data.strengths || []).length ? data.strengths.slice(0, 3).join(', ') : '-';
      liveImprovement.textContent = data.feedback || '-';
      liveObjects.textContent = (data.objects || []).length ? data.objects.join(', ') : '-';
    } catch (err) {
      console.warn('Stream parse error:', err);
    }
  };

  eventSource.onerror = () => {
    if (eventSource) eventSource.close();
    eventSource = null;
  };
}

startBtn.addEventListener('click', async () => {
  const sport = sportSelect.value;
  const source = document.querySelector('input[name="source"]:checked')?.value;
  if (!sport) {
    alert('Select sport or "Auto Detect" first.');
    return;
  }

  let body = { sport };
  if (source === 'camera') {
    body.use_camera = true;
  } else {
    const file = videoFile.files[0];
    if (!file) {
      alert('Select or upload a video first.');
      return;
    }
    const form = new FormData();
    form.append('file', file);
    const uploadLoading = document.getElementById('uploadLoading');
    if (uploadLoading) uploadLoading.textContent = 'Uploading...';
    try {
      const uploadRes = await fetch(`${API_BASE}/api/upload`, { method: 'POST', body: form });
      if (!uploadRes.ok) {
        const err = await uploadRes.json().catch(() => ({}));
        alert(parseError(err.detail || err) || 'Upload failed');
        return;
      }
      const uploadData = await uploadRes.json();
      body.source = uploadData.path;
    } catch (e) {
      alert('Upload failed: ' + e.message);
      return;
    } finally {
      if (uploadLoading) uploadLoading.textContent = '';
    }
  }

  startBtn.disabled = true;
  startBtn.setAttribute('aria-busy', 'true');
  stopBtn.disabled = false;
  analysisComplete = false;
  resultSection.classList.add('hidden');
  setProgress(0);

  if (source === 'camera') {
    try {
      cameraStream = await navigator.mediaDevices.getUserMedia({ video: true });
    } catch (e) {
      alert('Camera access denied. Use upload instead.');
      startBtn.disabled = false;
      startBtn.setAttribute('aria-busy', 'false');
      stopBtn.disabled = true;
      return;
    }
  }

  try {
    const res = await fetch(`${API_BASE}/api/analyze?export_pdf=true&export_csv=true&export_json=true&live_overlay=true`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(parseError(err.detail || err) || 'Failed to start');
      startBtn.disabled = false;
      startBtn.setAttribute('aria-busy', 'false');
      stopBtn.disabled = true;
      return;
    }
    const { job_id } = await res.json();
    currentJobId = job_id;
    connectStream(job_id);
    pollStatus(job_id);
  } catch (e) {
    alert('Error: ' + e.message);
    startBtn.disabled = false;
    startBtn.setAttribute('aria-busy', 'false');
    stopBtn.disabled = true;
  }
});

stopBtn.addEventListener('click', async () => {
  try {
    await fetch(`${API_BASE}/api/stop`, { method: 'POST' });
  } catch (_) {}
  stopBtn.disabled = true;
  progressText.textContent = 'Stopping...';
});

async function pollStatus(jobId) {
  let data;
  try {
    const res = await fetch(`${API_BASE}/api/status/${jobId}`);
    data = await res.json();
  } catch (e) {
    if (!analysisComplete) setTimeout(() => pollStatus(jobId), 1500);
    return;
  }

  if (data.progress && data.status === 'running') {
    const total = data.progress.total || 1;
    const frame = data.progress.frame || 0;
    const pct = Math.round(100 * frame / total);
    setProgress(pct);
    progressText.textContent = `Analyzing... ${pct}%`;
  }

  if (analysisComplete) return;

  if (data.status === 'completed' && data.result) {
    analysisComplete = true;
    progressSection.classList.add('hidden');
    resultSection.classList.remove('hidden');
    lastReport = data.result;
    renderResultSummary(data.result);
    startBtn.disabled = false;
    startBtn.setAttribute('aria-busy', 'false');
    stopBtn.disabled = true;
    if (cameraStream) {
      cameraStream.getTracks().forEach(t => t.stop());
      cameraStream = null;
    }
    return;
  }

  if (data.status === 'error') {
    analysisComplete = true;
    progressSection.classList.add('hidden');
    alert(data.error || 'Analysis failed');
    startBtn.disabled = false;
    startBtn.setAttribute('aria-busy', 'false');
    stopBtn.disabled = true;
    return;
  }

  setTimeout(() => pollStatus(jobId), 1000);
}

function downloadReport(type) {
  const files = lastReport?.report_files;
  const fn = files?.[type];
  if (fn) {
    window.open(`${API_BASE}/api/reports/${fn}`, '_blank');
  } else {
    alert(`No ${type.toUpperCase()} report available.`);
  }
}

document.getElementById('downloadPdf').addEventListener('click', () => downloadReport('pdf'));
document.getElementById('downloadCsv').addEventListener('click', () => downloadReport('csv'));
document.getElementById('downloadJson').addEventListener('click', () => downloadReport('json'));

document.getElementById('downloadVideo').addEventListener('click', () => {
  const fn = lastReport?.output_filename;
  if (fn) {
    window.open(`${API_BASE}/api/output/${fn}`, '_blank');
  } else {
    alert('No overlay video available.');
  }
});
