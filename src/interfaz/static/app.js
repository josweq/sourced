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

const PANAMA_OFFSET_MS = -5 * 60 * 60 * 1000;
const MONTHS = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
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
    dd: shifted.getUTCDate(),
    mo: MONTHS[shifted.getUTCMonth()],
    yy: shifted.getUTCFullYear()
  };
}

function panamaText(value, withRelative = false) {
  const date = parseIsoUtc(value);
  if (!date) return 'Sin fecha';
  const p = panamaParts(date);
  const absolute = `${p.dd} ${p.mo} ${p.yy} · ${p.hh}:${p.mm} (UTC−5)`;
  const relative = withRelative ? relativeTime(value) : '';
  return relative ? `${absolute} · ${relative}` : absolute;
}

function formatPanama(value, label = '', withRelative = false) {
  const date = parseIsoUtc(value);
  const text = panamaText(value, withRelative);
  const prefix = label ? `${label}: ` : '';
  return `<time datetime="${esc(date?.toISOString() || '')}" title="${date ? `UTC: ${esc(date.toISOString())}` : 'Sin fecha'}">${esc(prefix + text)}</time>`;
}

function relativeTime(value) {
  const date = parseIsoUtc(value);
  if (!date) return '';
  const diff = Date.now() - date.getTime();
  const abs = Math.abs(diff);
  if (abs > 48 * 60 * 60 * 1000) return '';
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
    nuevo: 'Nuevo',
    en_revision: 'En revisión',
    requiere_evidencia: 'Requiere evidencia',
    aprobado_como_borrador: 'Aprobado como borrador',
    descartado: 'Descartado'
  };
  const icons = {
    nuevo: '●',
    en_revision: '✎',
    requiere_evidencia: '!',
    aprobado_como_borrador: '✔',
    descartado: '✕'
  };
  return `${icons[value] || '●'} ${labels[value] || humanEnum(value)}`;
}

function humanEnum(value) {
  const labels = {
    titular_metadatos: 'Solo titular y metadatos',
    extracto_autorizado: 'Extracto autorizado',
    texto_autorizado: 'Texto autorizado',
    sustenta: 'Sustenta',
    contradice: 'Contradice',
    contextualiza: 'Contextualiza',
    hecho: 'Hecho',
    declaracion: 'Declaración atribuida',
    inferencia: 'Inferencia',
    hipotesis: 'Hipótesis'
  };
  return labels[value] || String(value || '').replaceAll('_', ' ');
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
  if (score >= 40) return { level: 'medio', text: 'Medio' };
  return { level: 'bajo', text: 'Bajo: seguimiento' };
}

