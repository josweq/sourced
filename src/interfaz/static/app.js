const casesEl = document.querySelector('#cases');
const detailEl = document.querySelector('#detail');
const template = document.querySelector('#case-template');
const searchForm = document.querySelector('#search-form');
const searchMeta = document.querySelector('#search-meta');
const cutoffTime = document.querySelector('#cutoff-time');
const filterCount = document.querySelector('#filter-count');
const themeButtons = document.querySelectorAll('[data-tema-opcion]');
const tabButtons = document.querySelectorAll('[data-panel]');
let selected = null;
let lastParams = {};
let currentDetail = null;

const PANAMA_OFFSET_MS = -5 * 60 * 60 * 1000;
const MONTHS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
const esc = value => String(value ?? '').replace(/[&<>'"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));

function parseIsoUtc(value) {
  if (!value) return null;
  const date = new Date(String(value).endsWith('Z') ? String(value) : `${value}Z`);
  return Number.isNaN(date.getTime()) ? null : date;
}

function panamaText(value, withRelative = false) {
  const date = parseIsoUtc(value);
  if (!date) return 'Sin fecha';
  const shifted = new Date(date.getTime() + PANAMA_OFFSET_MS);
  const absolute = `${shifted.getUTCDate()} ${MONTHS[shifted.getUTCMonth()]} ${shifted.getUTCFullYear()} · ${String(shifted.getUTCHours()).padStart(2, '0')}:${String(shifted.getUTCMinutes()).padStart(2, '0')} (UTC−5)`;
  const relative = withRelative ? relativeTime(value) : '';
  return relative ? `${absolute} · ${relative}` : absolute;
}

function relativeTime(value) {
  const date = parseIsoUtc(value);
  if (!date) return '';
  const diff = Date.now() - date.getTime();
  const abs = Math.abs(diff);
  if (abs > 48 * 60 * 60 * 1000) return '';
  for (const [label, size] of [['día', 86400000], ['h', 3600000], ['min', 60000]]) {
    if (abs >= size) {
      const amount = Math.round(abs / size);
      return diff >= 0 ? `hace ${amount} ${label === 'día' && amount !== 1 ? 'días' : label}` : `en ${amount} ${label}`;
    }
  }
  return 'hace menos de 1 min';
}

function formatPanama(value, label = '', withRelative = false) {
  const date = parseIsoUtc(value);
  const prefix = label ? `${label}: ` : '';
  return `<time datetime="${esc(date?.toISOString() || '')}" title="${date ? `UTC: ${esc(date.toISOString())}` : 'Sin fecha'}">${esc(prefix + panamaText(value, withRelative))}</time>`;
}

function setCutoffTime(value) {
  const date = parseIsoUtc(value);
  if (!date) {
    cutoffTime.removeAttribute('datetime');
    cutoffTime.textContent = 'Corte: sin fecha';
    return;
  }
  cutoffTime.dateTime = date.toISOString();
  cutoffTime.title = `UTC: ${date.toISOString()}`;
  cutoffTime.textContent = `Corte: ${panamaText(value)}`;
}

async function api(path, options) {
  const response = await fetch(path, options);
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || 'Error local');
  return body;
}

async function loadEstado() {
  try {
    const data = await api('/api/estado');
    setCutoffTime(data.corte);
    const status = document.querySelector('.status');
    status.textContent = data.modelo.ollama_responde ? `Modelo local: ${data.modelo.nombre}` : 'Modelo local no disponible';
    status.title = data.modelo.motivo || '';
  } catch (_) {}
}

function setTheme(theme) {
  const safeTheme = theme === 'sala' ? 'sala' : 'redaccion';
  if (safeTheme === 'sala') document.documentElement.dataset.tema = 'sala';
  else delete document.documentElement.dataset.tema;
  themeButtons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.temaOpcion === safeTheme)));
  try { localStorage.setItem('lupa-tema', safeTheme); } catch (_) {}
}

function readTheme() {
  try { return localStorage.getItem('lupa-tema') || 'redaccion'; } catch (_) { return 'redaccion'; }
}

function setPanel(panel) {
  const safePanel = ['agenda', 'radiografia', 'mesa'].includes(panel) ? panel : 'agenda';
  document.body.dataset.panelActivo = safePanel;
  tabButtons.forEach(button => button.setAttribute('aria-selected', String(button.dataset.panel === safePanel)));
}

