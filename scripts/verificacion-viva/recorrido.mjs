#!/usr/bin/env node
// PLANTILLA · recorrido vivo del proyecto
//
// Copiar a scripts/recorrido-vivo.mjs, junto con cdp.mjs y contraste-vivo.mjs
// (importar con ruta relativa: en Windows una ruta absoluta en un import tiene
// que ser file:///). Sustituir el cuerpo de `recorrido()` por el flujo del
// proyecto. Lo demás —dos corridas, esperas cronometradas, errores de consola,
// artefacto con encabezado— ya está.
//
//   npm run dev -- -- --remote-debugging-port=9222      (Electron)
//   node scripts/lanzar-navegador.mjs <url> --puerto 9333   (web)
//
//   CDP_PORT=9222 node scripts/recorrido-vivo.mjs --dos-veces --salida <carpeta verificacion>
//
// Sin --dos-veces hace una corrida, y el artefacto sale en amarillo como mucho:
// una verificación viva que pasó una vez todavía no ha probado que es repetible.

import { execSync } from 'node:child_process'
import { mkdirSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { conectar } from './cdp.mjs'
import { auditarConEstados } from './contraste-vivo.mjs'
import { medirAnchos } from './anchos-movil.mjs'

// ============================================================ CONFIGURACIÓN
const PROYECTO = 'jajanken-lupa'
const PAGINA = /^https?:\/\/(localhost|127\.0\.0\.1)[:/]|^file:/i
// ==================================================== FIN DE LA CONFIGURACIÓN

const opcion = (n, d) => { const i = process.argv.indexOf(n); return i >= 0 ? process.argv[i + 1] : d }
const DOS_VECES = process.argv.includes('--dos-veces')
const SALIDA = opcion('--salida', 'docs/verificacion')

let commit = 'desconocido'
try { commit = execSync('git rev-parse --short HEAD', { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim() } catch { /* sin git */ }

/**
 * EL RECORRIDO DEL PROYECTO. Sustituir este cuerpo.
 *
 * Recibe la aplicación conectada y dos funciones:
 *   ok(condicion, 'qué se comprueba', 'detalle')   registra una comprobación
 *   medir('qué se espera', promesaDeMs)            registra una espera cronometrada
 *
 * Reglas (references/repetible.md): recargar al empezar, datos únicos por corrida,
 * esperar a algo que CAMBIA, nunca a algo que existe.
 */
async function recorrido(app, { ok, medir, marca }) {
  await app.tamano(1366, 900, { movil: false })
  await app.recargar()
  await app.js(`localStorage.removeItem('lupa-tema'); document.documentElement.removeAttribute('data-tema')`)
  await app.recargar()
  const contraste = async (etiqueta) => {
    await app.quieto()
    for (const r of await auditarConEstados(app, etiqueta)) {
      ok(r.fallos === 0, `contraste · ${r.etiqueta}`, `${r.medidos - r.fallos}/${r.medidos} textos` +
        (r.fallos ? ` · peor ${r.malas[0].ratio}:1 en ${r.malas[0].camino}` : ''))
    }
  }
  const tema = () => app.js(`document.documentElement.dataset.tema || 'redaccion'`)
  ok(await tema() !== 'sala', 'arranca en tema Redacción', await tema())
  const n = await app.js(`document.querySelectorAll('#cases .case').length`)
  ok(n > 0, 'la agenda muestra casos', `${n}`)
  await contraste('Redacción · agenda')

  await medir('abrir el primer caso', app.esperarCambio(
    `/Qué se reporta/.test(document.querySelector('#detail')?.textContent ?? '')`,
    () => app.pulsar('#cases .case'), 'el detalle del caso'))
  ok(await app.js(`/Prioridad|Qué se reporta|Falta verificar/.test(document.querySelector('#detail').textContent)`),
    'el detalle muestra la radiografía')
  await contraste('Redacción · caso abierto')

  const antes = await app.js(`document.querySelectorAll('.review-entry').length`)
  await app.escribir('[name="persona_revisora"]', `Verificación ${marca}`)
  await app.js(`(() => { const s = document.querySelector('[name="estado"]'); s.value = 'en_revision'; s.dispatchEvent(new Event('change', { bubbles: true })) })()`)
  await app.escribir('[name="comentario"]', `Revisión automática ${marca}`)
  await medir('registrar la revisión', app.esperarCambio(
    `document.querySelectorAll('.review-entry').length`,
    () => app.js(`document.querySelector('.review-form, form[data-review], #detail form').requestSubmit()`),
    'la revisión nueva en el historial'))
  ok(await app.js(`document.querySelector('#detail').textContent.includes('Verificación ${marca}')`),
    'la revisión nueva aparece con su persona revisora', `antes ${antes}`)

  await medir('cambiar a tema Sala', app.esperarCambio(`document.documentElement.dataset.tema || ''`,
    () => app.pulsar('#tema-sala'), 'data-tema = sala'))
  ok(await tema() === 'sala', 'el conmutador activa Sala')
  await contraste('Sala · caso abierto')

  for (const t of ['sala', 'redaccion']) {
    if (await tema() !== t) await app.pulsar(t === 'sala' ? '#tema-sala' : '#tema-redaccion')
    for (const r of await medirAnchos(app, { anchos: [360, 390], pestanas: ['Agenda', 'Radiografía', 'Mesa'] })) {
      ok(r.ok ?? (r.desborde === 0 || r.desbordePx === 0), `ancho ${t} · ${r.etiqueta ?? r.ancho + ' px ' + (r.pestana ?? '')}`, JSON.stringify(r).slice(0, 160))
    }
  }
  await app.tamano(1366, 900, { movil: false })
}

// ------------------------------------------------------------------ corridas
async function corrida(n) {
  const app = await conectar({ pagina: PAGINA })
  const comprobaciones = []
  const esperas = []
  const marca = `${Date.now().toString().slice(-6)}${n}`
  const t0 = Date.now()
  const ok = (cond, que, detalle = '') => {
    comprobaciones.push({ ok: Boolean(cond), que, detalle })
    console.log(`  ${cond ? 'OK   ' : 'FALLA'} ${que}${detalle ? ` · ${detalle}` : ''}`)
  }
  const medir = async (que, promesa) => {
    const ms = await promesa
    esperas.push({ que, ms })
    if (ms < 50) console.log(`  AVISO la espera "${que}" midió ${ms} ms: ¿se cumplía antes de la acción?`)
    return ms
  }
  console.log(`\nCorrida ${n} · ${app.pagina.url}`)
  try {
    await recorrido(app, { ok, medir, marca })
  } catch (e) {
    ok(false, 'el recorrido termina sin excepción', e.message)
  } finally {
    const errores = app.errores()
    ok(errores.length === 0, 'sin errores de consola', errores.slice(0, 2).join(' | '))
    app.cerrar()
  }
  const fallos = comprobaciones.filter((c) => !c.ok).length
  return { n, comprobaciones: comprobaciones.length, fallos, errores: comprobaciones.at(-1).ok ? 0 : 1, esperas, detalle: comprobaciones, segundos: Math.round((Date.now() - t0) / 1000) }
}

const corridas = [await corrida(1)]
if (DOS_VECES) corridas.push(await corrida(2))

// ------------------------------------------------------------ estado y artefacto
const todasPasan = corridas.every((c) => c.fallos === 0)
const estado = !todasPasan ? 'rojo' : corridas.length < 2 ? 'amarillo' : 'verde'
const hoy = new Date().toISOString().slice(0, 10)

mkdirSync(SALIDA, { recursive: true })
writeFileSync(join(SALIDA, 'verificacion-viva.json'), JSON.stringify({ proyecto: PROYECTO, commit, fecha: hoy, estado, corridas }, null, 2))

const md = `---
skill: verificar-app-viva
estado: ${estado}
fecha: ${hoy}
commit: ${commit}
---

# Verificación viva · ${PROYECTO}

## Corridas

| Corrida | Comprobaciones | Fallos | Duración |
|---|---|---|---|
${corridas.map((c) => `| ${c.n} | ${c.comprobaciones} | ${c.fallos} | ${c.segundos} s |`).join('\n')}

## Esperas medidas

${corridas.flatMap((c) => c.esperas.map((e) => `- corrida ${c.n} · ${e.que}: ${e.ms} ms`)).join('\n') || '_El recorrido no registró esperas._'}

## Fallos

${corridas.flatMap((c) => c.detalle.filter((d) => !d.ok).map((d) => `- corrida ${c.n} · ${d.que}${d.detalle ? ` · ${d.detalle}` : ''}`)).join('\n') || '_Ninguno._'}

## Hecho cuando

- [${corridas[0]?.fallos === 0 ? 'x' : ' '}] Todas las comprobaciones pasan en la corrida 1
- [${corridas[1]?.fallos === 0 ? 'x' : ' '}] Y en la corrida 2, sin tocar nada entre medias
`
writeFileSync(join(SALIDA, 'verificacion-viva.md'), md)

console.log(`\nEstado: ${estado.toUpperCase()}${estado === 'amarillo' ? ' (una sola corrida: repite con --dos-veces)' : ''}`)
console.log(`Artefacto: ${join(SALIDA, 'verificacion-viva.md')}`)
process.exitCode = estado === 'verde' ? 0 : estado === 'amarillo' ? 2 : 1
