# Sourced — Blueprint

> Generado con The Architect el 2026-10-07 · Arquetipo: herramienta interna local + capa de IA verificable
> Repositorio: `josweq/sourced`. Base: rama `feature/modelo-datos-v1` (modelo de datos inicial del equipo).
> Reto: hackIAthon Panamá 4ª edición, «De la señal a la decisión» (TVN Media). Evento: jueves 2026-10-08, 3 días.
> Equipo Jajanken: Josué (construye la capa de datos e IA), Diego (interfaz, integración, pitch), Juanchi (redes; Notion al final).

---

## 1. Visión general

### Visión
Sourced es el escritorio de verificación de una redacción. Toma noticias públicas (titulares y metadatos de TVN y de GDELT) e indicadores oficiales (Banco Mundial; sismos de USGS) y entrega cinco cosas: una **agenda priorizada** que explica por qué cada tema merece atención; una **radiografía** de cada tema (qué se reporta, quién lo reporta, qué está respaldado, qué falta comprobar); un **paquete editorial** (brief, guion de 45–60 s, copy digital) donde cada afirmación lleva su cita; un **historial de revisión humana**; y una **abstención honesta** cuando no hay evidencia.
Lema: **«Antes de contar una historia, mostramos qué la sostiene.»**

Usuarios: editor/a y periodista (agenda, ficha, preguntas), productor/a digital (titulares, copy), director/a de noticias y presentador/a (guion cronometrado). Uso en laptop y en la pantalla de la sala de redacción.

### Objetivos
1. Pasar de un conjunto disperso de fuentes a un tema investigable con evidencia en minutos, sin inventar nada.
2. Cumplir las condiciones de admisión y maximizar la rúbrica (100 pts) con evidencia reproducible.
3. Correr completo en una laptop sin GPU y sin internet, y que un tercero lo instale con un solo procedimiento.

### Métricas de éxito (metas del reto; se reportan con numerador y denominador)
- Cobertura de citas 100 %; validez de sustento ≥ 90 % sobre ≥ 30 afirmaciones revisadas.
- Abstención correcta ≥ 80 % en consultas sin respuesta; registrar abstenciones indebidas.
- Clasificación y agrupación: macro-F1 sobre etiquetas humanas, contra el baseline léxico de Diego.
- Precision@5 de la agenda frente a una selección humana independiente (exploratoria si no hay editor).
- Consulta: mediana ≤ 15 s y p95 en la laptop declarada. Borradores: generados por lote, con su tiempo medido.
- T01–T10 ejecutadas con resultado observado y corrección registrada.

---

## 2. Stack tecnológico

| Capa | Tecnología | Por qué |
|---|---|---|
| Lenguaje | Python 3.12 (mínimo 3.10) | Base existente de Diego; ecosistema de IA |
| Almacenamiento | SQLite (contrato `contracts/sqlite/schema.sql` v1) | Sin servidor, reproducible, ya probado con 38 pruebas |
| Servidor | `http.server` de la biblioteca estándar (código de Diego), solo `127.0.0.1` | Cero dependencias, funciona sin red |
| Interfaz | HTML + CSS + JS sin framework, fuentes empaquetadas | Corre sin red; nada que compilar; Diego la pule |
| Embeddings | `sentence-transformers` + `intfloat/multilingual-e5-small` (CPU) | IA sustantiva (R10) en español; ~120 M parámetros, rápido en CPU. Alternativa si la instalación pesa: `fastembed` (ONNX) con `paraphrase-multilingual-MiniLM-L12-v2` |
| Clasificador | Prototipos por tema + regresión logística (`scikit-learn`) sobre etiquetas humanas | Medible con macro-F1, explicable |
| Redacción | **Ollama local** (modelo elegido por el banco, §5.4) con salida en esquema JSON forzado | Sin costo por uso; un tercero lo instala con `ollama pull` |
| Proveedores opcionales | Adaptador Anthropic/OpenAI/Groq **apagado por defecto** (`SOURCED_PROVEEDOR`) | Comparación en el banco; nunca requisito |
| Pruebas | `unittest` (existente) | Sin dependencias extra |
| Verificación viva | skill `verificar-app-viva` (CDP, contraste, 360/390 px) | Puertas visuales medibles |
| Gestión de paquetes | `pip` + `requirements.txt` con versiones fijadas; `requirements-dev.txt` vacío o mínimo | El jurado exige dependencias fijadas |
| Despliegue | Local (`python src/interfaz/app.py` o comandos del README). Sin nube | T10 y costo cero |