function evidenceState(value) {
  if (value === 'suficiente_para_borrador') return { icon: '✓', text: 'suficiente', cls: 'state-suficiente' };
  if (value === 'parcial') return { icon: '◐', text: 'parcial', cls: 'state-parcial' };
  return { icon: '○', text: 'insuficiente', cls: 'state-insuficiente' };
}

function humanEnum(value) {
  const labels = { titular_metadatos: 'Solo titular y metadatos', extracto_autorizado: 'Extracto autorizado', texto_autorizado: 'Texto autorizado', sustenta: 'Sustenta', contradice: 'Contradice', contextualiza: 'Contextualiza', hecho: 'Hecho', declaracion: 'Declaración atribuida', inferencia: 'Inferencia', hipotesis: 'Hipótesis' };
  return labels[value] || String(value || '').replaceAll('_', ' ');
}

function reviewState(value) {
  const labels = { nuevo: 'Nuevo', en_revision: 'En revisión', requiere_evidencia: 'Requiere evidencia', aprobado_como_borrador: 'Aprobado como borrador', descartado: 'Descartado' };
  const icons = { nuevo: '●', en_revision: '✎', requiere_evidencia: '!', aprobado_como_borrador: '✔', descartado: '✕' };
  return `${icons[value] || '●'} ${labels[value] || humanEnum(value)}`;
}

function topicLabel(value) {
  const labels = { economia: 'Economía', logistica_canal: 'Logística/Canal', turismo: 'Turismo', servicios_publicos: 'Servicios públicos', eventos_naturales: 'Eventos naturales', regulacion: 'Regulación', sin_clasificar: 'Sin clasificar' };
  return labels[value] || 'Sin clasificar';
}

function priorityLevel(score) {
  if (score == null) return { level: 'bajo', text: 'Bajo: sin puntaje' };
  if (score >= 70) return { level: 'alto', text: 'Alto: atención inmediata' };
  if (score >= 40) return { level: 'medio', text: 'Medio' };
  return { level: 'bajo', text: 'Bajo: seguimiento' };
}

function plural(value, singular, pluralText) {
  const count = Number(value || 0);
  return `${count} ${count === 1 ? singular : pluralText}`;
}

function sourceCountText(caseData) {
  return `${plural(caseData.publicaciones, 'pub', 'pub')} · ${plural(caseData.procedencias_identificadas, 'fuente independiente', 'fuentes independientes')}`;
}

function updateFilterCount() {
  const data = Object.fromEntries(new FormData(searchForm));
  const active = ['tema', 'evidencia', 'medio', 'desde', 'hasta'].filter(name => data[name]).length;
  filterCount.textContent = `${active} ${active === 1 ? 'activo' : 'activos'}`;
}

async function loadCases(params = lastParams) {
  lastParams = params;
  updateFilterCount();
  casesEl.textContent = 'Cargando…';
  searchMeta.textContent = '';
  try {
    const query = new URLSearchParams(Object.entries(params).filter(([, value]) => value));
    const data = await api(`/api/search?${query}`);
    setCutoffTime(data.snapshot?.fecha_corte_utc);
    casesEl.textContent = '';
    searchMeta.textContent = data.abstencion ? data.motivo_abstencion : `${data.resultados.length} resultado(s).`;
    for (const caseData of data.resultados) {
      const node = template.content.cloneNode(true);
      const button = node.querySelector('button');
      const evidence = evidenceState(caseData.estado_evidencia);
      const level = priorityLevel(caseData.puntaje);
      const when = caseData.fecha_publicacion || caseData.fecha_deteccion;
      button.dataset.id = caseData.id;
      button.dataset.nivel = level.level;
      button.title = `ID técnico: ${caseData.id}`;
      button.querySelector('.case-meta').textContent = `${topicLabel(caseData.tema)} · ${when ? panamaText(when, false).replace(' (UTC−5)', '').replace(` ${new Date().getFullYear()}`, '') : 'sin fecha'}`;
      button.querySelector('.score').textContent = caseData.puntaje == null ? 'Sin puntaje' : `${Math.round(Number(caseData.puntaje))}/100`;
      button.querySelector('strong').textContent = caseData.titulo;
      const evidenceEl = button.querySelector('.evidence');
      evidenceEl.textContent = `${evidence.icon} ${evidence.text}`;
      evidenceEl.classList.add(evidence.cls);
      button.querySelector('.source-count').textContent = sourceCountText(caseData).replace(/ independientes?/, '');
      button.querySelector('.reason').textContent = caseData.coincidencias?.length ? `Coincide: ${caseData.coincidencias.join(', ')}` : '';
      button.addEventListener('click', () => { setPanel('radiografia'); loadDetail(caseData.id); });
      casesEl.append(node);
    }
  } catch (error) {
    casesEl.textContent = error.message;
  }
}

