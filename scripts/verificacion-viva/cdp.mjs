// Cliente mínimo del protocolo de depuración de Chromium. Sin dependencias.
//
// Sirve para verificar una aplicación EN EJECUCIÓN: una app Electron abierta con
// `--remote-debugging-port`, o cualquier página en Chrome o Edge lanzados con ese
// mismo puerto. Se engancha a lo que ya está corriendo; no arranca nada.
//
//   import { conectar } from './cdp.mjs'
//   const app = await conectar({ puerto: 9222, pagina: /localhost|MiApp/ })
//   await app.recargar()
//   await app.pulsarTexto('Entrar')
//   const ms = await app.esperarCambio(`document.querySelectorAll('.fila').length`,
//     () => app.pulsarTexto('Guardar'), 'la fila nueva')
//
// Salió de MAM (ISD Summit 2026), donde 1.516 líneas de verificación contra la
// aplicación real repetían estas mismas funciones en cinco scripts. Cada una
// lleva el defecto que la hizo necesaria.
//
// Node 22 o superior: usa el WebSocket global.

import { writeFileSync } from 'node:fs'

const dormir = (ms) => new Promise((r) => setTimeout(r, ms))

/**
 * Se engancha a la primera página que coincida.
 *
 * `puerto` admite la variable CDP_PORT. No es un capricho: en una laptop Lenovo
 * el widget de Vantage ocupa el 9222, la verificación no encuentra la ventana y
 * falla entera con un error que parece de la aplicación.
 */