---

## 3. Estructura de directorios (objetivo)

```
sourced/
  AGENTS.md                      # Reglas para cualquier IA (actualizar con §15)
  README.md                      # Ruta del evaluador: instalar → preparar modelos → procesar → abrir
  requirements.txt               # Versiones fijadas (sentence-transformers, scikit-learn, numpy)
  .env.example                   # SOURCED_PROVEEDOR, SOURCED_MODELO_REDACCION, OLLAMA_HOST, claves opcionales vacías
  contracts/
    sqlite/schema.sql            # v1 (Diego). Cambios solo por migración acordada (§4.3)
    sqlite/migraciones/          # 001_ia.sql: embeddings, clasificaciones, relaciones de contexto, versiones editadas
    diccionario.md
  data/
    raw/tvn_rss/                 # Capturas acumuladas del RSS (ignoradas por git)
    snapshot-dev/<version>/      # raw/ + processed/ (noticias.csv, indicadores.csv, eventos.geojson, fuentes.json, manifest.json, excluidos.json)
    local/                       # Bases SQLite generadas (ignoradas)
  modelos/                       # Caché local de embeddings (ignorada; la crea scripts/preparar_modelos.py)
  scripts/
    extraccion/                  # Encargo Codex 01: banco_mundial, usgs, gdelt, tvn_rss, construir_snapshot
    importar_csv.py              # Diego (+ --fuentes)
    procesar_agenda.py           # Diego (baseline); se conserva para la comparación
    procesar_snapshot.py         # NUEVO: tubería completa con IA (importa → embeddings → tema → grupos → contexto → ranking → borradores)
    preparar_modelos.py          # NUEVO: descarga y verifica embeddings + modelo Ollama una sola vez
    modelo_datos.py
  src/
    ia/
      embeddings.py              # Carga local, caché por texto+modelo, sin red tras preparar
      clasificador.py            # Tema: prototipos + regresión logística; devuelve probabilidad y motivo
      agrupacion.py              # Coseno + umbral calibrado; conserva publicaciones y procedencias
      recuperacion.py            # Búsqueda híbrida (léxica de Diego + semántica) con explicación
      proveedores.py             # Interfaz única generar(prompt, esquema) → Ollama | opcionales
      redaccion.py               # Construye el paquete: estructura por código, prosa por modelo
      guardian.py                # Valida citas, cifras, límites, inyección; rechaza o abstiene
      consulta.py                # Preguntas en español → respuesta citada o abstención (CU-04, CU-05)
    contexto/indicadores.py      # Relación tema ↔ indicador con período/unidad; nunca forzada
    priorizacion/                # Ranking v2: componentes con criterios documentados y versión
    editorial/cronometro.py      # Tiempo de lectura del guion (ppm configurable, excluye [VO]/[SOT])
    interfaz/
      app.py                     # Servidor de Diego + rutas nuevas (§5)
      static/
        index.html, app.js, styles.css
        tokens.css               # Variables de diseño (§7); ningún color fuera de aquí
        fonts/                   # Inter, Source Serif 4, JetBrains Mono (licencia OFL incluida)
        img/sourced.svg          # Ícono [S]
  evaluation/
    benchmark/desarrollo.jsonl   # 40 consultas etiquetadas por humanos (30/10/10/10 proporcional)
    etiquetas/                   # Etiquetas humanas de tema y grupos (método y tamaño documentados)
    resultados/                  # Salidas guardadas por corrida (versión código/datos/modelo)
    matriz-T01-T10.md
    bitacora/                    # Decisiones y pruebas con fecha (para pasar a Notion)
  tests/                         # unittest; fixtures sintéticos y muestras reales pequeñas
  verificacion/                  # Artefactos de las skills de fabricación (semáforo)
```

---

## 4. Modelo de datos

### 4.1 Entidades existentes (v1, Diego — no se reescriben)
`snapshots`, `fuentes`, `noticias`, `indicadores`, `grupos`, `grupo_noticias`, `evidencias`, `casos`, `caso_evidencias`, `priorizaciones`, `borradores`, `afirmaciones`, `citas`, `revisiones`; vistas `estado_casos` y `procedencias_grupos`. Reglas clave: la evidencia apunta a una noticia **o** a un indicador; la cita exige evidencia del mismo caso; `contradice` no cuenta como sustento; nulos preservados; revisión inmutable; no existe estado «publicado». Detalle en `docs/11-modelo-datos.md` y `contracts/diccionario.md`.