function disabledBlock(title, text) {
  return `<section class="section disabled-block"><h3>${esc(title)}</h3><p>${esc(text)}</p></section>`;
}

function domainFromUrl(value) {
  try { return new URL(value).hostname.replace(/^www\./, ''); } catch (_) { return ''; }
}

function evidenceLabel(evidence) {
  if (evidence?.noticia_titulo) return `Titular · ${evidence.medio || domainFromUrl(evidence.noticia_url) || 'medio'}`;
  return evidence?.indicador_id ? `Banco Mundial · ${evidence.pais_iso3 || ''} ${evidence.anio || ''}`.trim() : 'Evidencia';
}

function sourceRows(evidences, grouping) {
  const news = evidences.filter(item => item.noticia_titulo);
  if (!news.length) return '<p class="muted">No hay publicaciones asociadas al caso.</p>';
  return `<p class="muted">${sourceCountText({ publicaciones: grouping?.publicaciones || news.length, procedencias_identificadas: grouping?.procedencias_identificadas || 0 })}</p>
  <div class="source-list">${news.map(item => `<article id="evidencia-${esc(item.id)}" class="source-row evidence-target" data-evidence-id="${esc(item.id)}">
    <strong>Publicado por ${esc(item.medio || domainFromUrl(item.noticia_url) || 'medio no identificado')}</strong>
    <span>${esc(item.procedencia_id ? `Fuente primaria: ${item.procedencia_id}` : 'Fuente primaria: no identificada')}</span>
    <span>${formatPanama(item.fecha_publicacion || item.fecha_deteccion, item.fecha_publicacion ? 'Publicado' : 'Detectado', true)}</span>
  </article>`).join('')}</div>`;
}

