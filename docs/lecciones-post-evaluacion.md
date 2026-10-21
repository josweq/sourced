# Lecciones después de la evaluación

**hackIAthon Panamá 2026 · reto TVN «De la señal a la decisión» · equipo Jajanken**

`main` es la versión entregada y evaluada. Esta rama no cambia esa entrega: reúne lo que el jurado señaló, lo que corregimos para aprenderlo y lo que haríamos distinto la próxima vez.

## La calificación

**64/100.** Comentario de la organización (21 de octubre de 2026), resumido:

- **Lo que estuvo bien:** repositorio sólido (128 pruebas, dependencias fijadas, manifest SHA-256 y nada de secretos). En el video se ve que el sistema se abstiene, que da las cifras con año y unidad y que separa importancia de respaldo.
- **Lo que más restó:** no había demo en línea. Varias capacidades, como la resistencia a la inyección o el funcionamiento sin internet, no se pudieron comprobar.
- **Además:** el brief reformulaba el titular, el guion no llegaba a 45 s y en Notion faltaban fechas en el plan e ID en cada ficha de caso.

Nuestra autoevaluación previa como jurado dio 77/100. Ninguno de estos puntos estaba en ella.

## Lección 1 · Lo que el jurado no puede ejecutar, no cuenta

Diseñamos Sourced para correr sin internet, y lo probamos: 0 de 52 intentos de salir a la red, 128 pruebas y una matriz T01–T10 completa. Pero esas pruebas vivían en el repositorio y en nuestra laptop. El jurado no instala, y lo que no puede ver funcionar vale como si no existiera.

**Qué haríamos distinto:**
- Publicar una demo sencilla en línea, aunque sea de solo lectura con resultados ya calculados (GitHub Pages sirve).
- En el video, mostrar **cada** prueba prometida, con su minuto: la inyección rechazada, la abstención, el Wi-Fi apagado en pantalla y la cifra con año.

## Lección 2 · Las salidas exigidas se cumplen al pie de la letra y se prueban con un script

Las bases pedían un brief de hasta 250 palabras con título propuesto, enfoque de interés público, 3 preguntas de investigación, fuentes y verificaciones pendientes, y un guion de 45–60 segundos. Nuestro principio de no rellenar nos llevó a entregar menos:
- **El brief** era la lista de titulares citados («TVN reporta en titular: …»).
- **El guion** duraba unos 20 s con un solo titular.

**Corrección** (`src/ia/redaccion.py`): no rellenar no significa quedarse corto. Se alarga con lo que sí dice la evidencia, nunca con hechos nuevos:
- **Brief:** aviso «Basado únicamente en titular/metadatos», título propuesto, enfoque, qué se reporta (citado), dato oficial, estado de evidencia, 3 preguntas, fuentes con fecha y verificaciones pendientes.
- **Guion por bloques:** `[PRESENTADOR]`, `[VO]` con medio y fecha (máximo 3 titulares), `[CONTEXTO]`, `[DATO]`, `[LO QUE FALTA]` y `[CIERRE]` con las preguntas.
- **Medido en los 275 casos del snapshot:**
  - con el respaldo determinista, 240 de 270 guiones quedan entre 45 y 60 s (mediana 46 s; mínimo 42, máximo 61);
  - con `llama3.2:3b`, el caso de cruceros dura 55 s;
  - el brief más largo tiene 173 palabras.
- **Pruebas nuevas en `tests/test_redaccion_guardian.py`:**
  - el brief trae todas las secciones;
  - un guion de un titular dura 45–60 s y no agrega cifras ajenas a la evidencia;
  - se leen como máximo 3 titulares.

## Lección 3 · Se califica la superficie oficial, no el repositorio

Los ID de caso ya estaban en el dossier del repositorio (`CASO-828dcf…`, `CASO-eac2d7…`), pero la página funcional de Notion no los mostraba. Esa página fue la que se calificó.

**Corrección:** `docs/notion/funcional.md` lleva ahora la fecha de cada tarea del plan y el ID de cada ficha de caso.

**Qué haríamos distinto:** revisar cada campo obligatorio de las bases directamente en la página que verá el jurado, uno por uno.

## Lección 4 · Un error recurrente en la consola no es ruido

Al probar las correcciones apareció un defecto que estaba en la versión entregada: las barras del puntaje desglosado no se veían. Tenía dos causas:
1. La política de seguridad de la app (`style-src 'self'`) bloqueaba el `style="--valor:…"` del HTML, y la consola lo avisaba en cada carga.
2. El componente llega entre 0 y 1 y se usaba como porcentaje: 0,55 se pintaba como 0,55 %.

**Corrección** (`src/interfaz/static/app.js`): el valor viaja en `data-valor`, se escala a porcentaje y se aplica por CSSOM, que la política sí permite. Verificado en la app real: anchos de 25, 55, 50, 60 y 100 % y 0 violaciones de la política.

**Qué haríamos distinto:** en la verificación en vivo, medir lo que se pinta y leer cada error de la consola, aunque se repita.

## Estado de esta rama

- `0171b9f`: brief, guion, interfaz y barras, con 3 pruebas nuevas. Quedan **131/131** pruebas en verde; también pasan `check_sin_red.py` y `check_contraste.py`.
- `docs/notion/funcional.md`: fechas e ID.
- Este documento.

Lo que no se hizo: la demo en línea queda como la tarea pendiente más importante si el proyecto continúa.

---
Equipo Jajanken: Josué Carrillo · Diego Laverde · Juan Andrés López