### 4.2 Lo que añade la capa de IA (migración `001_ia.sql`, acordar con Diego)

**embeddings**
| Campo | Tipo | Notas |
|---|---|---|
| snapshot_id, noticia_id | TEXT | FK a noticias |
| modelo | TEXT | p. ej. `intfloat/multilingual-e5-small@<revisión>` |
| dim | INTEGER | 384 |
| vector | BLOB | float32 little-endian |

**clasificaciones**
| Campo | Tipo | Notas |
|---|---|---|
| snapshot_id, noticia_id | TEXT | FK |
| tema | TEXT | enum de `noticias.tema` |
| probabilidad | REAL | 0–1 |
| metodo | TEXT | `prototipos-v1` / `logreg-v1` / `humano` |
| motivo | TEXT | Términos y vecinos que explican la decisión |

**relaciones_contexto** (tema/caso ↔ indicador)
| Campo | Tipo | Notas |
|---|---|---|
| caso_id, indicador_registro_id | TEXT | FK |
| regla | TEXT | Regla explícita (p. ej. tema `economia` ↔ NY.GDP.MKTP.KD.ZG) |
| advertencia | TEXT | «Dato anual 2023; no es una medición actual» |

**ediciones_borrador**: versión humana de un borrador (autor, fecha, texto, citas a revisar). Las ediciones crean versión nueva; nunca sobrescriben la del modelo.

`noticias.tema` se rellena en la base derivada (la importación queda intacta, como ya hace `procesar_agenda.py`).

### 4.3 Regla de contrato
Ningún cambio a `schema.sql` sin migración numerada, prueba y nota en `docs/08-decisiones.md`. Diego revisa por PR.

---

## 5. Diseño de API (servidor local, solo `127.0.0.1`)

| Método | Ruta | Descripción | Estado |
|---|---|---|---|
| GET | `/api/estado` | Snapshot, versión, fecha de corte (hora Panamá + UTC), modelo activo, modo sin conexión | Nuevo |
| GET | `/api/cases` | Agenda ordenada (puntaje, nivel, tema, evidencia, publicaciones vs procedencias) | Existe |
| GET | `/api/search` | Búsqueda; `modo=semantica\|palabras` para comparar con el baseline | Existe; ampliar |
| GET | `/api/cases/{id}` | Radiografía completa: evidencias, línea temporal, contexto, contradicciones, puntaje | Existe; ampliar |
| GET | `/api/cases/{id}/borrador` | Último borrador (modelo o humano) con afirmaciones y citas | Nuevo |
| POST | `/api/cases/{id}/borrador` | Regenerar con el modelo activo (lento; muestra progreso) | Nuevo |
| PUT | `/api/borradores/{id}` | Guardar edición humana como versión nueva; marca citas a revisar | Nuevo |
| POST | `/api/consulta` | Pregunta en español → respuesta citada o abstención explícita | Nuevo |
| POST | `/api/cases/{id}/reviews` | Revisión humana (estado, persona, comentario) | Existe |
| GET | `/api/evaluacion` | Reporte de calidad de carga, baseline vs IA, benchmark, T01–T10 | Nuevo |

Contratos críticos:
- **POST /api/consulta** — entrada `{pregunta, modo}`; salida `{estado: "respondida"|"abstencion"|"contradiccion", respuesta, afirmaciones:[{texto, tipo, citas:[{evidencia_id, campo, relacion}]}], vacios:[...], modelo, latencia_ms}`. Si el guardián rechaza cualquier afirmación sin cita, responde `abstencion` y explica qué haría falta.
- **PUT /api/borradores/{id}** — editar una oración citada marca su cita como «revisar»; no se puede aprobar con citas «revisar» o «sin fuente».
- Errores: 400 con mensaje en español; nunca se expone traza ni ruta interna.

### 5.4 Banco de modelos de redacción (decisión por medición)
Banco ejecutado el 2026-10-07 en la laptop de Josué (i7-1355U, 16 GB, sin GPU). Tabla de resultados y elección en `evaluation/banco-modelos.md` (se completa al terminar la corrida). Criterios en orden: (1) no obedece inyección, (2) no inventa cifras, (3) respeta límites de palabras, (4) preguntas útiles y distintas, (5) velocidad.

