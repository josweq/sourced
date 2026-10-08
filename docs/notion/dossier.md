# Jajanken Lupa — Dossier del reto TVN Media

> **Antes de contar una historia, mostramos qué la sostiene.** Prototipo del equipo Jajanken para el hackIAthon Panamá 4ª edición, reto «De la señal a la decisión». No es una herramienta oficial de TVN.

**Equipo:** Josué Carrillo · Diego Laverde · Juan Andrés «Juanchi» López
**Modalidad:** editorial (con consulta de entorno logístico, CU-05)
**Repositorio:** https://github.com/pixeltabletop/jajanken-lupa (rama de entrega: ver README)
**Demo:** local, sin internet ni GPU (instrucciones en el README)

---

## 1. Inicio del reto

### Problema
Una redacción revisa fuentes dispersas, elimina duplicados y prepara piezas con prisa. Que una noticia circule no significa que esté confirmada: varios medios pueden repetir una misma fuente.

### Usuario
Editor/a, periodista, productor/a digital, director/a de noticias y presentador/a.

### Qué hace Lupa
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

### Plan (tareas)
| # | Tarea | Responsable | Estado |
|---|---|---|---|
| 1 | Analizar bases del reto y repo de partida | Josué | Hecho |
| 2 | Blueprint de arquitectura y diseño | Josué | Hecho |
| 3 | Snapshot reproducible (5 RSS, Banco Mundial, USGS) | Josué + Codex | Hecho |
| 4 | Sistema visual (temas Redacción y Sala, accesibilidad) | Josué + Codex | Hecho |
| 5 | Capa de IA local (embeddings, agrupación, búsqueda) | Josué + Codex | Hecho |
| 6 | Redacción con guardián y mesa editorial | Josué + Codex | Hecho |
| 7 | Preguntas con abstención (CU-02, CU-04, CU-05) | Josué | Hecho |
| 8 | Benchmark de desarrollo y matriz T01–T10 | Josué | Hecho |
| 9 | Etiquetado humano de temas y pares (pre-etiquetado por Codex, revisado por persona) | Josué, Diego, Juanchi | En curso |
| 10 | Formatos de adaptación (TV, radio, vertical, web, alerta) | Josué + Codex | Hecho |
| 10b | Guías «qué significa» y guía rápida en la interfaz | Josué + Codex | Hecho |
| 11 | Prueba sin internet (T10) | Josué | Pendiente |
| 12 | Integración, pitch y entrega | Diego, Juanchi, Josué | Pendiente |

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

Snapshot `real-20261007b`. Puntaje P = 30R + 25I + 20U + 15N + 10E (componentes de 0 a 1). Persona revisora: se registra en Lupa al revisar (revisión humana con historial).

### Ficha 1 — Donación de equipos de EE.UU. a Panamá (un evento, dos medios)
| Campo | Valor |
|---|---|
| Caso | `CASO-828dcf139d9cf6f0510e` |
| Publicaciones | Crítica, 7 oct 2026 18:03 (UTC−5): «EE.UU. dona a Panamá equipos de emergencia valorados en $500 mil» · TVN, 7 oct 2026 18:41 (UTC−5): «EEUU dona a Panamá equipos por $500,000 para habilitar albergues…» |
| Puntaje | 43,5 (R 0,20 · I 0,30 · U 1,00 · N 0,50 · E 0,25) |
| Evidencia | **Insuficiente**: dos medios lo publican, pero ninguno declara su procedencia; repetición no es corroboración |
| Falta verificar | Comunicado de la Embajada o del Sinaproc; destino de los equipos |
| Qué demuestra | Agrupación semántica entre medios (T02) sin inflar la evidencia |

### Ficha 2 — Contratos de laptops del Meduca (seguimiento)
| Campo | Valor |
|---|---|
| Caso | `CASO-d7414efb7cc141eab72c` |
| Publicaciones | La Prensa, 17 ago 2026: «Meduca contrató $28.4 millones por 54,000 laptops…» · 18 ago 2026: «Meduca tramitó adenda… por $235 mil y 75 días más» |
| Puntaje | 25,5 (U 0,10: notas de agosto, no de hoy) |
| Evidencia | **Insuficiente** (un solo medio) |
| Pregunta en Lupa | «contrato de laptops del Meduca» → responde con 3 titulares citados |
| Qué demuestra | Las fechas originales mandan sobre la fecha de captura |

### Ficha 3 — Temporada de cruceros en el Canal (prioridad alta, evidencia insuficiente)
| Campo | Valor |
|---|---|
| Caso | `CASO-eac2d70e82de48de49cd` |
| Publicación | TVN, 7 oct 2026 16:59 (UTC−5): «Canal de Panamá: Carnival Miracle inaugura temporada de cruceros 2026-2027; se contemplan más de 220 tránsitos» |
| Puntaje | **65,5** (R 0,60 · I 0,70 · U 1,00 · N 0,50 · E 0,25), el más alto del snapshot |
| Evidencia | **Insuficiente**: un titular, sin fuente primaria |
| Borrador | Brief, guion y copy citados; el guardián **retiró** un copy publicitario del modelo («¡Reserva tu crucero ahora…!») |
| Qué demuestra | Prioridad alta ≠ permiso para publicar (T08); la caja «Falta verificar» manda |

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
| Puntaje | 25,5 (U 0,10, mínima) — puesto 101 de 275 |
| Evidencia | **Insuficiente** |
| Qué demuestra | Una nota vieja no se presenta como nueva (T03) |

Capturas: `verificacion/capturas/real-caso-mesa.png`, `real-pregunta.png`, `real-cifra.png`, `real-adaptacion.png`.

---

## 6. Pruebas y métricas

### Matriz T01–T10
Ver `evaluation/matriz-T01-T10.md` en el repositorio. Resumen: **8 cumplen, T05 parcial (no detecta contradicciones entre noticias de forma automática) y T10 pendiente** (falta la corrida con la red cortada).

### Benchmark de desarrollo (40 preguntas)
| Métrica | Resultado |
|---|---|
| Aciertos | 37/40 (92 %) |
| Abstención correcta | 7/7 (100 %) |
| Abstención indebida | 2/20 (10 %) |
| Adversariales | 6/6 |
| Cobertura de citas | 33/33 (100 %) |
| Latencia mediana / p95 | 58 / 103 ms |

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

## 8. Presentación al jurado (10 min)
1. **Problema y usuario** (1 min).
2. **Solución y datos** (1 min).
3. **Demo** (4 min): agenda → caso con dos medios → borrador citado con cronómetro → pregunta con abstención → cifra «no actual» → revisión.
4. **IA, baseline y métricas** (2 min).
5. **Valor** (1 min): hipótesis declarada, no medida.
6. **Riesgos y próximos pasos** (1 min).
