# Sourced — Dossier del reto TVN Media
*Nada sin fuente.*

> **Antes de contar una historia, mostramos qué la sostiene.** Prototipo del equipo Jajanken para el hackIAthon Panamá 4ª edición, reto «De la señal a la decisión». No es una herramienta oficial de TVN.

**Equipo:** Josué Carrillo · Diego Laverde · Juan Andrés «Juanchi» López
**Modalidad:** editorial (con consulta de entorno logístico, CU-05)
**Repositorio:** https://github.com/pixeltabletop/jajanken-lupa (rama de entrega: ver README)
**Demo:** local, sin internet ni GPU (instrucciones en el README)
**Notion:** la organización indicó avanzar sin depender de Notion (la cuenta Business del reto no funciona); este documento es la fuente completa y hay una copia en el espacio «hackIAthon 4taEd».

![Sourced con datos reales del 7 de octubre: agenda priorizada, radiografía del caso y mesa editorial](../../verificacion/capturas/sourced-escritorio.png)
*Agenda con puntaje y evidencia por separado (izquierda), radiografía del caso (centro) y mesa editorial con borrador citado y la barra «Generar versión» (derecha).*

---

## 1. Inicio del reto

### Problema
Una redacción revisa fuentes dispersas, elimina duplicados y prepara piezas con prisa. Que una noticia circule no significa que esté confirmada: varios medios pueden repetir una misma fuente.

### Usuario
Editor/a, periodista, productor/a digital, director/a de noticias y presentador/a.

### Qué hace Sourced
1. **Agenda priorizada** con el porqué de cada tema (puntaje desglosado) y su estado de evidencia, por separado.
2. **Radiografía** de cada tema: qué se reporta, quién lo reporta, qué está respaldado, qué falta verificar.
3. **Mesa editorial**: brief, guion cronometrado, copy y preguntas de investigación, con una cita por afirmación.
4. **Preguntas en español** con respuesta citada o abstención explícita.
5. **Adaptar la nota** a TV, radio 30 s, video vertical 60 s, web o alerta, sin añadir datos: mismas citas, otro orden y extensión.
6. **Revisión humana** con historial: nada se publica automáticamente.

### Alcance
Incluye CU-01 a CU-05 sobre un snapshot público reproducible. No incluye: rating o audiencia, detección de «noticias falsas», datos personales, producción audiovisual ni publicación automática.

### Criterios de éxito
Cobertura de citas 100 % · abstención correcta ≥ 80 % · ninguna cifra inventada · demo sin internet · latencia mediana ≤ 15 s.

---

## 2. Plan y decisiones

**Cómo trabajamos.** Sourced es obra del equipo Jajanken completo: Josué Carrillo, Diego Laverde y Juan Andrés López decidimos juntos el alcance, el diseño y la identidad, etiquetamos y revisamos los datos a mano, probamos la herramienta y preparamos la documentación y la presentación. Por practicidad, el código se integró y publicó desde un solo equipo y una sola cuenta de GitHub, por eso la mayoría de los commits aparecen con un mismo autor. Usamos asistentes de IA (Codex para construir partes del código y Claude para auditarlo y documentarlo), siempre bajo revisión del equipo.

### Plan (tareas)
| # | Tarea | Responsable | Estado |
|---|---|---|---|
| 1 | Analizar bases del reto y repo de partida | Equipo Jajanken | Hecho |
| 2 | Blueprint de arquitectura y diseño | Equipo Jajanken | Hecho |
| 3 | Snapshot reproducible (5 RSS, Banco Mundial, USGS) | Equipo Jajanken | Hecho |
| 4 | Sistema visual (temas Redacción y Sala, accesibilidad) | Equipo Jajanken | Hecho |
| 5 | Capa de IA local (embeddings, agrupación, búsqueda) | Equipo Jajanken | Hecho |
| 6 | Redacción con guardián y mesa editorial | Equipo Jajanken | Hecho |
| 7 | Preguntas con abstención (CU-02, CU-04, CU-05) | Equipo Jajanken | Hecho |
| 8 | Benchmark de desarrollo y matriz T01–T10 | Equipo Jajanken | Hecho |
| 9 | Etiquetado humano de temas y pares (pre-etiquetado por Codex, revisado por persona) | Equipo Jajanken | Hecho |
| 10 | Formatos de adaptación (TV, radio, vertical, web, alerta) | Equipo Jajanken | Hecho |
| 10b | Guías «qué significa» y guía rápida en la interfaz | Equipo Jajanken | Hecho |
| 11 | Prueba sin internet (T10) | Equipo Jajanken | Hecho |
| 12 | Integración, pitch y entrega | Equipo Jajanken | Hecho |

