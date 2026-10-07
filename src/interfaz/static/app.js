const casesEl = document.querySelector('#cases');
const detailEl = document.querySelector('#detail');
const template = document.querySelector('#case-template');
const searchForm = document.querySelector('#search-form');
const searchMeta = document.querySelector('#search-meta');
const cutoffTime = document.querySelector('#cutoff-time');
const themeButtons = document.querySelectorAll('[data-tema-opcion]');
const tabButtons = document.querySelectorAll('[data-panel]');
let selected = null;
let lastParams = {};

const PANAMA_OFFSET_MS = -5 * 60 * 60 * 1000;
const esc = value => String(value ?? '').replace(/[&<>'"]/g, char => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
}[char]));

function parseIsoUtc(value) {
  if (!value) return null;
  const normalized = String(value).endsWith('Z') ? String(value) : `${value}Z`;
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? null : date;
}

function panamaParts(date) {
  const shifted = new Date(date.getTime() + PANAMA_OFFSET_MS);
  return {
    hh: String(shifted.getUTCHours()).padStart(2, '0'),
    mm: String(shifted.getUTCMinutes()).padStart(2, '0'),
    dd: String(shifted.getUTCDate()).padStart(2, '0'),
    mo: String(shifted.getUTCMonth() + 1).padStart(2, '0'),
    yy: shifted.getUTCFullYear()
  };
}

function formatPanama(value, label = '') {
  const date = parseIsoUtc(value);
  if (!date) return label ? `${label}: sin fecha` : 'Sin fecha';
  const p = panamaParts(date);
  const text = `${label ? `${label}: ` : ''}${p.hh}:${p.mm} (UTC−5)`;
  return `<time datetime="${esc(date.toISOString())}" title="UTC: ${esc(date.toISOString())}">${esc(text)}</time>`;
}

function formatPanamaAbsolute(value) {
  const date = parseIsoUtc(value);
  if (!date) return 'Sin fecha';
  const p = panamaParts(date);
  return `${p.dd}/${p.mo}/${p.yy} ${p.hh}:${p.mm} (UTC−5)`;
}

function relativeTime(value) {
  const date = parseIsoUtc(value);
  if (!date) return 'sin referencia';
  const diff = Date.now() - date.getTime();
  const abs = Math.abs(diff);
  const units = [['día', 86400000], ['h', 3600000], ['min', 60000]];
  for (const [label, size] of units) {
    if (abs >= size) {
      const amount = Math.round(abs / size);
      const unit = label === 'día' && amount !== 1 ? 'días' : label;
      return diff >= 0 ? `hace ${amount} ${unit}` : `en ${amount} ${unit}`;
    }
  }
  return 'hace menos de 1 min';
}

function setCutoffTime() {
  const now = new Date();
  const p = panamaParts(now);
  cutoffTime.dateTime = now.toISOString();
  cutoffTime.title = `UTC: ${now.toISOString()}`;
  cutoffTime.textContent = `Corte ${p.hh}:${p.mm} (UTC−5)`;
}

function setTheme(theme) {
  const safeTheme = theme === 'sala' ? 'sala' : 'redaccion';
  if (safeTheme === 'sala') {
    document.documentElement.dataset.tema = 'sala';
  } else {
    delete document.documentElement.dataset.tema;
  }
  themeButtons.forEach(button => {
    button.setAttribute('aria-pressed', String(button.dataset.temaOpcion === safeTheme));
  });
  try {
    localStorage.setItem('lupa-tema', safeTheme);
  } catch (_) {
    return;
  }
}

function readTheme() {
  try {
    return localStorage.getItem('lupa-tema') || 'redaccion';
  } catch (_) {
    return 'redaccion';
  }
}

function setPanel(panel) {
  const safePanel = ['agenda', 'radiografia', 'mesa'].includes(panel) ? panel : 'agenda';
  document.body.dataset.panelActivo = safePanel;
  tabButtons.forEach(button => {
    button.setAttribute('aria-selected', String(button.dataset.panel === safePanel));
  });
}