export async function conectar({
  puerto = Number(process.env.CDP_PORT ?? 9222),
  pagina = /^https?:\/\/(localhost|127\.0\.0\.1)[:/]|^file:/i,
  intentos = 40
} = {}) {
  let objetivo = null
  for (let i = 0; i < intentos && !objetivo; i += 1) {
    try {
      const lista = await (await fetch(`http://127.0.0.1:${puerto}/json/list`)).json()
      objetivo = lista.find((t) => t.type === 'page' &&
        (typeof pagina === 'function' ? pagina(t) : pagina.test(`${t.url} ${t.title}`)))
    } catch { /* todavía no escucha */ }
    if (!objetivo) await dormir(1000)
  }
  if (!objetivo) {
    throw new Error(`No encontré ninguna página en el puerto ${puerto}. ` +
      '¿Está la aplicación abierta con --remote-debugging-port? ¿Otro programa usa ese puerto? (CDP_PORT lo cambia)')
  }

  const ws = new WebSocket(objetivo.webSocketDebuggerUrl)
  await new Promise((res, rej) => { ws.onopen = res; ws.onerror = () => rej(new Error('no se pudo abrir el WebSocket de depuración')) })

  let id = 0
  const pendientes = new Map()
  const oyentes = new Map()
  const errores = []

  ws.onmessage = (e) => {
    const m = JSON.parse(e.data)
    if (m.id && pendientes.has(m.id)) {
      const { res, rej } = pendientes.get(m.id)
      pendientes.delete(m.id)
      if (m.error) rej(new Error(`${m.error.message} (${m.error.code})`))
      else res(m.result)
      return
    }
    if (m.method === 'Runtime.consoleAPICalled' && m.params.type === 'error') {
      errores.push(`console.error: ${m.params.args.map((a) => a.value ?? a.description ?? '').join(' ').slice(0, 200)}`)
    }
    if (m.method === 'Runtime.exceptionThrown') {
      errores.push(`excepción: ${(m.params.exceptionDetails.exception?.description ?? m.params.exceptionDetails.text).slice(0, 200)}`)
    }
    for (const f of oyentes.get(m.method) ?? []) f(m.params)
  }

  const envia = (method, params = {}) => new Promise((res, rej) => {
    const n = ++id
    pendientes.set(n, { res, rej })
    ws.send(JSON.stringify({ id: n, method, params }))
  })
  const alOir = (metodo, f) => {
    if (!oyentes.has(metodo)) oyentes.set(metodo, [])
    oyentes.get(metodo).push(f)
  }

  await envia('Runtime.enable')
  await envia('Page.enable')

  /** Evalúa en la página y devuelve el valor. Lanza si la página lanza. */
  async function js(expresion) {
    const r = await envia('Runtime.evaluate', { expression: expresion, awaitPromise: true, returnByValue: true })
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.exception?.description ?? r.exceptionDetails.text)
    return r.result.value
  }

  /**
   * Espera a que una expresión sea verdadera. Devuelve los milisegundos.
   *
   * Cuidado con usarla para saber que algo TERMINÓ: si la condición ya se cumplía
   * antes de la acción, sale en 0 ms y la verificación sigue sobre un resultado
   * que no existe. En MAM, "existe el bloque de respuesta" era verdad antes de
   * preguntar, y la espera midió 0,0 s donde de verdad tardaba 14,2. Para eso
   * está `esperarCambio`.
   */
  async function esperar(expresion, queEs, { limite = 45000, cada = 250 } = {}) {
    const t0 = Date.now()
    for (;;) {
      if (await js(expresion).catch(() => false)) return Date.now() - t0
      if (Date.now() - t0 > limite) throw new Error(`Tiempo agotado esperando: ${queEs}`)
      await dormir(cada)
    }
  }

  /**
   * Toma una firma, dispara la acción, y espera a que la firma CAMBIE.
   *
   * La firma es cualquier expresión que la acción deba alterar: cuántas filas
   * hay, el texto de la respuesta, el estado deshabilitado de un botón. Es la
   * forma fiable de esperar a que algo termine, porque no puede cumplirse antes
   * de que ocurra nada.
   */
  async function esperarCambio(firma, disparar, queEs, { limite = 90000, cada = 250 } = {}) {
    const antes = JSON.stringify(await js(firma))
    await disparar()
    const t0 = Date.now()
    for (;;) {
      const ahora = JSON.stringify(await js(firma).catch(() => antes))
      if (ahora !== antes) return Date.now() - t0
      if (Date.now() - t0 > limite) throw new Error(`Tiempo agotado: ${queEs} no cambió (sigue en ${antes.slice(0, 80)})`)
      await dormir(cada)
    }
  }

  /**
   * Espera a que no quede ninguna animación corriendo.
   *
   * Medir a mitad de una transición da falsos positivos: en MAM, el resaltado de
   * evidencia arranca transparente y a los 20 ms mide 1,07:1 de contraste;
   * asentado mide 14,33:1. Un `sleep` fijo no sirve porque cada pantalla tiene
   * sus tiempos. El tope evita colgarse con una animación infinita.
   */
  async function quieto(tope = 900) {
    return js(`(async () => {
      const corriendo = document.getAnimations().filter((a) => a.playState === 'running')
      await Promise.race([Promise.all(corriendo.map((a) => a.finished.catch(() => undefined))), new Promise((r) => setTimeout(r, ${tope}))])
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))
      return document.getAnimations().filter((a) => a.playState === 'running').length
    })()`)
  }

  /**
   * Trae el elemento a la vista y devuelve su centro en coordenadas de ventana.
   *
   * Las coordenadas del protocolo son de la parte VISIBLE, no del documento. En
   * MAM, un botón a 904 px en una ventana de 779 de alto recibía el clic en el
   * vacío. Sin error: la verificación se quedaba esperando algo que nadie pidió.
   */
  async function aLaVista(selector) {
    const desplazo = await js(`(() => {
      const e = document.querySelector(${JSON.stringify(selector)})
      if (!e) return null
      const r = e.getBoundingClientRect()
      if (r.width === 0 || r.height === 0) return null
      const fuera = r.top < 0 || r.bottom > innerHeight || r.left < 0 || r.right > innerWidth
      if (fuera) e.scrollIntoView({ block: 'center', inline: 'center' })
      return fuera
    })()`)
    if (desplazo === null) return null
    if (desplazo) await dormir(350)
    return js(`(() => {
      const e = document.querySelector(${JSON.stringify(selector)})
      if (!e) return null
      const r = e.getBoundingClientRect()
      return { x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2) }
    })()`)
  }

  /** Clic real con el ratón: mueve, presiona, suelta. */
  async function pulsar(selector) {
    const c = await aLaVista(selector)
    if (!c) throw new Error(`No encontré para pulsar: ${selector}`)
    await envia('Input.dispatchMouseEvent', { type: 'mouseMoved', x: c.x, y: c.y })
    await envia('Input.dispatchMouseEvent', { type: 'mousePressed', x: c.x, y: c.y, button: 'left', clickCount: 1 })
    await envia('Input.dispatchMouseEvent', { type: 'mouseReleased', x: c.x, y: c.y, button: 'left', clickCount: 1 })
  }

  /**
   * Pulsa el control cuyo TEXTO coincide, no el primero que comparta clase.
   *
   * En MAM dos `button.primary` convivían en el mismo panel. Buscar por clase
   * pulsaba el equivocado, el guardado nunca ocurría, y el siguiente paso
   * disparaba un diálogo del sistema.
   */
  async function pulsarTexto(texto, candidatos = 'button, [role="button"], [role="tab"], a') {
    const patron = texto instanceof RegExp ? texto.source : texto.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const flags = texto instanceof RegExp ? texto.flags : ''
    const marca = `cdp-${Date.now()}`
    const hay = await js(`(() => {
      const re = new RegExp(${JSON.stringify(patron)}, ${JSON.stringify(flags)})
      const e = [...document.querySelectorAll(${JSON.stringify(candidatos)})].find((x) => re.test(x.textContent.trim()) && x.getClientRects().length)
      if (!e) return 'no-existe'
      if (e.disabled || e.getAttribute('aria-disabled') === 'true') return 'deshabilitado'
      e.setAttribute('data-cdp', ${JSON.stringify(marca)})
      return 'ok'
    })()`)
    if (hay !== 'ok') throw new Error(`No pude pulsar "${texto}": ${hay}`)
    try { await pulsar(`[data-cdp="${marca}"]`) } finally {
      await js(`document.querySelector('[data-cdp="${marca}"]')?.removeAttribute('data-cdp')`)
    }
  }

  /**
   * Escribe en un campo de forma que el framework se entere.
   *
   * Asignar `el.value = x` no dispara los eventos que React escucha: el campo
   * muestra el texto y el estado de la aplicación sigue vacío. Hay que usar el
   * setter nativo del prototipo y emitir el evento.
   */
  async function escribir(selector, valor) {
    const ok = await js(`(() => {
      const el = document.querySelector(${JSON.stringify(selector)})
      if (!el) return false
      const proto = el.tagName === 'TEXTAREA' ? HTMLTextAreaElement : el.tagName === 'SELECT' ? HTMLSelectElement : HTMLInputElement
      Object.getOwnPropertyDescriptor(proto.prototype, 'value').set.call(el, ${JSON.stringify(valor)})
      el.dispatchEvent(new Event(el.tagName === 'SELECT' ? 'change' : 'input', { bubbles: true }))
      return true
    })()`)
    if (!ok) throw new Error(`No encontré el campo: ${selector}`)
  }

  /**
   * Fuerza :hover, :active o :focus sobre todos los elementos del selector.
   * Devuelve una función que los suelta.
   *
   * `:hover` no es una media query: no se emula con `setEmulatedMedia`. Hay que
   * pedírselo al motor de estilos nodo por nodo. En MAM, el peor defecto de
   * contraste solo existía con el ratón encima, y ninguna revisión en reposo lo
   * veía.
   */
  async function forzarEstado(selector, estados) {
    await envia('DOM.enable')
    await envia('CSS.enable')
    const { root } = await envia('DOM.getDocument', { depth: -1 })
    const { nodeIds } = await envia('DOM.querySelectorAll', { nodeId: root.nodeId, selector })
    for (const nodeId of nodeIds) await envia('CSS.forcePseudoState', { nodeId, forcedPseudoClasses: estados })
    return async () => {
      for (const nodeId of nodeIds) await envia('CSS.forcePseudoState', { nodeId, forcedPseudoClasses: [] }).catch(() => undefined)
    }
  }

  /** Cambia el tamaño de la ventana emulada. `movil` activa el táctil y la escala de teléfono. */
  async function tamano(ancho, alto = 800, { movil = ancho < 768 } = {}) {
    await envia('Emulation.setDeviceMetricsOverride', { width: ancho, height: alto, deviceScaleFactor: 1, mobile: movil })
    await dormir(250)
    return async () => { await envia('Emulation.clearDeviceMetricsOverride') }
  }

  /** Recarga y espera a que el documento termine de cargar. */
  async function recargar() {
    const cargada = new Promise((r) => alOir('Page.loadEventFired', r))
    await envia('Page.reload', { ignoreCache: true })
    await Promise.race([cargada, dormir(30000)])
  }

  /** Captura la parte visible a un PNG. */
  async function captura(ruta) {
    const { data } = await envia('Page.captureScreenshot', { format: 'png' })
    writeFileSync(ruta, Buffer.from(data, 'base64'))
    return ruta
  }

  return {
    pagina: { url: objetivo.url, titulo: objetivo.title },
    envia, alOir, js, esperar, esperarCambio, quieto, aLaVista, pulsar, pulsarTexto,
    escribir, forzarEstado, tamano, recargar, captura,
    /** Errores de consola y excepciones desde que se conectó. */
    errores: () => [...errores],
    cerrar: () => ws.close(),
    dormir
  }
}