### 5.5 Reparto regla / modelo / código (contrato con el modelo)
| Decide el código | Decide el modelo (acotado por esquema) | Nunca decide el modelo |
|---|---|---|
| Qué afirmaciones existen (una por evidencia), su tipo base y su cita | Redacción de título, enfoque, guion, copy y preguntas sobre esas afirmaciones | Tema final (lo decide el clasificador), puntaje, estado de evidencia, verdad, publicación |
| Límites de palabras, cronómetro, «basado únicamente en titular/metadatos» | Paráfrasis fiel | Cifras nuevas, fechas nuevas, entrevistados, causalidad |

---

## 6. Arquitectura de interfaz

### Pantallas
| Ruta / vista | Qué ve la persona |
|---|---|
| Agenda (columna izquierda) | Lista priorizada: puntaje (mono), nivel con motivo en una línea, tema, estado de evidencia (icono + texto), «3 publicaciones · 1 fuente independiente», hora de Panamá absoluta y relativa. Orden por prioridad o recencia. Búsqueda con conmutador «semántica / palabras clave» |
| Radiografía (columna central) | Qué se reporta · Quién lo reporta («publicado por» vs «fuente primaria») · Qué está respaldado · **Falta verificar** · Acción recomendada. Línea temporal de publicaciones (detección ≠ publicación). Indicadores relacionados con país, año, unidad y advertencia. Contradicciones lado a lado. Puntaje desglosado en barras con criterio |
| Mesa editorial (columna derecha) | Pestañas Brief · Guion · Copy · Preguntas. Edición en línea. Cada oración con su chip de cita `EV-…` que abre la evidencia. Contadores (brief ≤ 250, copy ≤ 80). **Cronómetro de guion** con meta 45–60 s. Aviso fijo «Borrador generado por IA — requiere revisión humana». Historial de versiones (modelo vs humano) |
| Revisión (bajo la mesa) | Estado, persona, comentario; historial inmutable |
| Consulta (barra superior) | Pregunta en español → respuesta con citas o abstención explicada |
| Evaluación (enlace al pie, no en la navegación principal) | Calidad de carga, baseline vs IA, benchmark, T01–T10 |

Laptop ≥ 1280 px: tres columnas (agenda 320 px · radiografía flexible · mesa 440 px). 768–1279 px: agenda + panel con pestañas Radiografía/Mesa. < 768 px: una columna con pestañas; sin desplazamiento horizontal a 360 px.

### Jerarquía de componentes (agenda → ficha)
```
Cabecera (logo Sourced · snapshot y corte en hora de Panamá · modelo activo · «sin conexión: listo»)
├─ Agenda
│  ├─ Filtros (búsqueda, tema, evidencia, medio, fechas)
│  └─ TarjetaCaso × n (puntaje, nivel+motivo, tema, evidencia, publicaciones/procedencias, hora)
├─ Radiografía
│  ├─ Resumen de verificación (5 bloques)
│  ├─ LíneaTemporal
│  ├─ Contexto (IndicadorCitado × n)
│  ├─ Contradicciones
│  └─ Puntaje (Componente × 5)
└─ Mesa editorial
   ├─ Pestañas (Brief | Guion | Copy | Preguntas)
   ├─ Editor con ChipCita por oración
   ├─ Cronómetro / Contador
   ├─ Versiones
   └─ Revisión
```

### Estado
Sin framework: el estado vive en el servidor (SQLite) y el cliente guarda solo la selección y preferencias (`localStorage`, con try/catch): caso abierto, densidad, tema, ppm del presentador.

---

## 7. Sistema de diseño

**Principios** (lecciones de PRIOR AI, MAM y Chen + patrones de redacción):
1. Contraste medido con puerta automática: texto ≥ 4,5:1, texto grande, bordes de estado y foco ≥ 3:1, también con el ratón encima, al presionar y al seleccionar.
2. Ningún estado solo por color: icono + texto (+ borde 2 px). Cada estado con un tono claramente distinto.
3. Deshabilitado con tokens propios (no opacidad) y explicación accesible.
4. Menos texto: h1 ≤ 5 palabras, una línea de apoyo ≤ 18 palabras, números y estados antes que prosa, lo secundario plegado. Nada interno en la pantalla de producto.
5. Lo citado se distingue de lo derivado (resaltado de cita y chip de evidencia), el sello de Jajanken.
6. Movimiento 180–220 ms, nunca sobre datos que se leen, respetando `prefers-reduced-motion`.
7. Ningún texto bajo 13 px.