async function api(path, options) {
  const response = await fetch(path, options);
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || 'Error local');
  return body;
}

function evidenceState(value) {
  if (value === 'suficiente_para_borrador') return { icon: '✓', text: 'suficiente', cls: 'state-suficiente' };
  if (value === 'parcial') return { icon: '◐', text: 'parcial', cls: 'state-parcial' };
  return { icon: '○', text: 'insuficiente', cls: 'state-insuficiente' };
}

function reviewState(value) {
  const labels = {
    en_revision: 'En revisión',
    requiere_evidencia: 'Requiere evidencia',
    aprobado_como_borrador: 'Aprobado',
    descartado: 'Descartado'
  };
  const icons = {
    en_revision: '◐',
    requiere_evidencia: '○',
    aprobado_como_borrador: '✓',
    descartado: '×'
  };
  return `${icons[value] || '◐'} ${labels[value] || String(value).replaceAll('_', ' ')}`;
}

function topicLabel(value) {
  const labels = {
    economia: 'Economía',
    logistica_canal: 'Logística/Canal',
    turismo: 'Turismo',
    servicios_publicos: 'Servicios públicos',
    eventos_naturales: 'Eventos naturales',
    regulacion: 'Regulación',
    sin_clasificar: 'Sin clasificar'
  };
  return labels[value] || 'Sin clasificar';
}

function priorityLevel(score) {
  if (score == null) return { level: 'bajo', text: 'Bajo: sin puntaje' };
  if (score >= 70) return { level: 'alto', text: 'Alto: atención inmediata' };
  if (score >= 40) return { level: 'medio', text: 'Medio: revisar agenda' };
  return { level: 'bajo', text: 'Bajo: seguimiento' };
}

function firstDate(caseData) {
  return caseData.fecha_publicacion || caseData.fecha_deteccion || null;
}

async function loadCases(params = lastParams) {
  lastParams = params;
  casesEl.textContent = 'Cargando…';
  searchMeta.textContent = '';
  try {
    const query = new URLSearchParams(Object.entries(params).filter(([, value]) => value));
    const data = await api(`/api/search?${query}`);
    casesEl.textContent = '';
    searchMeta.textContent = data.abstencion
      ? data.motivo_abstencion
      : `${data.resultados.length} resultado(s). Baseline local.`;
    for (const caseData of data.resultados) {
      const node = template.content.cloneNode(true);
      const button = node.querySelector('button');
      const evidence = evidenceState(caseData.estado_evidencia);
      const level = priorityLevel(caseData.puntaje);
      const when = firstDate(caseData);
      button.dataset.id = caseData.id;
      button.dataset.nivel = level.level;
      button.querySelector('.case-id').textContent = caseData.id;
      button.querySelector('strong').textContent = caseData.titulo;
      button.querySelector('.score').textContent = caseData.puntaje == null ? 'Sin puntaje' : `${caseData.puntaje}/100`;
      button.querySelector('.case-level').textContent = level.text;
      button.querySelector('.case-topic').textContent = topicLabel(caseData.tema);
      const evidenceEl = button.querySelector('.evidence');
      evidenceEl.textContent = `${evidence.icon} ${evidence.text}`;
      evidenceEl.classList.add(evidence.cls);
      button.querySelector('.review').textContent = `${caseData.publicaciones} publicaciones · ${caseData.procedencias_identificadas} fuentes independientes`;
      button.querySelector('.case-time').textContent = when ? `${formatPanamaAbsolute(when)} · ${relativeTime(when)}` : 'Sin fecha verificable';
      button.querySelector('.reason').textContent = caseData.motivo;
      button.addEventListener('click', () => {
        setPanel('radiografia');
        loadDetail(caseData.id);
      });
      casesEl.append(node);
    }
  } catch (error) {
    casesEl.textContent = error.message;
  }
}

