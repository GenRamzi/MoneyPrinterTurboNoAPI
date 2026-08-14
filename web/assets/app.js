const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const TASK_STORAGE_KEY = 'mpt-active-task';
const state = { providers: [], materials: [], task: null, poll: null, voiceUrl: null, busy: false };

function toast(message, error = false) {
  const el = $('#toast');
  el.textContent = message;
  el.classList.toggle('error', error);
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 4200);
}

async function api(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let message = `HTTP ${response.status}`;
    try {
      const payload = await response.json();
      message = payload.detail || message;
    } catch {}
    throw new Error(message);
  }
  if (response.status === 204) return null;
  return response.json();
}

function escapeHtml(value = '') {
  return String(value).replace(/[&<>'"]/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  }[character]));
}

function providerStatus(provider) {
  if (!provider.installed) return ['غير مثبت', ''];
  if (provider.authenticated === true) return ['متصل', 'connected'];
  if (provider.authenticated === null) return ['جاهز للفحص', ''];
  return ['غير متصل', ''];
}

async function loadHealth() {
  try {
    const [health, gpu] = await Promise.all([api('/api/health'), api('/api/gpu')]);
    const ready = health.ok;
    $('#systemStatus .dot').classList.toggle('ok', ready);
    $('#systemStatus b').textContent = ready ? 'النظام جاهز' : 'FFmpeg مطلوب';
    $('#systemStatus small').textContent = ready ? `Renderer online · ${gpu.label}` : 'Install ffmpeg + ffprobe';
  } catch {
    $('#systemStatus b').textContent = 'غير متصل';
    $('#systemStatus small').textContent = 'تعذر الوصول إلى الخادم';
  }
}

async function loadProviders() {
  const grid = $('#providerGrid');
  try {
    state.providers = await api('/api/providers');
    grid.innerHTML = state.providers.map((provider) => {
      const [status, statusClass] = providerStatus(provider);
      const action = provider.kind === 'local' && provider.installed
        ? ''
        : `<button class="mini provider-login" data-id="${escapeHtml(provider.id)}">${provider.installed ? 'تسجيل الدخول' : 'طريقة التثبيت'}</button>`;
      return `<article class="provider-card"><div class="provider-top"><span class="provider-icon">${escapeHtml(provider.icon)}</span><span class="provider-state ${statusClass}">${status}</span></div><b>${escapeHtml(provider.name)}</b><p>${escapeHtml(provider.status)}</p>${action}</article>`;
    }).join('');
    $('#provider').innerHTML = state.providers.map((provider) => `<option value="${escapeHtml(provider.id)}" ${!provider.installed ? 'disabled' : ''}>${escapeHtml(provider.name)}${provider.installed ? '' : ' — غير مثبت'}</option>`).join('');
    const preferred = state.providers.find((provider) => provider.id === 'gemini' && provider.installed) || state.providers.find((provider) => provider.installed);
    if (preferred) $('#provider').value = preferred.id;
    $$('.provider-login').forEach((button) => { button.onclick = () => connectProvider(button.dataset.id); });
    await onProviderChange();
  } catch (error) {
    grid.innerHTML = '<div class="empty-state">تعذر قراءة الحسابات</div>';
    toast(error.message, true);
  }
}

async function connectProvider(id) {
  const provider = state.providers.find((item) => item.id === id);
  if (provider && !provider.installed) {
    toast(provider.install_hint || 'ثبّت الأداة الرسمية أولاً');
    return;
  }
  try {
    const result = await api(`/api/providers/${encodeURIComponent(id)}/login`, { method: 'POST' });
    toast(result.message);
    setTimeout(loadProviders, 1500);
  } catch (error) {
    toast(error.message, true);
  }
}

async function onProviderChange() {
  const isOllama = $('#provider').value === 'ollama';
  $('#ollamaModelRow').classList.toggle('hidden', !isOllama);
  if (!isOllama) return;
  try {
    const data = await api('/api/providers/ollama/models');
    const models = data.models || [];
    $('#ollamaModel').innerHTML = models.length
      ? models.map((model) => `<option value="${escapeHtml(model)}">${escapeHtml(model)}</option>`).join('')
      : '<option value="qwen3:8b">qwen3:8b — pull it first</option>';
  } catch {
    $('#ollamaModel').innerHTML = '<option value="qwen3:8b">qwen3:8b</option>';
  }
}

async function loadVoices() {
  try {
    const voices = await api('/api/voices');
    $('#voice').innerHTML = voices.map((voice) => `<option value="${escapeHtml(voice.id)}">${escapeHtml(voice.name)}</option>`).join('');
  } catch (error) {
    toast(error.message, true);
  }
}

async function uploadFiles(files) {
  if (!files.length) return [];
  const formData = new FormData();
  [...files].forEach((file) => formData.append('files', file));
  return api('/api/uploads', { method: 'POST', body: formData });
}

function renderMaterials() {
  const box = $('#materialList');
  box.innerHTML = state.materials.map((item, index) => `<span class="file-pill">${escapeHtml(item.name)}<button type="button" aria-label="حذف ${escapeHtml(item.name)}" data-material-index="${index}">×</button></span>`).join('');
  $$('[data-material-index]').forEach((button) => {
    button.onclick = () => {
      state.materials.splice(Number(button.dataset.materialIndex), 1);
      renderMaterials();
    };
  });
}

async function onMaterials(files) {
  try {
    const saved = await uploadFiles(files);
    state.materials.push(...saved);
    renderMaterials();
    toast(`تمت إضافة ${saved.length} ملف`);
  } catch (error) {
    toast(error.message, true);
  }
}

async function previewScript() {
  const button = $('#previewScript');
  const topic = $('#topic').value.trim();
  if (topic.length < 2) {
    toast('اكتب موضوع الفيديو أولاً', true);
    $('#topic').focus();
    return;
  }
  button.disabled = true;
  try {
    const data = await api('/api/scripts/preview', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        topic,
        provider: $('#provider').value,
        ollama_model: $('#provider').value === 'ollama' ? $('#ollamaModel').value : null,
        language: $('#language').value,
        duration: +$('#duration').value
      })
    });
    $('#script').value = data.script;
    $('#scriptMeta').textContent = `${data.word_count} كلمة · مدة صوتية تقريبية ${data.estimated_seconds} ثانية`;
    toast('تم اقتراح النص ويمكنك تعديله قبل الإنشاء');
  } catch (error) {
    toast(error.message, true);
  } finally {
    button.disabled = false;
  }
}