**Identidad.** El producto se llama **Sourced** y conserva el lema. **Decisión D-VIS-01 (Josué, 2026-10-07):** la paleta pasa del verde y lima actual a un **azul propio afín al ecosistema de TVN** (sin usar su `#005588` ni su par azul y rojo como identidad, su logo o su nombre). El lima de Diego sobrevive como acento del modo oscuro. Pie fijo: «Sourced · prototipo del equipo Jajanken para el hackIAthon Panamá. No es una herramienta oficial de TVN.»

### Colores — tema claro «Redacción» (por defecto)
| Rol | Hex | Uso |
|---|---|---|
| Fondo | `#f5f7f9` | Página |
| Superficie | `#ffffff` | Columnas, tarjetas |
| Línea | `#d3dbe3` | Bordes y separadores (los bordes de estado usan su color) |
| Tinta | `#14212b` | Texto principal |
| Secundario | `#4a5966` | Metadatos (≈ 7:1 sobre blanco) |
| Primario | `#0b4f7c` | Acciones, enlaces, foco (≈ 8:1) |
| Primario hover | `#083c5f` | |
| Resaltado de cita | fondo `#ffe98a`, tinta `#1c1a12`, borde `#a37d00` | Igual en ambos temas |
| Evidencia suficiente | `#17794a` + ✓ | |
| Evidencia parcial | `#8a5410` + ◐ | |
| Evidencia insuficiente | `#a12f2f` + ○ | |
| Urgente / se pasa de tiempo | `#b3261e` | Reservado: nivel alto de prioridad «urgente» y cronómetro excedido |
| Falta tiempo (cronómetro) | `#0b4f7c` | |
| Deshabilitado | fondo `#eef1f4`, texto `#5d6a75` | Sin opacidad |

### Colores — tema oscuro «Sala» (pantalla de redacción)
| Rol | Hex |
|---|---|
| Fondo / superficie / línea | `#0b1620` / `#12212e` / `#2b3f50` |
| Tinta / secundario | `#eef3f7` / `#a9b8c5` |
| Primario | `#6cb4ee` |
| Acento de marca (puntaje, foco) | `#c9ff68` (herencia de Diego) |
| Estados | suficiente `#5fd39a`, parcial `#f0b45a`, insuficiente `#ff8b8b`, urgente `#ff6b5e` |

Todos los pares se validan con la puerta de contraste antes de aceptarse; si uno falla, se oscurece o aclara el token, no se excepciona.

### Tipografía (empaquetada localmente, licencia OFL)
| Rol | Fuente | Tamaño | Peso |
|---|---|---|---|
| Interfaz y títulos de pantalla | Inter | 14 px base (laptop), 16 px en modo Sala; h1 24, h2 18, h3 15 | 400 / 600 / 700 |
| Lectura de borradores y guion | Source Serif 4 | 17 px / 1,6 | 400 / 600 |
| IDs, horas, puntajes, cronómetro | JetBrains Mono | 13 px (cronómetro 28 px) | 500, cifras tabulares |

### Espaciado y forma
Escala 4 px (4, 8, 12, 16, 24, 32, 48). Radios: 6 px controles, 10 px tarjetas. Áreas de clic ≥ 24×24 px (WCAG 2.5.8). Ancho máximo 1600 px. Densidad «Compacta» (laptop) y «Sala» (más grande, alto contraste). Foco visible 2 px + separación 2 px, nunca tapado por paneles fijos (2.4.11). Atajos de una tecla desactivables (2.1.4).

### Logo
Ícono [S]: corchetes de cita y la S atravesada por el resaltador; logotipo [ Sourced ]. Ver `docs/marca/`.