### Decisiones justificadas
| ID | Decisión | Por qué | Alternativa descartada |
|---|---|---|---|
| R2-002 | Embeddings locales para clasificar, agrupar y buscar; el modelo de lenguaje solo redacta; guardián determinista | IA sustantiva medible, funciona sin internet, cada afirmación queda citada | Todo con un modelo de lenguaje (puntaje no reproducible, se cae sin red) |
| R2-004 | Redacción con Ollama local (`llama3.2:3b`), sin API de pago | Costo cero por uso; un tercero lo instala sin claves | API en la nube (costo y dependencia de red) |
| R2-005 | `llama3.2:3b` elegido por banco de 5 modelos | El más fiel: no inventó cifras ni datos; los otros inventaron detalles, imágenes o citaron una fuente maliciosa | qwen3:4b (mejor prosa, inventó «maíz y frutas tropicales») |
| R2-006 | Azul propio afín al ecosistema de TVN, tema oscuro «Sala» | Que no desentone con el cliente sin copiar su marca | Paleta verde/lima original |
| — | GDELT fuera; RSS de 5 medios panameños | GDELT respondió HTTP 429 a todas las consultas; varios medios permiten distinguir repetición de corroboración | Esperar a GDELT |

---

## 3. Catálogo de datos

| Fuente | URL | Extracción | Cobertura | Campos | Condiciones | Transformaciones |
|---|---|---|---|---|---|---|
| TVN (RSS) | https://www.tvn-2.com/rss/ | 2026-10-07/08 (2 capturas) | ~1 día por captura | título, URL, fecha de publicación | Solo titular y metadatos; sin descripción ni imágenes | URL normalizada, ID estable SHA-256 |
| La Prensa (RSS) | https://www.prensa.com/arc/outboundfeeds/rss/ | 2026-10-08 | Notas de ago–oct 2026 | Igual | Igual | Igual |
| Crítica (RSS) | https://www.critica.com.pa/rss.xml | 2026-10-08 | Incluye una nota de abr 2025 (recirculada) | Igual | Igual | Igual |
| Panamá América (RSS) | https://www.panamaamerica.com.pa/rss.xml | 2026-10-08 | Notas de feb 2024 | Igual | Igual | Igual |
| En Segundos (RSS) | https://ensegundos.com.pa/feed/ | 2026-10-08 | oct 2026 | Igual | Igual | Igual |
| Banco Mundial API v2 | https://api.worldbank.org/v2/ | 2026-10-08 | PAN, CRI, COL, DOM, MEX, GTM · 2010–2024 · 6 indicadores | país, indicador, año, valor, unidad | CC BY 4.0 (verificar excepciones) | Cuadrícula de 540 combinaciones; nulos nunca como 0 |
| USGS sismos | https://earthquake.usgs.gov/fdsnws/event/1/ | 2026-10-08 | 2024, lat 5–12, lon −86 a −76, M ≥ 3 | id, magnitud, fecha, lugar, coordenadas, URL | Dominio público | Solo hechos sísmicos |

**Snapshot `real-20261007b`:** 284 titulares, 540 valores, 82 sismos. Hash SHA-256 por archivo en `data/snapshot-dev/real-20261007b/processed/manifest.json`.
> El documento del reto calcula 1.350 combinaciones del Banco Mundial; 6 países × 6 indicadores × 15 años dan 540. Usamos 540 y no se inventan filas.

---

## 4. Diseño de solución