function disabledBlock(title, text) {
  return `<section class="section disabled-block"><h3>${esc(title)}</h3><p>${esc(text)}</p></section>`;
}

function evidenceCard(evidence) {
  const source = evidence.noticia_titulo
    ? `<strong>${esc(evidence.noticia_titulo)}</strong>
       <p>${formatPanama(evidence.fecha_publicacion, 'Publicado')} · ${formatPanama(evidence.fecha_deteccion, 'Detectado')}</p>
       <p class="muted">${esc(evidence.alcance_texto)}</p>`
    : `<strong>${esc(evidence.indicador_id)}</strong>
       <p>${esc(evidence.pais_iso3)} · ${esc(evidence.anio)} · ${esc(evidence.valor)} ${esc(evidence.unidad)}</p>`;
  return `<article class="evidence-card">
    <span class="citation">${esc(evidence.id)} → ${esc(evidence.campo)}</span>
    ${source}
    <p>${esc(evidence.limitaciones)}</p>
  </article>`;
}

function scoreBlock(priority, grouping) {
  if (!priority) return disabledBlock('Puntaje', 'Este caso aún no tiene priorización calculada.');
  const rows = Object.keys(priority.componentes).map(key => {
    const value = Number(priority.componentes[key]);
    const percent = Math.max(0, Math.min(100, value));
    return `<div class="score-bar">
      <div class="score-row"><strong>${esc(key)}</strong><span class="mono">${esc(value)} × ${esc(priority.pesos[key])}</span></div>
      <div class="bar-track" aria-hidden="true"><span class="bar-fill" style="--valor:${percent}%"></span></div>
      <p class="muted">${esc(priority.explicacion[key])}</p>
    </div>`;
  }).join('');
  return `<section class="score-card">
    <h3>Puntaje ${esc(priority.puntaje)}/100</h3>
    <p class="muted">${esc(priority.reglas_version)} · ${esc(grouping?.publicaciones || 0)} publicaciones · ${esc(grouping?.procedencias_identificadas || 0)} fuentes independientes · ${esc(grouping?.publicaciones_origen_desconocido || 0)} origen desconocido</p>
    <div class="score-list">${rows}</div>
    <p class="warning">El puntaje ordena atención; no estima verdad ni habilita publicación.</p>
  </section>`;
}

function draftBlock(draft) {
  if (!draft) return disabledBlock('Borrador', 'No hay borrador asociado. La mesa no puede aprobar una pieza sin texto revisable.');
  return `<section class="editorial-card">
    <h3>Borrador v${esc(draft.version)}</h3>
    <p class="warning">${esc(draft.alcance_texto)}</p>
    <h4>${esc(draft.titulo)}</h4>
    <p class="reading">${esc(draft.brief)}</p>
    <details><summary>Guion y copy</summary><p>${esc(draft.guion)}</p><p>${esc(draft.copy)}</p></details>
    <p class="citation">${draft.afirmaciones.map(item => `${esc(item.id)} → ${esc(item.evidencia_id || 'sin cita')}`).join(' · ')}</p>
  </section>`;
}

function reviewForm(draft) {
  const disabled = draft ? '' : 'disabled title="No hay borrador asociado" aria-describedby="disabled-help"';
  return `<section class="editorial-card">
    <h3>Revisión humana</h3>
    <form class="review-form">
      <label>Persona revisora<input name="persona_revisora" required minlength="2" maxlength="80"></label>
      <label>Estado<select name="estado">
        <option value="en_revision">◐ En revisión</option>
        <option value="requiere_evidencia">○ Requiere evidencia</option>
        <option value="aprobado_como_borrador" ${disabled}>✓ Aprobado como borrador</option>
        <option value="descartado">× Descartado</option>
      </select></label>
      <label>Comentario<textarea name="comentario" required minlength="3" maxlength="1000"></textarea></label>
      <input type="hidden" name="borrador_id" value="${esc(draft?.id || '')}">
      <button class="submit" type="submit">Registrar revisión</button>
      <p class="message" aria-live="polite"></p>
    </form>
  </section>`;
}