async function previewVoice() {
  const button = $('#previewVoice');
  button.disabled = true;
  try {
    const text = $('#script').value.trim().slice(0, 180) || 'مرحباً بك في MoneyPrinterTurbo NoAPI. هذه معاينة سريعة للصوت المختار.';
    const response = await fetch('/api/voices/preview', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ voice: $('#voice').value, text })
    });
    if (!response.ok) {
      let message = 'تعذر إنشاء المعاينة';
      try { message = (await response.json()).detail || message; } catch {}
      throw new Error(message);
    }
    const blob = await response.blob();
    if (state.voiceUrl) URL.revokeObjectURL(state.voiceUrl);
    state.voiceUrl = URL.createObjectURL(blob);
    const audio = $('#voiceAudio');
    audio.src = state.voiceUrl;
    audio.classList.remove('hidden');
    await audio.play();
  } catch (error) {
    toast(error.message, true);
  } finally {
    button.disabled = false;
  }
}

function setActiveTask(task) {
  state.task = task;
  if (task && ['queued', 'running'].includes(task.state)) localStorage.setItem(TASK_STORAGE_KEY, task.id);
  else localStorage.removeItem(TASK_STORAGE_KEY);
}

function updateProgress(task) {
  $('#progressBox').classList.remove('hidden');
  $('#progressMessage').textContent = task.message;
  $('#progressPercent').textContent = `${task.progress}%`;
  $('#progressBar').style.width = `${task.progress}%`;
  $('#previewStatus').textContent = task.state === 'completed' ? 'الفيديو جاهز' : task.state === 'failed' ? 'حدث خطأ' : task.state === 'cancelled' ? 'تم الإلغاء' : task.message;
  $('#previewHint').textContent = task.error || `Task ${task.id.slice(0, 8)}`;
  $('#cancelTask').classList.toggle('hidden', !['queued', 'running'].includes(task.state));
}

function renderResults(tasks) {
  const completed = tasks.filter((task) => task.state === 'completed' && task.output_files.length);
  const box = $('#resultsGrid');
  if (!completed.length) {
    box.innerHTML = '<div class="empty-state"><span>▣</span><p>لم يتم إنشاء فيديو بعد</p></div>';
    $('#resultsCaption').textContent = 'ستظهر الفيديوهات المكتملة هنا.';
    return;
  }
  box.innerHTML = completed.flatMap((task) => task.output_files.map((file, index) => {
    const url = `/api/tasks/${encodeURIComponent(task.id)}/files/${encodeURIComponent(file)}`;
    const artifacts = (task.artifact_files || []).filter((artifact) => ['script.txt', 'captions.srt', 'captions.ass', 'request.json'].includes(artifact));
    const artifactLinks = artifacts.map((artifact) => {
      const artifactUrl = `/api/tasks/${encodeURIComponent(task.id)}/artifacts/${encodeURIComponent(artifact)}`;
      const label = artifact === 'script.txt' ? 'النص TXT' : artifact === 'captions.srt' ? 'الترجمة SRT' : artifact === 'captions.ass' ? 'الترجمة ASS' : 'الإعدادات JSON';
      return `<a href="${artifactUrl}" download>${label}</a>`;
    }).join('');
    return `<article class="result-card"><video controls preload="metadata" src="${url}"></video><div class="result-footer"><b>${task.id.slice(0, 8)} · Video ${String(index + 1).padStart(2, '0')}</b><a href="${url}" download>تنزيل MP4 ↗</a></div><div class="result-artifacts">${artifactLinks}</div></article>`;
  })).join('');
  $('#resultsCaption').textContent = `${completed.reduce((count, task) => count + task.output_files.length, 0)} ملف جاهز`;
}