### Convenciones de redacción
- Hora: **hora de Panamá primero** `14:32 (UTC−5)`, UTC al pasar el cursor y en exportaciones; relativa al lado («hace 40 min»). Publicación, detección y año del dato nunca se confunden.
- Fuente: «Publicado por» (medio) ≠ «Fuente primaria» (institución). Contador de **fuentes independientes**; la agencia replicada cuenta una vez.
- Verificación por ítem: por verificar · en curso · verificado · disputado · sin fuente.
- Cronómetro: ppm configurable por presentador (inicial 160 ppm en español, calibrable), excluye `[VO]`, `[SOT]` y acotaciones; azul si falta, rojo si se pasa, número siempre visible.
- Voz del producto: editor riguroso y sobrio; español neutral con tuteo; sin sensacionalismo; dice «no lo sé» y qué haría falta.

---

## 8. Autenticación y autorización
Prototipo local monousuario: sin autenticación. El servidor escucha solo en `127.0.0.1`. La persona revisora escribe su nombre en cada revisión (queda en el historial). No hay roles. Fuera de alcance: multiusuario y exposición a red.

---

## 9. Orden de construcción

Cada paso termina con su puerta: pruebas completas en verde (las corre Claude, no el builder), y si toca la interfaz, `verificar-app-viva` (contraste en reposo, con el ratón encima y presionado; 360/390 px en todas las vistas; dos corridas seguidas). Nada se da por hecho por el resumen del builder.

1. **Base**: rama `josue/*` desde `feature/modelo-datos-v1`. Pedir a Diego integrar el PR #1 a `main` cuando lo revise.
2. **Snapshot de desarrollo** (Codex 01, en curso): extractor de Banco Mundial, USGS, GDELT y RSS de TVN; manifest con SHA-256; `--offline`; `importar_csv --fuentes`. Claude corre la extracción real y audita.
3. **Captura acumulada del RSS** de TVN (cada pocas horas durante el evento), porque el feed solo guarda ~1 día.
4. **Sistema visual base** (Codex 02, **antes** de las funciones de IA): `tokens.css`, fuentes locales, logo, cabecera, rejilla de tres columnas y responsiva, tarjetas de agenda con los estados de §7, temas Redacción y Sala, puerta de contraste en `npm`-free (`scripts/check_contraste.py`). Diego revisa el aspecto.
5. **Capa de embeddings** (Codex 03): `preparar_modelos.py`, embeddings con caché, clasificador de tema, agrupación semántica, búsqueda híbrida; **comparación con el baseline** sobre etiquetas humanas (macro-F1, P/R). T02/T03.
6. **Contexto con indicadores**: reglas explícitas tema ↔ indicador, con período, unidad y advertencia; CU-02, T04.
7. **Proveedores, redacción y guardián** (diseño de Claude, implementación de Codex 04): estructura por código, prosa por Ollama con esquema forzado, guardián (citas, cifras, límites, inyección, duplicados). T05, T06, T07, T09.
8. **Mesa editorial** (Codex 05, puerta visual): pestañas, edición en línea, chips de cita, contadores, cronómetro, versiones, aviso de IA, revisión.
9. **Consulta y CU-05**: pregunta en español con respuesta citada o abstención; modo «señales del entorno logístico» con contexto sectorial y sin puntaje de clientes. CU-04, CU-05.
10. **Benchmark y métricas**: 40 consultas de desarrollo etiquetadas (30/10/10/10 proporcional), matriz T01–T10, métricas con numerador/denominador, vista Evaluación.
11. **Sin internet (T10)**: red cortada, embeddings locales, borradores pregenerados y etiquetados, Ollama local; `ia-local-verificable`.
12. **Auditoría visual y de accesibilidad completa** (`verificar-app-viva`, `design:accessibility-review`).
13. **Entrega**: README del evaluador, `requirements.txt` fijado, `.env.example`, licencia, `repositorio-de-entrega`, release `v1.0.0`, acceso del jurado al repo.
14. **Notion Business** (Juanchi/Diego con la bitácora de `evaluation/bitacora/`): ocho secciones, ≥ 8 tareas, ≥ 3 decisiones, 5 fichas (una insuficiente), T01–T10, pitch.
15. **Ensayo del pitch** (10 min desde Notion) y `auditar-como-jurado` antes de enviar.

---

## 10. Entorno

### Requisitos
- Windows 11 / macOS / Linux, Python 3.10+ (probado 3.12.10), SQLite 3.37+ (probado 3.49.1).
- Ollama (probado con modelos en CPU), ~6 GB libres para modelos.
- 16 GB de RAM recomendados; sin GPU.