**Flujo:** snapshot → validación con cuarentena → embeddings locales → tema y grupos → relación con indicadores → ranking explicable → ficha → borrador citado → guardián → revisión humana.

| Pieza | Tecnología | Versión / parámetros |
|---|---|---|
| Embeddings | `intfloat/multilingual-e5-small` (CPU) | dim 384; agrupación por enlace promedio, umbral 0,945 calibrado con datos reales |
| Búsqueda y abstención | Semántica + coincidencia de contenido | responde si similitud ≥ 0,88, o ≥ 0,84 con una palabra de contenido común; si no, se abstiene |
| Redacción | Ollama `llama3.2:3b` | temperatura 0,2; salida JSON forzada; costo 0 por uso; 60–90 s por borrador en CPU |
| Guardián | Reglas deterministas | retira afirmaciones sin cita, cifras y términos sin respaldo, imágenes o citas inventadas, tono publicitario e instrucciones de fuentes |
| Ranking | P = 30R + 25I + 20U + 15N + 10E | componentes visibles con su criterio; versión de reglas registrada |
| Interfaz | Servidor local de biblioteca estándar + HTML/CSS/JS | solo 127.0.0.1; fuentes locales; WCAG 2.2 AA medido |

**Reparto de responsabilidades:** el código decide qué afirmaciones existen, su cita, el puntaje, el estado de evidencia y la publicación (que no existe). El modelo solo redacta, y el guardián decide qué se acepta.

---

## 5. Casos y evidencias

Snapshot `real-20261007b`. Puntaje P = 30R + 25I + 20U + 15N + 10E (componentes de 0 a 1). Persona revisora: se registra en Sourced al revisar (revisión humana con historial).

### Ficha 1 — Donación de equipos de EE.UU. a Panamá (un evento, dos medios)
| Campo | Valor |
|---|---|
| Caso | `CASO-828dcf139d9cf6f0510e` |
| Publicaciones | Crítica, 7 oct 2026 18:03 (UTC−5): «EE.UU. dona a Panamá equipos de emergencia valorados en $500 mil» · TVN, 7 oct 2026 18:41 (UTC−5): «EEUU dona a Panamá equipos por $500,000 para habilitar albergues…» |
| Puntaje | 64,25 (R 0,60 · I 0,65 · U 1,00 · N 0,50 · E 0,25) · tema «servicios públicos» asignado por el clasificador entrenado · puesto 26 de 275 |
| Evidencia | **Insuficiente**: dos medios lo publican, pero ninguno declara su procedencia; repetición no es corroboración |
| Falta verificar | Comunicado de la Embajada o del Sinaproc; destino de los equipos |
| Qué demuestra | Agrupación semántica entre medios (T02) sin inflar la evidencia |

### Ficha 2 — Contratos de laptops del Meduca (seguimiento)
| Campo | Valor |
|---|---|
| Caso | `CASO-d7414efb7cc141eab72c` |
| Publicaciones | La Prensa, 17 ago 2026: «Meduca contrató $28.4 millones por 54,000 laptops…» · 18 ago 2026: «Meduca tramitó adenda… por $235 mil y 75 días más» |
| Puntaje | 46,25 (U 0,10: notas de agosto, no de hoy) · tema «regulación» · puesto 118 de 275 |
| Evidencia | **Insuficiente** (un solo medio) |
| Pregunta en Sourced | «contrato de laptops del Meduca» → responde con 3 titulares citados |
| Qué demuestra | Las fechas originales mandan sobre la fecha de captura |

### Ficha 3 — Temporada de cruceros en el Canal (prioridad media, evidencia insuficiente)
| Campo | Valor |
|---|---|
| Caso | `CASO-eac2d70e82de48de49cd` |
| Publicación | TVN, 7 oct 2026 16:59 (UTC−5): «Canal de Panamá: Carnival Miracle inaugura temporada de cruceros 2026-2027; se contemplan más de 220 tránsitos» |
| Puntaje | **61,75** (R 0,60 · I 0,55 · U 1,00 · N 0,50 · E 0,25) · tema «turismo» · puesto 46 de 275. El máximo del snapshot es 65,5, en rango **medio** (alto ≥ 70; con solo titulares, ningún caso real llega ahí porque E y N quedan bajos) |
| Evidencia | **Insuficiente**: un titular, sin fuente primaria |
| Borrador | Brief, guion y copy citados; el guardián **retiró** un copy publicitario del modelo («¡Reserva tu crucero ahora…!») |
| Qué demuestra | Prioridad ≠ permiso para publicar (T08); la caja «Falta verificar» manda |