async function pollTask() {
  if (!state.task) return;
  clearTimeout(state.poll);
  try {
    const task = await api(`/api/tasks/${encodeURIComponent(state.task.id)}`);
    setActiveTask(task);
    updateProgress(task);
    if (task.state === 'completed' || task.state === 'failed' || task.state === 'cancelled') {
      state.busy = false;
      $('#generateBtn').disabled = false;
      if (task.state === 'completed') {
        const history = await api('/api/tasks');
        renderResults(history);
        toast('اكتمل إنشاء الفيديو');
        $('#results').scrollIntoView({ behavior: 'smooth' });
      } else if (task.state === 'failed') toast(task.error || 'فشل إنشاء الفيديو', true);
      return;
    }
    state.poll = setTimeout(pollTask, 1800);
  } catch (error) {
    toast(error.message, true);
    state.poll = setTimeout(pollTask, 3500);
  }
}

async function cancelTask() {
  if (!state.task || !['queued', 'running'].includes(state.task.state)) return;
  $('#cancelTask').disabled = true;
  try {
    const task = await api(`/api/tasks/${encodeURIComponent(state.task.id)}`, { method: 'DELETE' });
    setActiveTask(task);
    updateProgress(task);
    toast('تم طلب إلغاء المهمة');
  } catch (error) {
    toast(error.message, true);
  } finally {
    $('#cancelTask').disabled = false;
  }
}

async function restoreTaskHistory() {
  try {
    const history = await api('/api/tasks');
    renderResults(history);
    const activeId = localStorage.getItem(TASK_STORAGE_KEY);
    const active = history.find((task) => task.id === activeId && ['queued', 'running'].includes(task.state));
    if (active) {
      setActiveTask(active);
      updateProgress(active);
      state.busy = true;
      $('#generateBtn').disabled = true;
      pollTask();
    }
  } catch (error) {
    toast(error.message, true);
  }
}

async function submit(event) {
  event.preventDefault();
  if (state.busy) return;
  const button = $('#generateBtn');
  state.busy = true;
  button.disabled = true;
  try {
    let bgmId = null;
    if ($('#bgm').files[0]) {
      const saved = await uploadFiles($('#bgm').files);
      bgmId = saved[0]?.id || null;
    }
    const body = {
      topic: $('#topic').value.trim(), provider: $('#provider').value,
      ollama_model: $('#provider').value === 'ollama' ? $('#ollamaModel').value : null,
      language: $('#language').value, script: $('#script').value.trim() || null,
      duration: +$('#duration').value, aspect_ratio: $('input[name=aspect]:checked').value,
      clip_duration: +$('#clipDuration').value, voice: $('#voice').value,
      subtitles: $('#subtitles').checked, subtitle_format: $('#subtitleFormat').value,
      subtitle_position: $('#subtitlePosition').value,
      subtitle_font_size: +$('#subtitleFontSize').value, subtitle_color: $('#subtitleColor').value,
      subtitle_outline_color: $('#subtitleOutlineColor').value,
      subtitle_outline_width: +$('#subtitleOutlineWidth').value,
      subtitle_font_name: $('#subtitleFontName').value.trim() || 'Arial',
      gpu_backend: $('#gpuBackend').value,
      material_ids: state.materials.map((item) => item.id), bgm_id: bgmId,
      bgm_volume: +$('#bgmVolume').value, batch_count: +$('#batch').value
    };
    setActiveTask(await api('/api/tasks', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
    }));
    updateProgress(state.task);
    $('#previewStatus').textContent = 'بدأ الإنشاء';
    pollTask();
  } catch (error) {
    toast(error.message, true);
    state.busy = false;
    button.disabled = false;
  }
}

function bind() {
  $('#refreshProviders').onclick = loadProviders;
  $('#provider').onchange = onProviderChange;
  $('#previewVoice').onclick = previewVoice;
  $('#previewScript').onclick = previewScript;
  $('#script').oninput = () => { $('#scriptMeta').textContent = ''; };
  $('#cancelTask').onclick = cancelTask;
  $('#createForm').onsubmit = submit;
  $('#duration').oninput = (event) => { $('#durationOut').value = `${event.target.value} ثانية`; };
  $('#clipDuration').oninput = (event) => { $('#clipDurationOut').value = `${event.target.value} ث`; };
  $('#pickMaterials').onclick = (event) => { event.stopPropagation(); $('#materials').click(); };
  $('#uploadZone').onclick = () => $('#materials').click();
  $('#materials').onchange = (event) => onMaterials(event.target.files);
  const zone = $('#uploadZone');
  ['dragenter', 'dragover'].forEach((name) => zone.addEventListener(name, (event) => { event.preventDefault(); zone.classList.add('drag'); }));
  ['dragleave', 'drop'].forEach((name) => zone.addEventListener(name, (event) => { event.preventDefault(); zone.classList.remove('drag'); }));
  zone.addEventListener('drop', (event) => onMaterials(event.dataTransfer.files));
  $$('.nav-item').forEach((button) => { button.onclick = () => document.getElementById(button.dataset.scroll).scrollIntoView({ behavior: 'smooth' }); });
}

bind();
loadHealth();
loadProviders();
loadVoices();
restoreTaskHistory();