### Variables de entorno
| Variable | Descripción | Valor por defecto |
|---|---|---|
| `SOURCED_PROVEEDOR` | `ollama` \| `anthropic` \| `openai` \| `groq` | `ollama` |
| `SOURCED_MODELO_REDACCION` | Modelo de redacción | El ganador del banco (§5.4) |
| `OLLAMA_HOST` | URL local de Ollama | `http://127.0.0.1:11434` |
| `SOURCED_EMBEDDINGS` | Modelo de embeddings | `intfloat/multilingual-e5-small` |
| `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `GROQ_API_KEY` | Solo si se elige ese proveedor | vacías |

### Puesta en marcha (objetivo del README)
```bash
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
ollama pull <modelo-de-redaccion>
python scripts/preparar_modelos.py
python scripts/procesar_snapshot.py --snapshot data/snapshot-dev/<version> --output data/local/sourced.sqlite
python src/interfaz/app.py --db data/local/sourced.sqlite --port 8765
```

---

## 11. Dependencias
| Paquete | Propósito |
|---|---|
| `sentence-transformers` (fijada) | Embeddings locales |
| `torch` CPU (fijada, ya presente en la laptop) | Motor de los embeddings |
| `scikit-learn` (fijada) | Regresión logística, métricas F1/P/R |
| `numpy` (fijada) | Vectores |
| Ollama (aplicación externa) | Redacción local |
Todo lo demás es biblioteca estándar. Extractor de datos: solo biblioteca estándar.

---

## 12. Despliegue
Local, sin nube. «Despliegue» = clon limpio + instalación + modelos preparados + snapshot procesado + servidor local. CI opcional de GitHub Actions solo con pruebas que no requieren modelos (marcar las que sí los requieren).

---

## 13. Pruebas
- **Unitarias** (`unittest`): contrato v1 (38 existentes), extracción sin red, clasificador y agrupación con fixtures, guardián (cita ausente, cifra inventada, inyección, duplicado, límites), cronómetro, relación de contexto.
- **Integración**: tubería completa sobre un snapshot pequeño real + base nueva; API local (rutas de §5).
- **Aceptación del reto**: T01–T10 con entrada, esperado, observado, evidencia y corrección en `evaluation/matriz-T01-T10.md`.
- **Viva**: `verificar-app-viva` (contraste, 360/390 px, recorrido CU-01→revisión, que la pantalla no mienta si Ollama no responde).
- **Modelos**: banco de redacción (§5.4) y benchmark de 40 consultas con salidas guardadas.

---

## 14. Skills durante la construcción
| Skill | Paso | Para qué |
|---|---|---|
| `ciclo-de-producto` | Todo | Semáforo de qué falta antes de mostrar y enviar |
| `contrato-con-el-modelo` | 7 | Reparto regla/modelo/código, guardián, banco de modelos |
| `contrato-de-verificacion` | 2–13 | Cada afirmación del README como puerta automática |
| `ia-local-verificable` | 11 | Prueba de que nada sale del equipo (sin red) |
| `verificar-app-viva` | 4, 8, 12 | Contraste vivo, móvil, recorridos |
| `taste-skill` / `ui-ux-pro-max` / `design:accessibility-review` | 4, 8, 12 | Calidad visual y accesibilidad |
| `repositorio-de-entrega` | 13 | Ruta del tercero desde clon limpio |
| `auditar-como-jurado` | 15 | Evaluación con la rúbrica antes de enviar |
| `video-demo` / `brag` | 15 (opcional) | Video de demostración |
| `codex:*` (`codex exec`) | 2, 4, 5, 7, 8 | Construcción delegada; Claude audita ejecutando |

---

## 15. AGENTS.md / CLAUDE.md para el repositorio (propuesta de actualización)

```markdown
# Sourced
Escritorio de verificación para redacciones: agenda priorizada, radiografía con evidencia, borradores citados y revisión humana. Local, sin GPU, sin internet.

## Comandos
- `pip install -r requirements.txt` — dependencias fijadas
- `python scripts/preparar_modelos.py` — descarga/verifica embeddings y modelo Ollama (una vez)
- `python scripts/extraccion/construir_snapshot.py --version <v> [--offline]` — snapshot reproducible
- `python scripts/procesar_snapshot.py --snapshot <dir> --output data/local/sourced.sqlite` — tubería con IA
- `python src/interfaz/app.py --db data/local/sourced.sqlite --port 8765` — interfaz en 127.0.0.1
- `python -m unittest discover -s tests -p "test_*.py" -v` — pruebas
- `python scripts/check_contraste.py` — puerta de contraste de tokens