### Ficha 4 — Inflación de Panamá (dato oficial, no actual)
| Campo | Valor |
|---|---|
| Pregunta | «¿Cuál es la inflación de Panamá hoy?» |
| Respuesta | «Panamá, 2024: 0,7 (% anual). Dato anual del Banco Mundial; no es una medición actual» + aviso de que para hoy hace falta la fuente primaria nacional |
| Cita | Banco Mundial · FP.CPI.TOTL.ZG · 2024 |
| Qué demuestra | Año y unidad siempre visibles (T04); con «2026» se abstiene (T06) |

### Ficha 5 — Nota recirculada del papa Francisco
| Campo | Valor |
|---|---|
| Caso | `CASO-c89d635822b3f8a2ffc9` |
| Publicación | Crítica: «EL MUNDO DESPIDE AL PAPA FRANCISCO #ENVIVO», fecha original **26 abr 2025**, servida en el RSS de hoy |
| Puntaje | 25,5 (U 0,10, mínima) — puesto 259 de 275 |
| Evidencia | **Insuficiente** |
| Qué demuestra | Una nota vieja no se presenta como nueva (T03) |

### Sourced en acción (capturas con los datos reales)

**Caso, radiografía y mesa editorial** — un titular de TVN, evidencia insuficiente, borrador citado y la barra «Generar versión» con criterios opcionales:
![Caso de cruceros con mesa editorial](../../verificacion/capturas/sourced-escritorio.png)

**Generar versión** — reel/short de 30 s en tono cercano: la versión no rellena; dice cuánto alcanza con la evidencia y qué faltaría para llegar al objetivo:
![Versión generada con aviso de alcance](../../verificacion/capturas/sourced-generar-version.png)

**Un hecho, dos medios** — Crítica y TVN en un solo caso; 0 fuentes independientes porque ninguno declara su origen:
![Caso con dos medios](../../verificacion/capturas/sourced-dos-medios.png)

**Cifra oficial, no actual** — país, año, unidad y fuente, con el aviso de que no es una medición de hoy:
![Cifra del Banco Mundial con aviso](../../verificacion/capturas/sourced-cifra-oficial.png)

**Abstención** — sin evidencia en el snapshot, no responde:
![Abstención explícita](../../verificacion/capturas/sourced-abstencion.png)

**En el teléfono:**
![Agenda en móvil](../../verificacion/capturas/sourced-movil.png)

---

## 6. Pruebas y métricas

### Matriz T01–T10
Ver `evaluation/matriz-T01-T10.md` en el repositorio. Resumen: **10 de 10 cumplen**. T05: un detector determinista compara cifras (dinero, porcentaje, conteo, magnitud) entre medios del mismo caso y, si chocan, muestra ambas y deja el caso «insuficiente» sin elegir una; en el snapshot real hay 0 contradicciones («$500 mil» y «$500,000» son la misma cifra) y se ejerce con un par sintético marcado SYN. T10 se corrió con el Wi-Fi cortado: 5/5 pasos, 0 de 52 intentos de la sonda alcanzaron la red.

### Benchmark de desarrollo (40 preguntas): IA frente a línea base sin IA
Mismas 40 preguntas, mismas reglas de cifras oficiales, abstención y protección; solo cambia cómo se buscan las noticias. Línea base: palabras clave (basta una palabra de contenido en común, como la búsqueda de la agenda).

