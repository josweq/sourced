#!/usr/bin/env node
// Capturas del dossier con la app viva (Sourced en http://127.0.0.1:8765 y un navegador con CDP).
//   CDP_PORT=9333 node scripts/verificacion-viva/capturas.mjs [--salida verificacion/capturas]
// Abre casos por su título y guarda PNG a 1366×860 (y la agenda a 390 px de ancho).
import { mkdirSync } from 'node:fs'
import { join } from 'node:path'
import { conectar } from './cdp.mjs'

const i = process.argv.indexOf('--salida')
const SALIDA = i >= 0 ? process.argv[i + 1] : 'verificacion/capturas'
mkdirSync(SALIDA, { recursive: true })

const app = await conectar({ pagina: /^https?:\/\/(localhost|127\.0\.0\.1):8765/ })
const abrirCaso = async (texto) => {
  await app.js(`(() => { const f = document.querySelector('#search-form, form.search-row'); const q = document.querySelector('#agenda-q, #search, input[type=search]'); return Boolean(f && q) })()`)
  await app.esperarCambio(
    `/Qué se reporta/.test(document.querySelector('#detail')?.textContent ?? '') && (document.querySelector('#detail h2')?.textContent ?? '').includes(${JSON.stringify(texto)})`,
    () => app.js(`(() => { const c = [...document.querySelectorAll('#cases .case')].find(e => e.textContent.includes(${JSON.stringify(texto)})); if (!c) throw new Error('No encontré el caso: ' + ${JSON.stringify(texto)}); c.scrollIntoView({ block: 'center' }); c.click() })()`),
    `el caso ${texto}`)
  await app.quieto()
}
const guardar = async (nombre) => { await app.quieto(); await app.dormir(400); console.log('captura', await app.captura(join(SALIDA, nombre))) }

await app.tamano(1366, 860, { movil: false })
await app.recargar()
await app.js(`localStorage.removeItem('lupa-tema'); document.documentElement.removeAttribute('data-tema')`)
await app.recargar()
await app.esperarCambio(`document.querySelectorAll('#cases .case').length > 0`, async () => {}, 'la agenda')

// 1. Vista general: caso de cruceros con radiografía y mesa (barra de criterios visible).
await abrirCaso('Carnival Miracle')
await app.js(`document.querySelector('.criteria-toolbar')?.scrollIntoView({ block: 'center' })`)
await guardar('sourced-escritorio.png')

// 2. Versión generada: reel / short de 30 s en tono cercano.
await app.esperarCambio(
  `/palabras ·/.test(document.querySelector('[data-draft-panel="adaptado"]')?.textContent ?? '')`,
  () => app.js(`(() => { const f = document.querySelector('.adapt-form'); f.formato.value = 'vertical'; f.duracion_s.value = '30'; f.tono.value = 'cercano'; f.requestSubmit() })()`),
  'la versión generada', { limite: 180000 })
await app.js(`document.querySelector('[data-draft-panel="adaptado"]')?.scrollIntoView({ block: 'start' })`)
await guardar('sourced-generar-version.png')

// 3. Caso con dos medios (donación de EE.UU.): repetición no es corroboración.
await abrirCaso('dona a Panamá equipos')
await guardar('sourced-dos-medios.png')

// 4. Pregunta con cifra oficial no actual y 5. abstención.
const preguntar = async (q, archivo) => {
  await app.esperarCambio(
    `(document.querySelector('#answer, .answer, [data-answer]')?.textContent ?? '').includes(${JSON.stringify(q.slice(0, 12))}) || document.querySelector('#answer, .answer, [data-answer]')?.dataset?.q === ${JSON.stringify(q)}`,
    () => app.js(`(() => { const i = document.querySelector('#ask'); i.value = ${JSON.stringify(q)}; i.closest('form').requestSubmit() })()`),
    'la respuesta', { limite: 60000 }).catch(() => {})
  await app.dormir(1500)
  await guardar(archivo)
}
await preguntar('¿Cuál es la inflación de Panamá hoy?', 'sourced-cifra-oficial.png')
await preguntar('precio del oro en Bolivia', 'sourced-abstencion.png')

// 6. Agenda en teléfono.
await app.js(`document.querySelector('dialog[open]')?.close()`)
await app.tamano(390, 844, { movil: true })
await app.recargar()
await app.esperarCambio(`document.querySelectorAll('#cases .case').length > 0`, async () => {}, 'la agenda móvil')
await guardar('sourced-movil.png')
await app.tamano(1366, 860, { movil: false })
app.cerrar()
