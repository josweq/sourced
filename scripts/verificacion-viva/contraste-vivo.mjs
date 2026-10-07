#!/usr/bin/env node
// Contraste medido sobre lo que de verdad quedó pintado, texto por texto.
//
//   CDP_PORT=9222 node contraste-vivo.mjs [--pagina <regex>] [--pulsables "button, a, [role=tab]"]
//
// Mide la pantalla que esté abierta, en tres estados: en reposo, con el ratón
// encima de todo lo pulsable, y presionado. Sale con 1 si algún texto visible
// queda por debajo de WCAG 2.1 (4,5:1, o 3:1 en texto grande).
//
// También se usa como biblioteca, dentro del recorrido propio del proyecto, para
// medir cada pantalla y cada tema:
//
//   import { auditarContraste } from './contraste-vivo.mjs'
//   const r = await auditarContraste(app, 'registro · tema oscuro')
//
// Por qué existe además de medir los pares declarados. Una lista de pares solo
// ve lo que alguien declaró. No ve un fondo heredado, una regla que gana por
// especificidad, ni el estado con el ratón encima. En MAM, una regla genérica
// `button:hover` le ganaba a la de la tarjeta y dejaba el texto del mismo color
// que el fondo. La lista de pares daba 150 de 150. Esta medición lo encontró.

import { fileURLToPath, pathToFileURL } from 'node:url'
import { realpathSync } from 'node:fs'
import { conectar } from './cdp.mjs'

// Corre DENTRO de la página: necesita getComputedStyle de verdad.
const AUDITOR = `(() => {
  const lum = (rgb) => {
    const c = rgb.map((v) => { const s = v / 255; return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4 })
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
  }
  const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05) }
  const parse = (s) => {
    const m = /rgba?\\(([^)]+)\\)/.exec(s || '')
    if (!m) return null
    const p = m[1].split(/[\\s,\\/]+/).filter(Boolean).map((v) => parseFloat(v))
    return { rgb: [p[0], p[1], p[2]], a: p.length > 3 ? p[3] : 1 }
  }
  const over = (fg, bg) => fg.rgb.map((v, i) => Math.round(v * fg.a + bg[i] * (1 - fg.a)))
  // Fondo efectivo: se sube por los ancestros componiendo transparencias hasta
  // dar con uno opaco. Medir contra el fondo propio del elemento, que casi siempre
  // es transparente, da contra blanco y aprueba cosas ilegibles sobre oscuro.
  const capas = (el) => {
    const pila = []
    for (let cur = el; cur; cur = cur.parentElement) {
      const b = parse(getComputedStyle(cur).backgroundColor)
      if (b && b.a > 0) { pila.push(b); if (b.a >= 0.999) break }
    }
    let base = [255, 255, 255]
    for (const b of pila.reverse()) base = over(b, base)
    return base
  }
  const visible = (el) => {
    const r = el.getBoundingClientRect()
    const s = getComputedStyle(el)
    return r.width > 2 && r.height > 2 && s.visibility !== 'hidden' && s.display !== 'none' && Number(s.opacity) > 0.05
  }
  const tieneTexto = (el) => [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim().length > 0)
  const camino = (el) => {
    const partes = []
    for (let cur = el, i = 0; cur && i < 3; i += 1, cur = cur.parentElement) {
      const clase = typeof cur.className === 'string' && cur.className.trim() ? '.' + cur.className.trim().split(/\\s+/).slice(0, 2).join('.') : ''
      partes.unshift(cur.tagName.toLowerCase() + (cur.id ? '#' + cur.id : '') + clase)
    }
    return partes.join(' > ')
  }
  // Un elemento a mitad de una animación es un fotograma de paso, no un estado.
  const enMovimiento = (el) => el.getAnimations().some((a) => a.playState === 'running')
  const out = []
  for (const el of document.querySelectorAll('body *')) {
    if (!tieneTexto(el) || !visible(el) || enMovimiento(el)) continue
    const s = getComputedStyle(el)
    const fg = parse(s.color)
    if (!fg || fg.a < 0.05) continue
    const bg = capas(el)
    const color = over(fg, bg)
    const r = ratio(color, bg)
    const px = parseFloat(s.fontSize)
    const grande = px >= 24 || (px >= 18.66 && parseInt(s.fontWeight, 10) >= 700)
    const min = grande ? 3 : 4.5
    out.push({ camino: camino(el), texto: el.textContent.trim().slice(0, 40), ratio: Math.round(r * 100) / 100, min,
      ok: r + 0.005 >= min, fg: 'rgb(' + color.join(',') + ')', bg: 'rgb(' + bg.join(',') + ')' })
  }
  return out
})()`

/** Mide la pantalla actual. Devuelve { etiqueta, medidos, fallos, malas }. */
export async function auditarContraste(app, etiqueta) {
  await app.quieto()
  const filas = await app.js(AUDITOR)
  const malas = filas.filter((f) => !f.ok)
  return { etiqueta, medidos: filas.length, fallos: malas.length, malas }
}

/**
 * Mide en reposo, con el ratón encima de lo pulsable, y presionado.
 * El segundo y el tercero son donde se escondía el defecto de MAM.
 */
export async function auditarConEstados(app, prefijo, pulsables = 'button, a, [role="button"], [role="tab"], summary') {
  const resultados = [await auditarContraste(app, `${prefijo} · en reposo`)]
  for (const estados of [['hover'], ['hover', 'active']]) {
    const soltar = await app.forzarEstado(pulsables, estados)
    try {
      resultados.push(await auditarContraste(app, `${prefijo} · ${estados.join(' + ')}`))
    } finally {
      await soltar()
    }
  }
  return resultados
}

export function imprimir(resultados) {
  let fallos = 0
  for (const r of resultados) {
    fallos += r.fallos
    console.log(`${r.fallos ? 'FALLA' : 'OK   '} ${r.etiqueta} · ${r.medidos - r.fallos}/${r.medidos} textos`)
    for (const m of r.malas.slice(0, 8)) {
      console.log(`      ${m.ratio}:1 (necesita ${m.min}) · ${m.fg} sobre ${m.bg} · ${m.camino} · "${m.texto}"`)
    }
    if (r.malas.length > 8) console.log(`      … y ${r.malas.length - 8} más`)
  }
  return fallos
}

// Se compara por ruta REAL: si la skill está instalada como enlace simbólico, argv[1] trae la ruta del
// enlace e import.meta.url la ruta real, y la comparación directa nunca coincide (el script no arranca).
if (process.argv[1] && esPrincipal(import.meta.url, process.argv[1])) {
  const opcion = (n, d) => { const i = process.argv.indexOf(n); return i >= 0 ? process.argv[i + 1] : d }
  const patron = opcion('--pagina')
  const app = await conectar(patron ? { pagina: new RegExp(patron, 'i') } : {})
  try {
    console.log(`Contraste vivo · ${app.pagina.url}\n`)
    const resultados = await auditarConEstados(app, 'pantalla actual', opcion('--pulsables'))
    const fallos = imprimir(resultados)
    console.log(fallos === 0 ? '\nCONTRASTE VIVO OK' : `\nCONTRASTE VIVO: ${fallos} textos por debajo del umbral`)
    process.exitCode = fallos === 0 ? 0 : 1
  } finally {
    app.cerrar()
  }
}

function esPrincipal(urlModulo, argv1) {
  const real = (p) => { try { return realpathSync(p) } catch { return p } }
  const a = real(fileURLToPath(urlModulo)), b = real(argv1)
  return process.platform === 'win32' ? a.toLowerCase() === b.toLowerCase() : a === b
}