| Métrica | Sourced (búsqueda semántica local) | Línea base (palabras clave) |
|---|---|---|
| Aciertos | **37/40 (92 %)** | 35/40 (88 %) |
| Abstención correcta (sin respuesta en el corpus) | **7/7 (100 %)** | 4/7 (57 %) |
| Abstención indebida (sí había respuesta) | 2/20 (10 %) | **1/20 (5 %)** |
| Adversariales | 6/6 | 6/6 |
| Cobertura de citas | 33/33 (100 %) | 47/47 (100 %) |
| Latencia mediana / p95 | 92 / 106 ms | 22 / 47 ms |

**Qué significa:** las palabras clave responden más, pero responden mal cuando no hay evidencia: a «precio del oro en Bolivia» cita «el precio del clientelismo» y a «resultado de las elecciones en Japón» cita un titular de béisbol porque comparte la palabra «resultado». En una redacción, una cita pertinente equivocada es peor que una abstención. Sourced paga ese control con una abstención indebida más (2 vs 1).

**Sesgo declarado:** las preguntas y los umbrales los preparó el equipo con el sistema a la vista (conjunto de desarrollo, no reservado); la diferencia es indicativa, no una medición independiente. Resultados: `evaluation/resultados/benchmark-20261008T154642Z.md` y `benchmark-20261008T154554Z-lexico.md`.

### Clasificación de tema y agrupación con etiquetas humanas
284 titulares y 40 pares revisados fila por fila por las tres personas del equipo (pre-etiquetado por Codex, revisado por persona; 81 temas corregidos). Validación cruzada de 5 pliegues:

| Método | Macro-F1 | Aciertos |
|---|---|---|
| **Clasificador entrenado con etiquetas humanas** (embeddings locales + regresión logística) | **0,449** | 179/283 |
| Reglas por palabras clave (sin IA) | 0,259 | 185/283 |
| Embeddings sin entrenar | 0,163 | 30/283 |

**Qué significa:** el modelo entrenado sube el macro-F1 de 0,26 a 0,45: acierta en temas que las reglas nunca ven (regulación 0,52 frente a 0,13; eventos naturales 0,33 frente a 0). Las reglas empatan en aciertos totales porque mandan casi todo a «sin clasificar», la clase más grande. Agrupación: en los 40 pares, el umbral en uso (0,945) da precisión 0,50 y cobertura 0,14, y bajarlo a 0,90 sube la cobertura a 0,77; pero revisando el snapshot completo con 0,90 aparecen fusiones absurdas (Amber Heard con una reforma de seguridad chilena, cuatro notas de fútbol en un caso). Preferimos no fusionar hechos distintos aunque queden tarjetas repetidas. Detalle y curva completa: `evaluation/resultados/etiquetas-humanas-20261008.md`.

### Una prueba fallida y su corrección
**Fallo:** con noticias reales, el borrador del modelo dijo «¡Reserva tu crucero ahora y prepárate para una aventura inolvidable!» y expandió «RSE» como «Resolución de Situaciones Económicas». **Causa:** el guardián validaba las afirmaciones, pero no la prosa libre. **Corrección:** cada oración del modelo pasa por el guardián; lo retirado sale con su motivo. Hay prueba automática con esos casos reales.

---

## 7. Riesgos y ética
| Riesgo | Control | Prueba |
|---|---|---|
| Inventar hechos, cifras o citas | Guardián; abstención si falta evidencia | T06, T09, benchmark |
| Inyección desde una fuente o una pregunta | Las fuentes son datos; las instrucciones se rechazan | T07, B35–B36 |
| Confundir repetición con corroboración | Procedencia solo por origen declarado; medios del evento visibles | T02 |
| Presentar un dato anual como actual | Año, unidad y aviso «no es una medición actual» | T04 |
| Derechos de autor | Solo titulares y metadatos; las capturas crudas no se versionan | Catálogo |
| Privacidad y reputación | Sin datos personales; acusaciones atribuidas a su medio | Benchmark B40 |
| Credenciales | Ninguna clave necesaria; `.env.example` sin secretos | Revisión del repo |

---

## 8. Presentación
La presentación del producto está en Notion, en la página del equipo («Presentación Pitch Day»), con el video de demostración.

---

## 9. Bitácora (cronología con evidencia)
Hora de Panamá (UTC−5). Cada línea enlaza a un commit del repositorio.