function supportedClaims(draft, evidences) {
  if (!draft) return disabledBlock('Qué está respaldado', 'Todavía no hay afirmaciones citadas.');
  const byEvidence = new Map(evidences.map(item => [item.id, item]));
  const seen = new Set();
  const claims = (draft.afirmaciones || []).filter(item => {
    const key = `${(item.texto || '').replace(/\s*\([^)]*\)\.?$/, '').trim()}|${item.evidencia_id}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  if (!claims.length) return disabledBlock('Qué está respaldado', 'El borrador no tiene afirmaciones citadas.');
  return `<section class="section"><h3>Qué está respaldado</h3><div class="claim-list">${claims.map(item => {
    const label = evidenceLabel(byEvidence.get(item.evidencia_id));
    return `<article class="claim-row"><p>${esc(item.texto || 'Afirmación sin texto visible.')}</p>
      <button class="citation citation-chip" type="button" data-cita="${esc(item.evidencia_id || '')}">${esc(label)} · ${esc(humanEnum(item.relacion))}</button>
      <details><summary>ID técnico</summary><span class="mono">${esc(item.id)}${item.evidencia_id ? ` · ${esc(item.evidencia_id)}` : ''}</span></details></article>`;
  }).join('')}</div></section>`;
}

function scoreBlock(priority, grouping) {
  if (!priority) return disabledBlock('Puntaje', 'Este caso aún no tiene priorización calculada.');
  const rows = Object.keys(priority.componentes).map(key => {
    const value = Number(priority.componentes[key]);
    return `<div class="score-bar"><div class="score-row"><strong>${esc(key)}</strong><span class="mono">${esc(value)} × ${esc(priority.pesos[key])}</span></div>
      <div class="bar-track" aria-hidden="true"><span class="bar-fill" style="--valor:${Math.max(0, Math.min(100, value))}%"></span></div>
      <p class="muted">${esc(priority.explicacion[key])}</p></div>`;
  }).join('');
  return `<section class="score-card"><h3>Puntaje ${esc(Math.round(Number(priority.puntaje)))}/100</h3><p class="muted">${esc(priority.reglas_version)} · ${esc(plural(grouping?.publicaciones, 'publicación', 'publicaciones'))}</p><div class="score-list">${rows}</div><p class="warning">El puntaje ordena atención; no estima verdad ni habilita publicación.</p></section>`;
}

function wordCount(text) {
  return (text || '').trim().split(/\s+/).filter(Boolean).length;
}

function scriptSeconds(text, ppm) {
  const clean = (text || '').replace(/\[(VO|SOT)[^\]]*\]/gi, ' ').replace(/\([^)]*\)/g, ' ');
  return Math.round((wordCount(clean) / Math.max(1, ppm)) * 60);
}

function readPpm() {
  try { return Number(localStorage.getItem('lupa-ppm')) || 160; } catch (_) { return 160; }
}

function cronLabel(seconds) {
  if (seconds < 45) return { cls: 'timer-low', text: `${seconds} s · falta para el objetivo` };
  if (seconds > 60) return { cls: 'timer-high', text: `${seconds} s · se pasa del objetivo` };
  return { cls: 'timer-ok', text: `${seconds} s · dentro del objetivo` };
}

function citationButton(item, evidences) {
  return `<button class="citation citation-chip" type="button" data-cita="${esc(item.evidencia_id || '')}">${esc(evidenceLabel(evidences.find(ev => ev.id === item.evidencia_id)))}</button>`;
}

function sectionClaims(draft, evidences, section) {
  const claims = (draft?.afirmaciones || []).filter(item => item.seccion === section);
  if (!claims.length) return `<p class="muted">Sin oraciones citadas en esta sección.</p>`;
  return `<div class="draft-sentences">${claims.map(item => `<p class="reading cited-sentence"><span>${esc(item.texto)}</span> ${citationButton(item, evidences)}</p>`).join('')}</div>`;
}

function draftTabContent(draft, evidences, tab) {
  if (tab === 'preguntas') return `<ol class="question-list">${(draft.preguntas || []).map(p => `<li>${esc(p)}</li>`).join('')}</ol>`;
  return sectionClaims(draft, evidences, tab);
}

function removedBlock(draft) {
  const removed = draft?.meta?.guardian?.retiradas || [];
  if (!removed.length) return '';
  return `<details class="guardian-removed"><summary>Retirado por el guardián (${removed.length})</summary>${removed.map(item => `<article><p>${esc(item.texto || '')}</p><small>${esc(item.motivo || 'Sin motivo registrado')}</small></article>`).join('')}</details>`;
}

function draftBlock(draft, evidences, versions) {
  if (!draft) return `<section class="editorial-card disabled-block" aria-disabled="true"><h3>Mesa editorial</h3><p><strong>Sin borrador todavía.</strong></p><p>Usa el modelo local para generar texto con afirmaciones citadas.</p><button class="submit regenerate" type="button">Regenerar con el modelo local</button><p class="message" aria-live="polite"></p></section>`;
  const ppm = readPpm();
  const timer = cronLabel(scriptSeconds(draft.guion, ppm));
  return `<section class="editorial-card"><div class="draft-head"><h3>Borrador v${esc(draft.version)}</h3><button class="submit regenerate" type="button">Regenerar con el modelo local</button></div>
    <p class="warning">Borrador generado por IA — requiere revisión humana</p>${draft.alcance_texto === 'titular_metadatos' ? '<p class="warning">Basado únicamente en titular/metadatos</p>' : ''}
    <nav class="draft-tabs" aria-label="Secciones del borrador">${['brief', 'guion', 'copy', 'preguntas'].map((tab, index) => `<button type="button" data-draft-tab="${tab}" aria-selected="${index === 0 ? 'true' : 'false'}">${esc(tab === 'guion' ? 'Guion' : tab.charAt(0).toUpperCase() + tab.slice(1))}</button>`).join('')}</nav>
    <div class="draft-panel" data-draft-panel="brief">${draftTabContent(draft, evidences, 'brief')}<p class="counter">${wordCount(draft.brief)}/250 palabras</p></div>
    <div class="draft-panel hidden" data-draft-panel="guion"><div class="timer ${timer.cls}"><strong>${esc(timer.text)}</strong><label>PPM<input id="ppm-input" type="number" min="80" max="240" value="${esc(ppm)}"></label></div>${draftTabContent(draft, evidences, 'guion')}</div>
    <div class="draft-panel hidden" data-draft-panel="copy">${draftTabContent(draft, evidences, 'copy')}<p class="counter">${wordCount(draft.copy)}/80 palabras</p></div>
    <div class="draft-panel hidden" data-draft-panel="preguntas">${draftTabContent(draft, evidences, 'preguntas')}</div>${removedBlock(draft)}
    <details class="edit-draft"><summary>Editar en línea</summary><form class="draft-edit-form"><label>Título<input name="titulo" maxlength="180" value="${esc(draft.titulo)}"></label><label>Enfoque<textarea name="enfoque" maxlength="600">${esc(draft.enfoque)}</textarea></label><label>Brief <span class="counter" data-count-for="brief">${wordCount(draft.brief)}/250</span><textarea name="brief" maxlength="4000">${esc(draft.brief)}</textarea></label><label>Guion<textarea name="guion" maxlength="5000">${esc(draft.guion)}</textarea></label><label>Copy <span class="counter" data-count-for="copy">${wordCount(draft.copy)}/80</span><textarea name="copy" maxlength="1200">${esc(draft.copy)}</textarea></label><button class="submit" type="submit">Guardar como versión nueva</button><p class="message" aria-live="polite"></p></form></details>
    <details><summary>Versiones</summary>${versions.map(item => `<p class="version-row"><strong>v${esc(item.version)}</strong> · ${esc(item.generador)} · ${formatPanama(item.fecha_utc)}</p>`).join('')}</details><details><summary>ID técnico</summary><p class="mono">${esc(draft.id)}</p></details></section>`;
}

function reviewForm(draft) {
  const disabled = draft ? '' : 'disabled title="No hay borrador asociado" aria-describedby="disabled-help"';
  return `<section class="editorial-card"><h3>Revisión humana</h3><form class="review-form"><label>Persona revisora<input name="persona_revisora" required minlength="2" maxlength="80"></label><label>Estado<select name="estado"><option value="en_revision">✎ En revisión</option><option value="requiere_evidencia">! Requiere evidencia</option><option value="aprobado_como_borrador" ${disabled}>✔ Aprobado como borrador</option><option value="descartado">✕ Descartado</option></select></label><label>Comentario<textarea name="comentario" required minlength="3" maxlength="1000"></textarea></label><input type="hidden" name="borrador_id" value="${esc(draft?.id || '')}"><button class="submit" type="submit">Registrar revisión</button><p class="message" aria-live="polite"></p></form></section>`;
}

function reviewsBlock(reviews) {
  if (!reviews.length) return disabledBlock('Historial', 'Todavía no hay revisiones registradas.');
  return `<section class="editorial-card"><h3>Historial</h3>${reviews.map(review => `<article class="review-entry"><p><strong>${esc(reviewState(review.estado))}</strong> · ${esc(review.persona_revisora)} · ${formatPanama(review.fecha_utc)}</p><p>${esc(review.comentario)}</p></article>`).join('')}</section>`;
}

async function loadDetail(id) {
  selected = id;
  currentDetail = null;
  document.querySelectorAll('.case').forEach(item => item.classList.toggle('active', item.dataset.id === id));
  detailEl.className = '';
  detailEl.textContent = 'Cargando ficha…';
  try {
    const detail = await api(`/api/cases/${encodeURIComponent(id)}`);
    currentDetail = detail;
    setCutoffTime(detail.snapshot?.fecha_corte_utc);
    const caseData = detail.caso;
    const draft = detail.borradores[0];
    const evidence = evidenceState(caseData.estado_evidencia);
    detailEl.innerHTML = `<div class="panel radiografia-panel"><div class="panel-header"><h2>${esc(caseData.titulo)}</h2><span class="technical-id" title="ID técnico">${esc(caseData.id)}</span><div class="badges"><i class="${evidence.cls}">${evidence.icon} ${evidence.text}</i><i>${reviewState(caseData.estado_revision)}</i></div></div><section class="section"><h3>Qué se reporta</h3><p class="reading">${esc(caseData.titulo)}</p></section><section class="section"><h3>Quién lo reporta</h3>${sourceRows(detail.evidencias, detail.agrupacion)}</section>${supportedClaims(draft, detail.evidencias)}<section class="section"><h3>Falta verificar</h3><p>${esc(caseData.preguntas_pendientes || 'Sin pendientes registrados.')}</p></section><section class="section"><h3>Acción recomendada</h3><p>${caseData.estado_evidencia === 'suficiente_para_borrador' ? 'Revisar el borrador y confirmar citas antes de aprobar.' : 'Completar evidencia independiente antes de publicar.'}</p></section>${scoreBlock(detail.priorizacion, detail.agrupacion)}</div><div class="panel mesa-panel"><div class="panel-header"><h2>Mesa editorial</h2><p class="muted">Borrador y revisión.</p></div>${draftBlock(draft, detail.evidencias, detail.borradores)}${reviewForm(draft)}${reviewsBlock(detail.revisiones)}</div>`;
    wireDraftControls();
    const review = detailEl.querySelector('.review-form');
    if (review) review.addEventListener('submit', submitReview);
  } catch (error) {
    detailEl.textContent = error.message;
  }
}

function wireDraftControls() {
  detailEl.querySelectorAll('[data-draft-tab]').forEach(button => button.addEventListener('click', () => {
    detailEl.querySelectorAll('[data-draft-tab]').forEach(item => item.setAttribute('aria-selected', String(item === button)));
    detailEl.querySelectorAll('[data-draft-panel]').forEach(panel => panel.classList.toggle('hidden', panel.dataset.draftPanel !== button.dataset.draftTab));
  }));
  detailEl.querySelectorAll('[data-cita]').forEach(button => button.addEventListener('click', () => {
    const id = button.dataset.cita;
    detailEl.querySelectorAll('.evidence-highlight').forEach(item => item.classList.remove('evidence-highlight'));
    const target = detailEl.querySelector(`[data-evidence-id="${CSS.escape(id)}"]`);
    if (target) { target.classList.add('evidence-highlight'); target.scrollIntoView({ block: 'center', behavior: 'smooth' }); }
  }));
  const ppm = detailEl.querySelector('#ppm-input');
  if (ppm) ppm.addEventListener('change', () => { try { localStorage.setItem('lupa-ppm', ppm.value); } catch (_) {} loadDetail(selected); });
  detailEl.querySelectorAll('.regenerate').forEach(button => button.addEventListener('click', regenerateDraft));
  const editForm = detailEl.querySelector('.draft-edit-form');
  if (editForm) {
    editForm.addEventListener('input', () => {
      const data = Object.fromEntries(new FormData(editForm));
      editForm.querySelector('[data-count-for="brief"]').textContent = `${wordCount(data.brief)}/250`;
      editForm.querySelector('[data-count-for="copy"]').textContent = `${wordCount(data.copy)}/80`;
    });
    editForm.addEventListener('submit', saveDraftEdit);
  }
}

async function regenerateDraft(event) {
  const button = event.currentTarget;
  const message = button.parentElement.querySelector('.message') || detailEl.querySelector('.message');
  button.disabled = true;
  if (message) message.textContent = 'Generando con el modelo local…';
  try {
    await api(`/api/cases/${encodeURIComponent(selected)}/borrador`, { method: 'POST' });
    await loadCases(lastParams);
    await loadDetail(selected);
  } catch (error) {
    if (message) message.textContent = error.message;
  } finally {
    button.disabled = false;
  }
}

async function saveDraftEdit(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const message = form.querySelector('.message');
  const draft = currentDetail?.borradores?.[0];
  if (!draft) return;
  message.textContent = 'Guardando versión nueva…';
  try {
    await api(`/api/borradores/${encodeURIComponent(draft.id)}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(Object.fromEntries(new FormData(form))) });
    await loadDetail(selected);
  } catch (error) {
    message.textContent = error.message;
  }
}