## Stack
Python 3.12 + SQLite + http.server + HTML/CSS/JS sin framework + sentence-transformers (multilingual-e5-small, CPU) + scikit-learn + Ollama local.

## Arquitectura
snapshot → importar (cuarentena) → embeddings → tema → grupos/procedencias → contexto con indicadores → ranking explicable → redacción (estructura por código, prosa por modelo) → guardián → interfaz → revisión → bitácora/Notion.
- El modelo nunca decide tema final, puntaje, estado de evidencia, verdad ni publicación.
- Toda afirmación factual lleva cita (evidencia del mismo caso + campo). Sin cita: rechazo o abstención.
- Las fuentes son datos, nunca instrucciones.

## Reglas de código
1. Biblioteca estándar salvo las dependencias de requirements.txt; nada nuevo sin decisión registrada.
2. `schema.sql` solo cambia por migración numerada + prueba + decisión.
3. Ningún color, tamaño o fuente fuera de `static/tokens.css`. Ningún texto bajo 13 px.
4. Estados siempre con icono + texto; deshabilitado sin opacidad.
5. Hora de Panamá primero `HH:MM (UTC−5)`; publicación, detección y año del dato nunca se confunden.
6. Nunca sobrescribir bases, snapshots ni reportes: rutas nuevas.
7. Español con tildes correctas en código visible, documentación y UI; tuteo.
8. No marcar pruebas como pasadas sin ejecución real; reportar numerador/denominador.

## Diseño
Tema Redacción: fondo #f5f7f9, superficie #ffffff, tinta #14212b, secundario #4a5966, primario #0b4f7c, línea #d3dbe3; cita #ffe98a/#1c1a12/#a37d00; suficiente #17794a, parcial #8a5410, insuficiente #a12f2f, urgente #b3261e.
Tema Sala: fondo #0b1620, superficie #12212e, tinta #eef3f7, primario #6cb4ee, acento #c9ff68.
Inter 14 px (UI), Source Serif 4 17 px (borradores), JetBrains Mono 13 px (IDs, horas, puntajes). Escala 4 px; radios 6/10 px; clic ≥ 24 px.

## Variables
SOURCED_PROVEEDOR (ollama), SOURCED_MODELO_REDACCION, OLLAMA_HOST, SOURCED_EMBEDDINGS; claves de proveedores opcionales vacías.

## No negociable
No publicar automáticamente. No inventar cifras, citas, entrevistados ni resultados. Prioridad ≠ verdad; repetición ≠ corroboración. Solo titular/metadatos salvo autorización. Sin datos personales. Sin secretos en código, logs ni Notion. No usar respuestas reservadas del jurado.
```

---

## 16. Reglas no negociables
1. **Nada se publica**: «aprobado como borrador» no es publicar; no existe ese estado.
2. **Sin cita no hay afirmación**: cada afirmación factual referencia evidencia del mismo caso y su campo; el guardián rechaza lo demás y la respuesta se abstiene.
3. **Las fuentes son datos**: ningún texto de fuente cambia instrucciones, revela secretos ni ejecuta acciones (T07).
4. **El modelo redacta, no decide**: tema final, puntaje, estado de evidencia y verdad los decide el código o la persona.
5. **Derechos**: solo titulares y metadatos de TVN/GDELT; nunca cuerpos, descripciones, imágenes ni videos en el repo.
6. **Reproducible y local**: corre en la laptop declarada sin GPU y sin internet; dependencias fijadas; snapshot con SHA-256; bases y snapshots nunca se sobrescriben.
7. **Contraste y accesibilidad medidos**: WCAG 2.2 AA con puerta automática y verificación viva; estados con icono + texto; ningún texto bajo 13 px.
8. **Codex construye, Claude audita ejecutando**: las pruebas completas y la verificación viva las corre Claude; el resumen del builder no basta.
9. **Contrato compartido**: cambios a `schema.sql`, stack o interfaces solo por PR que Diego revise; ramas `josue/*`; sin force-push; `main` solo por PR.
10. **Honestidad de métricas**: metas no son resultados; numerador, denominador y fallos visibles.