| Fecha y hora | Qué pasó | Commit |
|---|---|---|
| 7 oct 09:51 | Base del repo, guías del equipo y estructura compartida | `da0f210`, `9812e32` |
| 7 oct 14:44–15:22 | Modelo de datos trazable, importador CSV con cuarentena, interfaz local, agenda priorizada y búsqueda explicable (línea base léxica) | `22c93ec`, `6c6b8a6`, `98f5ccd`, `f4e5f74` |
| 7 oct 18:09 | Extractor de snapshot reproducible y blueprint de arquitectura | `c642468`, `3c027bd` |
| 7 oct 18:10 | Banco de 5 modelos de redacción local → se elige `llama3.2:3b` (R2-005) | `4da2000` |
| 7 oct 18:31–18:48 | Sistema visual «Redacción» y «Sala», puerta de contraste y recorrido vivo | `2037a4d`, `dcb87ba` |
| 7 oct 19:02 | Capa de IA local: embeddings, agrupación semántica y búsqueda híbrida | `14f0fab` |
| 7 oct 19:21 | GDELT responde 429 → RSS de 5 medios; **fallo**: el centroide unía 102 titulares → enlace promedio y umbral calibrado | `97b86a5` |
| 7 oct 19:28–20:06 | Redacción con guardián y mesa editorial; **fallo**: prosa publicitaria y sigla mal expandida → el guardián revisa cada oración y las preguntas | `5a38337`, `23c86f2`, `3f00bd5` |
| 7 oct 20:55 | Preguntas en español con cita o abstención (CU-02, CU-04, CU-05) | `f6d3f52` |
| 7 oct 21:46–21:49 | Benchmark de 40 preguntas, matriz T01–T10 y primer borrador de este dossier | `687af9e`, `fad697f`, `c512f19` |
| 7 oct 23:47–8 oct 00:23 | Formatos de adaptación, guías «qué significa», hojas de revisión humana y verificación viva en verde | `2276a27`, `700ddde`, `914451a`, `93c1199` |
| 8 oct 07:48 | Integración de la rama en `main` (PR #2) | `b50695f` |
| 8 oct 09:09 | T10 con el Wi-Fi cortado: 5/5 pasos, 0 salidas a la red; puerta estática sin red | `5780688` |
| 8 oct 10:20 | Auditoría tipo jurado → **fallo**: todas las noticias apuntaban a la fuente TVN en el catálogo → corregido | `41e03f0` |
| 8 oct 10:43 | **Fallo**: «turistas en septiembre de 2026» citaba cruceros por el «2026» → años, meses y palabras de tiempo ya no deciden la búsqueda | `e146b2a` |
| 8 oct 10:48 | IA frente a línea base sin IA en el benchmark | `0ae9c08` |
| 8 oct 11:09 | T05: cifras incompatibles entre medios (Codex construye, Claude audita y corrige falsos positivos); matriz 10/10 | `e6c4ec4` |
| 8 oct 11:20 | Generar versión: barra de criterios opcionales (formato, duración, palabras, tono, enfoque, público) que arma el prompt; tope sin relleno | `d8aaf7c` |
| 8 oct 11:45 | El producto pasa a llamarse **Sourced** («nada sin fuente») | `6a6a51f` |
| 8 oct 12:20 | Etiquetas humanas (primeras dos hojas): clasificador entrenado macro-F1 0,479 frente a 0,254 de reglas; **fallo**: el umbral heredado de 0,45 dejaba todo sin tema → calibrado a 0; **fallo**: «EE.UU.» partía oraciones → corregido; capturas y verificación viva rehechas | este commit |
| 8 oct 13:30 | Tercera hoja (Diego): 284 temas y 40 pares, macro-F1 0,449; **fallo**: una sola etiqueta de «logística y Canal» impedía entrenar → clases con menos de 5 ejemplos fuera; identidad Sourced (papel, tinta y resaltador); auditoría de seguridad (0 críticos/altos) con correcciones; instalación probada en un entorno limpio | `1508656`, `d44278a` |