async function submitReview(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const message = form.querySelector('.message');
  message.textContent = 'Guardando…';
  try {
    await api(`/api/cases/${encodeURIComponent(selected)}/reviews`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(Object.fromEntries(new FormData(form))) });
    await loadCases(lastParams);
    await loadDetail(selected);
  } catch (error) {
    message.textContent = error.message;
  }
}

const askForm = document.querySelector('#ask-form');

function consultaBadge(estado) {
  if (estado === 'respondida') return '<i class="state-suficiente">✓ Respondida con evidencia citada</i>';
  if (estado === 'contexto_sectorial') return '<i class="state-parcial">◆ Contexto sectorial</i>';
  return '<i class="state-insuficiente">○ Me abstengo: no hay evidencia suficiente</i>';
}

function consultaCita(af) {
  const c = af.cita || {};
  if (c.tipo === 'indicador') {
    return `<span class="mono">${esc(c.fuente)} · ${esc(c.indicador)} · ${esc(c.anio)}</span> · <a href="${esc(c.url)}" target="_blank" rel="noopener noreferrer">fuente</a>`;
  }
  const medios = (af.medios_del_evento || []).filter(Boolean);
  const indep = medios.length > 1 ? ` · ${medios.length} medios publican el evento: ${medios.map(esc).join(', ')}` : '';
  return `${esc(c.medio || '')} · ${esc(c.fecha ? panamaText(c.fecha, true) : 'sin fecha')} · <a href="${esc(c.url)}" target="_blank" rel="noopener noreferrer">abrir titular</a>${indep}`;
}