function firstDate(caseData) {
  return caseData.fecha_publicacion || caseData.fecha_deteccion || null;
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
    const hasTextSearch = Boolean((params.q || '').trim());
    searchMeta.textContent = data.abstencion ? data.motivo_abstencion : `${data.resultados.length} resultado(s).`;
    if (!data.abstencion && hasTextSearch) {
      searchMeta.textContent += ` Coincidencia por texto: ${data.consulta}.`;
    }
    for (const caseData of data.resultados) {
      const node = template.content.cloneNode(true);
      const button = node.querySelector('button');
      const evidence = evidenceState(caseData.estado_evidencia);
      const level = priorityLevel(caseData.puntaje);
      const when = firstDate(caseData);
      button.dataset.id = caseData.id;
      button.dataset.nivel = level.level;
      button.title = `ID técnico: ${caseData.id}`;
      button.querySelector('.case-meta').textContent = `${topicLabel(caseData.tema)} · ${when ? panamaText(when, true).replace(' (UTC−5)', '') : 'sin fecha'}`;
      button.querySelector('.score').title = `Prioridad ${level.text.toLowerCase()}`;
      button.querySelector('strong').textContent = caseData.titulo;
      button.querySelector('.score').textContent = caseData.puntaje == null ? 'Sin puntaje' : `${Math.round(Number(caseData.puntaje))}/100`;
      const evidenceEl = button.querySelector('.evidence');
      evidenceEl.textContent = `${evidence.icon} ${evidence.text}`;
      evidenceEl.classList.add(evidence.cls);
      button.querySelector('.source-count').textContent = sourceCountText(caseData).replace(/ independientes?/, '');
      button.querySelector('.source-count').title = sourceCountText(caseData);
      button.querySelector('.reason').textContent = hasTextSearch && caseData.coincidencias.length
        ? `Coincide: ${caseData.coincidencias.join(', ')}`
        : '';
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

function evidenceLabel(evidence) {
  if (evidence?.noticia_titulo) {
    const medium = evidence.medio || domainFromUrl(evidence.noticia_url) || 'medio';
    return `Titular · ${medium}`;
  }
  return evidence?.indicador_id ? `Dato · ${evidence.indicador_id}` : 'Evidencia';
}

function domainFromUrl(value) {
  try {
    return new URL(value).hostname.replace(/^www\./, '');
  } catch (_) {
    return '';
  }
}

function sourceRows(evidences, grouping) {
  const news = evidences.filter(item => item.noticia_titulo);
  const seen = new Set();
  const rows = news.filter(item => {
    const key = `${item.medio || ''}|${item.procedencia_id || ''}|${item.noticia_url || item.noticia_titulo}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  if (!rows.length) return '<p class="muted">No hay publicaciones asociadas al caso.</p>';
  return `<p class="muted">${sourceCountText({
    publicaciones: grouping?.publicaciones || rows.length,
    procedencias_identificadas: grouping?.procedencias_identificadas || 0
  })}</p>
  <div class="source-list">${rows.map(item => `<article class="source-row">
    <strong>Publicado por ${esc(item.medio || domainFromUrl(item.noticia_url) || 'medio no identificado')}</strong>
    <span>${esc(item.procedencia_id ? `Fuente primaria: ${item.procedencia_id}` : 'Fuente primaria: no identificada')}</span>
    <span>${formatPanama(item.fecha_publicacion || item.fecha_deteccion, item.fecha_publicacion ? 'Publicado' : 'Detectado', true)}</span>
  </article>`).join('')}</div>`;
}

function supportedClaims(draft, evidences) {
  if (!draft) {
    return `<section class="section disabled-block" aria-disabled="true">
      <h3>Qué está respaldado</h3>
      <p><strong>Solo titulares: nada confirmado todavía.</strong></p>
      <p>Cuando el modelo local genere un borrador, aquí verás cada afirmación con su cita. Por ahora no hay texto aprobable.</p>
    </section>`;
  }
  const byEvidence = new Map(evidences.map(item => [item.id, item]));
  const claims = draft.afirmaciones || [];
  if (!claims.length) return disabledBlock('Qué está respaldado', 'El borrador no tiene afirmaciones citadas.');
  return `<section class="section"><h3>Qué está respaldado</h3>
    <div class="claim-list">${claims.map(item => {
      const evidence = byEvidence.get(item.evidencia_id);
      const label = evidenceLabel(evidence);
      return `<article class="claim-row">
        <p>${esc(item.texto || 'Afirmación sin texto visible.')}</p>
        <span class="citation" title="ID técnico: ${esc(item.evidencia_id || 'sin cita')}">${esc(label)} · ${esc(humanEnum(item.relacion))}</span>
        <details><summary>ID técnico</summary><span class="mono">${esc(item.id)}${item.evidencia_id ? ` · ${esc(item.evidencia_id)}` : ''}</span></details>
      </article>`;
    }).join('')}</div>
  </section>`;
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
    <h3>Puntaje ${esc(Math.round(Number(priority.puntaje)))}/100</h3>
    <p class="muted">${esc(priority.reglas_version)} · ${esc(plural(grouping?.publicaciones, 'publicación', 'publicaciones'))} · ${esc(plural(grouping?.procedencias_identificadas, 'fuente independiente', 'fuentes independientes'))} · ${esc(plural(grouping?.publicaciones_origen_desconocido, 'origen desconocido', 'orígenes desconocidos'))}</p>
    <div class="score-list">${rows}</div>
    <p class="warning">El puntaje ordena atención; no estima verdad ni habilita publicación.</p>
  </section>`;
}

function draftBlock(draft) {
  if (!draft) return `<section class="editorial-card disabled-block" aria-disabled="true">
    <h3>Borrador</h3>
    <p><strong>Sin borrador todavía · se generará con el modelo local.</strong></p>
    <p>La edición y aprobación quedan deshabilitadas hasta que exista texto con afirmaciones citadas.</p>
  </section>`;
  return `<section class="editorial-card">
    <h3>Borrador v${esc(draft.version)}</h3>
    <p class="warning">${esc(humanEnum(draft.alcance_texto))}</p>
    <h4>${esc(draft.titulo)}</h4>
    <p class="reading">${esc(draft.brief)}</p>
    <details><summary>Guion y copy</summary><p>${esc(draft.guion)}</p><p>${esc(draft.copy)}</p></details>
    <details><summary>ID técnico</summary><p class="mono">${esc(draft.id)}</p></details>
  </section>`;
}

function reviewForm(draft) {
  const disabled = draft ? '' : 'disabled title="No hay borrador asociado" aria-describedby="disabled-help"';
  return `<section class="editorial-card">
    <h3>Revisión humana</h3>
    <form class="review-form">
      <label>Persona revisora<input name="persona_revisora" required minlength="2" maxlength="80"></label>
      <label>Estado<select name="estado">
        <option value="en_revision">✎ En revisión</option>
        <option value="requiere_evidencia">! Requiere evidencia</option>
        <option value="aprobado_como_borrador" ${disabled}>✔ Aprobado como borrador</option>
        <option value="descartado">✕ Descartado</option>
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
    setCutoffTime(detail.snapshot?.fecha_corte_utc);
    const caseData = detail.caso;
    const draft = detail.borradores[0];
    const evidence = evidenceState(caseData.estado_evidencia);
    detailEl.innerHTML = `<div class="panel radiografia-panel">
      <div class="panel-header">
        <h2>${esc(caseData.titulo)}</h2>
        <span class="technical-id" title="ID técnico">${esc(caseData.id)}</span>
        <div class="badges"><i class="${evidence.cls}">${evidence.icon} ${evidence.text}</i><i>${reviewState(caseData.estado_revision)}</i></div>
      </div>
      <section class="section"><h3>Qué se reporta</h3><p class="reading">${esc(caseData.titulo)}</p></section>
      <section class="section"><h3>Quién lo reporta</h3>${sourceRows(detail.evidencias, detail.agrupacion)}</section>
      ${supportedClaims(draft, detail.evidencias)}
      <section class="section"><h3>Falta verificar</h3><p>${esc(caseData.preguntas_pendientes || 'Sin pendientes registrados.')}</p></section>
      <section class="section"><h3>Acción recomendada</h3><p>${caseData.estado_evidencia === 'suficiente_para_borrador' ? 'Revisar el borrador y confirmar citas antes de aprobar.' : 'Completar evidencia independiente antes de publicar.'}</p></section>
      ${scoreBlock(detail.priorizacion, detail.agrupacion)}
    </div>
    <div class="panel mesa-panel">
      <div class="panel-header"><h2>Mesa editorial</h2><p class="muted">Borrador y revisión.</p></div>
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

searchForm.addEventListener('input', updateFilterCount);
searchForm.addEventListener('change', updateFilterCount);

document.querySelector('#refresh').addEventListener('click', () => {
  searchForm.reset();
  loadCases({});
});

themeButtons.forEach(button => button.addEventListener('click', () => setTheme(button.dataset.temaOpcion)));
tabButtons.forEach(button => button.addEventListener('click', () => setPanel(button.dataset.panel)));

setCutoffTime();
setTheme(readTheme());
setPanel('agenda');
updateFilterCount();
loadCases({});
