#!/usr/bin/env node
// Desbordamiento horizontal a ancho de teléfono, en TODAS las pestañas.
//
//   CDP_PORT=9333 node anchos-movil.mjs [--anchos 360,390] [--pestanas "Resumen,Movimientos"] [--pagina <regex>]
//
// Para cada ancho, pulsa cada pestaña por su texto y mide si la página es más
// ancha que la ventana. Sale con 1 si alguna desborda.
//
// Por qué 360 y en todas las pestañas. En Chen, la primera versión medía a 390 px
// y solo la pestaña que estuviera abierta. No vio que Resumen se iba a 387 px y
// Recurrentes a 406 justo en la franja de 360, que es el ancho de la mayoría de
// los Android. Un desbordamiento se esconde en la pestaña que no se miró.
//
// Sin --pestanas, mide solo la pantalla actual en cada ancho.

import { fileURLToPath, pathToFileURL } from 'node:url'
import { realpathSync } from 'node:fs'
import { conectar } from './cdp.mjs'

export async function medirAnchos(app, { anchos = [360, 390], pestanas = [] } = {}) {
  const resultados = []
  // Una página sin <meta name="viewport"> no es responsiva aunque el CSS lo sea:
  // un teléfono de verdad la dibuja a 980 px y la reduce. Se avisa aparte.
  const tieneViewport = await app.js(`/width\\s*=\\s*device-width/i.test(document.querySelector('meta[name="viewport"]')?.content ?? '')`)
  if (!tieneViewport) resultados.push({ ancho: 0, pestana: 'meta viewport', ok: false, aviso: true, pagina: 0, ventana: 0,
    peor: { que: 'falta <meta name="viewport" content="width=device-width">', derecha: 980 } })

  for (const ancho of anchos) {
    // movil: false A PROPÓSITO. Con movil: true, Chromium le da a una página sin
    // meta viewport un ancho de diseño de 980 px: la ventana mide 980, la página
    // 980, y "no desborda" nada. Así se aprobó una caja de 420 px en una ventana
    // de 360 al probar esta herramienta. Se mide el diseño al ancho CSS real.
    const restaurar = await app.tamano(ancho, 800, { movil: false })
    try {
      for (const pestana of pestanas.length ? pestanas : [null]) {
        if (pestana) {
          await app.pulsarTexto(new RegExp(`^${pestana.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}$`))
          await app.quieto()
        }
        const m = await app.js(`(() => {
          const ventana = ${ancho}
          const pagina = document.documentElement.scrollWidth
          // El culpable: el elemento visible que más sobresale por la derecha.
          let peor = null
          for (const el of document.querySelectorAll('body *')) {
            const r = el.getBoundingClientRect()
            if (r.width && r.right > ventana + 1 && (!peor || r.right > peor.derecha)) {
              peor = { derecha: Math.round(r.right), que: el.tagName.toLowerCase() + (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\\s+/)[0] : '') }
            }
          }
          return { ventana, pagina, peor }
        })()`)
        // Contra el ancho pedido, no contra innerWidth, que puede no coincidir.
        resultados.push({ ancho, pestana: pestana ?? 'pantalla actual', ...m, ok: m.pagina <= ancho })
      }
    } finally {
      await restaurar()
    }
  }
  return resultados
}

// Se compara por ruta REAL: si la skill está instalada como enlace simbólico, argv[1] trae la ruta del
// enlace e import.meta.url la ruta real, y la comparación directa nunca coincide (el script no arranca).
if (process.argv[1] && esPrincipal(import.meta.url, process.argv[1])) {
  const opcion = (n, d) => { const i = process.argv.indexOf(n); return i >= 0 ? process.argv[i + 1] : d }
  const anchos = opcion('--anchos', '360,390').split(',').map(Number)
  const pestanas = (opcion('--pestanas', '') ?? '').split(',').map((s) => s.trim()).filter(Boolean)
  const patron = opcion('--pagina')
  const app = await conectar(patron ? { pagina: new RegExp(patron, 'i') } : {})
  try {
    console.log(`Anchos de teléfono · ${app.pagina.url}\n`)
    const resultados = await medirAnchos(app, { anchos, pestanas })
    for (const r of resultados) {
      if (r.aviso) { console.log(`AVISO ${r.peor.que}: en un teléfono real se dibuja a 980 px y se reduce`); continue }
      console.log(`${r.ok ? 'OK   ' : 'FALLA'} ${String(r.ancho).padStart(4)} px · ${r.pestana} · la página mide ${r.pagina}` +
        (r.ok ? '' : ` · sobresale ${r.peor?.que ?? '?'} hasta ${r.peor?.derecha ?? '?'} px`))
    }
    const malos = resultados.filter((r) => !r.ok && !r.aviso).length
    console.log(malos === 0 ? '\nANCHOS OK · nada desborda' : `\nANCHOS: ${malos} desbordamientos`)
    process.exitCode = malos === 0 ? 0 : 1
  } finally {
    app.cerrar()
  }
}

function esPrincipal(urlModulo, argv1) {
  const real = (p) => { try { return realpathSync(p) } catch { return p } }
  const a = real(fileURLToPath(urlModulo)), b = real(argv1)
  return process.platform === 'win32' ? a.toLowerCase() === b.toLowerCase() : a === b
}