function reviewsBlock(reviews) {
  if (!reviews.length) return disabledBlock('Historial', 'Todavía no hay revisiones registradas.');
  return `<section class="editorial-card">
    <h3>Historial</h3>
    ${reviews.map(review => `<article class="review-entry">
      <p><strong>${esc(reviewState(review.estado))}</strong> · ${esc(review.persona_revisora)} · ${formatPanama(review.fecha_utc)}</p>
      <p>${esc(review.comentario)}</p>
    </article>`).join('')}
  </section>`;
}

async function loadDetail(id) {
  selected = id;
  document.querySelectorAll('.case').forEach(item => item.classList.toggle('active', item.dataset.id === id));
  detailEl.className = '';
  detailEl.textContent = 'Cargando ficha…';
  try {
    const detail = await api(`/api/cases/${encodeURIComponent(id)}`);
    const caseData = detail.caso;
    const draft = detail.borradores[0];
    const evidence = evidenceState(caseData.estado_evidencia);
    const reported = detail.evidencias.filter(item => item.noticia_titulo);
    detailEl.innerHTML = `<div class="panel radiografia-panel">
      <div class="panel-header">
        <span class="mono">${esc(caseData.id)}</span>
        <h2>${esc(caseData.titulo)}</h2>
        <div class="badges"><i class="${evidence.cls}">${evidence.icon} ${evidence.text}</i><i>${reviewState(caseData.estado_revision)}</i></div>
      </div>
      <section class="section"><h3>Qué se reporta</h3><p class="reading">${esc(caseData.titulo)}</p></section>
      <section class="section"><h3>Quién lo reporta</h3><div class="grid">${reported.length ? reported.map(evidenceCard).join('') : '<p class="muted">No hay publicaciones asociadas al caso.</p>'}</div></section>
      <section class="section"><h3>Qué está respaldado</h3><div class="grid">${detail.evidencias.length ? detail.evidencias.map(evidenceCard).join('') : '<p class="warning">No hay evidencia asociada. El sistema debe abstenerse.</p>'}</div></section>
      <section class="section"><h3>Falta verificar</h3><p>${esc(caseData.preguntas_pendientes || 'Sin pendientes registrados.')}</p></section>
      <section class="section"><h3>Acción recomendada</h3><p>${caseData.estado_evidencia === 'suficiente_para_borrador' ? 'Revisar el borrador y confirmar citas antes de aprobar.' : 'Completar evidencia independiente antes de publicar.'}</p></section>
      ${scoreBlock(detail.priorizacion, detail.agrupacion)}
    </div>
    <div class="panel mesa-panel">
      <div class="panel-header"><h2>Mesa editorial</h2><p class="muted">Borrador y revisión existentes.</p></div>
      ${draftBlock(draft)}
      ${reviewForm(draft)}
      ${reviewsBlock(detail.revisiones)}
    </div>`;
    detailEl.querySelector('form').addEventListener('submit', submitReview);
  } catch (error) {
    detailEl.textContent = error.message;
  }
}

async function submitReview(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const message = form.querySelector('.message');
  const data = Object.fromEntries(new FormData(form));
  message.textContent = 'Guardando…';
  try {
    await api(`/api/cases/${encodeURIComponent(selected)}/reviews`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    await loadCases(lastParams);
    await loadDetail(selected);
  } catch (error) {
    message.textContent = error.message;
  }
}

searchForm.addEventListener('submit', event => {
  event.preventDefault();
  loadCases(Object.fromEntries(new FormData(searchForm)));
});

document.querySelector('#refresh').addEventListener('click', () => {
  searchForm.reset();
  loadCases({});
});

themeButtons.forEach(button => button.addEventListener('click', () => setTheme(button.dataset.temaOpcion)));
tabButtons.forEach(button => button.addEventListener('click', () => setPanel(button.dataset.panel)));

setCutoffTime();
setTheme(readTheme());
setPanel('agenda');
loadCases({});