function renderConsulta(r) {
  const afirm = (r.afirmaciones || []).map(af => `<li class="consulta-item"><p class="reading">${esc(af.texto)}</p><p class="muted">${af.tipo === 'contexto' ? 'Contexto (no responde lo pedido) · ' : ''}${consultaCita(af)}</p></li>`).join('');
  const vacios = (r.vacios || []).map(v => `<li>${esc(v)}</li>`).join('');
  detailEl.className = '';
  detailEl.innerHTML = `<div class="panel radiografia-panel"><div class="panel-header"><h2>Respuesta</h2><p class="muted">«${esc(r.pregunta)}»</p><div class="badges">${consultaBadge(r.estado)}</div></div><section class="section"><p>${esc(r.respuesta)}</p>${afirm ? `<ul class="consulta-lista">${afirm}</ul>` : ''}</section>${vacios ? `<section class="section"><h3>Falta verificar</h3><ul>${vacios}</ul></section>` : ''}<p class="technical-id">Método: ${esc(r.metodo)} · ${esc(r.latencia_ms)} ms · modelo local ${esc((r.reglas || {}).modelo || '')}</p></div><div class="panel mesa-panel"><div class="panel-header"><h2>Mesa editorial</h2><p class="muted">Abre un caso de la agenda para trabajar su borrador.</p></div></div>`;
  setPanel('radiografia');
}

askForm.addEventListener('submit', async event => {
  event.preventDefault();
  const pregunta = askForm.pregunta.value.trim();
  if (!pregunta) { askForm.pregunta.focus(); return; }
  const button = askForm.querySelector('button');
  button.disabled = true; button.textContent = 'Buscando…';
  detailEl.className = 'empty';
  detailEl.innerHTML = '<div><strong>Buscando evidencia en el snapshot…</strong><p>La primera pregunta puede tardar mientras carga el modelo local.</p></div>';
  try {
    renderConsulta(await api('/api/consulta', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pregunta }) }));
  } catch (error) {
    detailEl.className = 'empty';
    detailEl.innerHTML = `<div><strong>No se pudo responder</strong><p>${esc(error.message)}</p></div>`;
  } finally {
    button.disabled = false; button.textContent = 'Preguntar';
  }
});

searchForm.addEventListener('submit', event => { event.preventDefault(); loadCases(Object.fromEntries(new FormData(searchForm))); });
searchForm.addEventListener('input', updateFilterCount);
searchForm.addEventListener('change', updateFilterCount);
document.querySelector('#refresh').addEventListener('click', () => { searchForm.reset(); loadCases({}); });
themeButtons.forEach(button => button.addEventListener('click', () => setTheme(button.dataset.temaOpcion)));
tabButtons.forEach(button => button.addEventListener('click', () => setPanel(button.dataset.panel)));

setCutoffTime();
setTheme(readTheme());
setPanel('agenda');
updateFilterCount();
loadCases({});
loadEstado();
