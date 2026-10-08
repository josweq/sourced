# Documentación técnica

**Sourced** corre completo en una laptop: sin GPU, sin claves y sin internet durante el uso. Repositorio público: https://github.com/josweq/sourced (rama `main`, licencia MIT).

---

## 1. Arquitectura

**Flujo:** snapshot → validación con cuarentena → embeddings locales → tema y grupos → relación con indicadores → ranking explicable → ficha → borrador citado → guardián → revisión humana.

| Pieza | Tecnología | Versión / parámetros |
|---|---|---|
| Embeddings | `intfloat/multilingual-e5-small` en CPU (sentence-transformers) | 384 dimensiones; caché en SQLite |
| Clasificación de tema | Regresión logística sobre embeddings, entrenada con etiquetas humanas | 6 temas + «sin clasificar»; clases con < 5 ejemplos fuera del entrenamiento |
| Agrupación por evento | Enlace promedio sobre similitud coseno | umbral 0,945; ventana de 7 días |
| Búsqueda y abstención | Semántica + coincidencia de contenido | responde si similitud ≥ 0,88, o ≥ 0,84 con una palabra de contenido común; años, meses y palabras de tiempo no cuentan |
| Redacción | Ollama local `llama3.2:3b` | temperatura 0,2; salida JSON forzada; 30–90 s por borrador en CPU |
| Guardián | Reglas deterministas en Python | retira oraciones sin cita, cifras, términos, negaciones o multiplicadores sin respaldo, tono publicitario, menciones inventadas e instrucciones de fuentes |
| Contradicciones | Extractor determinista de cifras (dinero, porcentaje, conteo, magnitud) | compara solo medios distintos del mismo caso; tolerancia 5 % |
| Ranking | P = 30R + 25I + 20U + 15N + 10E | componentes de 0 a 1 visibles con su criterio; versión de reglas registrada |
| Persistencia | SQLite con esquema versionado (`contracts/sqlite/schema.sql`) | revisiones de solo inserción; la base original de importación queda intacta |
| Interfaz | Servidor de biblioteca estándar de Python + HTML/CSS/JS sin dependencias | solo 127.0.0.1; CSP `default-src 'self'`; fuentes locales; WCAG 2.2 AA medido |

**Reparto de responsabilidades:** el código decide qué afirmaciones existen, su cita, el puntaje, el estado de evidencia y la publicación (que no existe). El modelo de lenguaje solo redacta, y el guardián decide qué se acepta.

---

## 2. Instalación y ejecución
Requisitos: Git, Python 3.10+ y [Ollama](https://ollama.com/download). Un comando por línea (PowerShell 5.1/7, cmd o bash).

```
git clone https://github.com/josweq/sourced.git
cd sourced
python -m venv .venv
.venv\Scripts\activate        (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
ollama pull llama3.2:3b
python scripts/preparar_modelos.py
python scripts/preparar_demo.py --snapshot data/snapshot-dev/real-20261007b --borradores 3
```
El último paso termina con «Siguiente paso (cópialo tal cual)»: `python src/interfaz/app.py --db "data/local/demo-<marca>.sqlite"`. Luego abre `http://127.0.0.1:8765`.

Comprobaciones: `python -m unittest discover -s tests -p "test_*.py"` (125 pruebas), `python scripts/check_sin_red.py` y `python scripts/check_contraste.py`.

**Probado en un entorno limpio** (clon nuevo, entorno de Python nuevo, caché de modelos vacía): los 6 pasos en ~8 minutos; pip ~5 min, modelo de embeddings ~1,5 min, preparación de la demo ~1,5 min con un borrador.

---

## 3. Datos

| Fuente | Extracción | Cobertura | Campos | Condiciones |
|---|---|---|---|---|
| TVN (RSS) | 7–8 oct 2026 | ~1 día por captura | título, URL, fecha | Solo titular y metadatos |
| La Prensa (RSS) | 8 oct 2026 | ago–oct 2026 | igual | igual |
| Crítica (RSS) | 8 oct 2026 | incluye una nota de abr 2025 | igual | igual |
| Panamá América (RSS) | 8 oct 2026 | notas de feb 2024 | igual | igual |
| En Segundos (RSS) | 8 oct 2026 | oct 2026 | igual | igual |
| Banco Mundial API v2 | 8 oct 2026 | PAN, CRI, COL, DOM, MEX, GTM · 2010–2024 · 6 indicadores | país, indicador, año, valor, unidad | CC BY 4.0 |
| USGS sismos | 8 oct 2026 | 2024, región de Panamá, M ≥ 3 | id, magnitud, fecha, lugar, coordenadas | Dominio público |

**Snapshot `real-20261007b`:** 284 titulares, 540 valores oficiales, 82 sismos, con huella SHA-256 por archivo en `manifest.json`. Los nulos nunca se convierten en 0; las filas inválidas van a cuarentena con su causa. GDELT quedó fuera: respondió HTTP 429 a todas las consultas.

---

## 4. Inteligencia artificial y cómo se mide

### Búsqueda semántica frente a una línea base sin IA (40 preguntas)
| Métrica | Sourced | Palabras clave (sin IA) |
|---|---|---|
| Aciertos | **37/40** | 35/40 |
| Abstención correcta (no había respuesta) | **7/7** | 4/7 |
| Abstención indebida (sí había respuesta) | 2/20 | **1/20** |
| Cobertura de citas | 100 % | 100 % |
| Latencia mediana | 84 ms | 16 ms |

Las palabras clave responden más, pero mal cuando no hay evidencia: a «precio del oro en Bolivia» citan «el precio del clientelismo». Sesgo declarado: conjunto de desarrollo preparado por el equipo, no reservado.

### Clasificación de tema (284 etiquetas revisadas por las tres personas del equipo)
| Método | Macro-F1 |
|---|---|
| **Entrenado con etiquetas humanas** | **0,449** |
| Reglas por palabras clave | 0,259 |
| Embeddings sin entrenar | 0,163 |

Validación cruzada de 5 pliegues. Etiquetas pre-propuestas por Codex y revisadas fila por fila por una persona (81 corregidas), con el nombre de quien revisó cada fila.

### Agrupación por evento (40 pares revisados)
Con el umbral en uso (0,945): precisión 0,50 y cobertura 0,14. Bajarlo a 0,90 sube la cobertura a 0,77, pero en el snapshot completo fusiona hechos distintos (por ejemplo, cuatro notas de fútbol en un caso). Se prioriza no esconder un hecho dentro de otro.

### Redacción y guardián
El modelo recibe solo afirmaciones citadas y devuelve JSON. Cada oración pasa por el guardián; lo retirado se muestra con su motivo. El modelo se eligió en un banco de 5 modelos locales: `llama3.2:3b` fue el único que no inventó cifras; `qwen3:1.7b` citó una fuente maliciosa, por eso la protección vive en el código y no en el modelo.

### Generar versión
`src/editorial/criterios.py` arma el prompt solo con los criterios elegidos (formato, duración, palabras, tono, enfoque, público, énfasis) y repite las reglas: sin hechos nuevos, quedarse corto antes que rellenar, el tono cambia la forma y no los hechos. Si el modelo no responde, se arma una versión determinista desde las citas.

---

## 5. Pruebas de aceptación T01–T10

| ID | Prueba | Estado | Evidencia |
|---|---|---|---|
| T01 | Fechas inválidas y nulos | Cumple | Cuarentena con archivo, fila y causa; nulos conservados |
| T02 | Tres registros del mismo evento | Cumple | Un caso con dos medios; procedencia solo por origen declarado |
| T03 | Noticia antigua recirculada | Cumple | Nota de abr 2025 conserva su fecha; urgencia mínima |
| T04 | Cifra anual del Banco Mundial | Cumple | País, año, unidad y aviso «no es una medición actual» |
| T05 | Afirmaciones incompatibles | Cumple | Muestra ambas cifras y deja el caso insuficiente; control negativo «$500 mil» = «$500,000» |
| T06 | Consulta sin respuesta | Cumple | 7/7 abstenciones correctas |
| T07 | Fuente que exige ignorar instrucciones | Cumple | Evidencia maliciosa excluida; pregunta con instrucciones rechazada |
| T08 | Caso de prioridad alta | Cumple | Componentes visibles; no existe estado «publicado» |
| T09 | Brief editorial | Cumple (con límite declarado) | Una cita por afirmación; el guardián retiró copy publicitario |
| T10 | Sin internet durante la demo | Cumple | Corrida con el Wi-Fi cortado: 5/5 pasos; 0 de 52 intentos de la sonda salieron a la red |

Matriz completa con entradas, resultados y evidencias: `evaluation/matriz-T01-T10.md`.

**Además:** 125 pruebas automáticas; verificación viva de la app real en verde en dos corridas seguidas (contraste en reposo, hover y presionado en ambos temas; 360 y 390 px; recorridos de punta a punta; sin errores de consola).

---

## 6. Seguridad y riesgos

### Auditoría (OWASP Top 10 / CWE Top 25), 8 de octubre de 2026
**0 críticos, 0 altos.** Corregidos con prueba automática:

| Severidad | Hallazgo | Corrección |
|---|---|---|
| Media | El servidor no validaba `Host` (DNS rebinding) | Solo `127.0.0.1` y `localhost` en su puerto |
| Media | El guardián no revisaba palabras cortas («no», «mil») | Negaciones y multiplicadores deben estar en la evidencia citada |
| Baja | Cuerpos no JSON o no objeto cortaban la conexión | Cuerpo JSON obligatorio, acotado y tipado |
| Baja | Sin timeout de socket | 15 s |
| Baja | Errores con texto interno de Python | Mensajes propios |
| Baja | Lista corta de instrucciones prohibidas | Ampliada (español e inglés) |

Sin hallazgos en: inyección SQL (todo parametrizado), path traversal, XSS (todo pasa por escape), secretos en el código o el historial, recursos externos.

### Riesgos éticos
| Riesgo | Control |
|---|---|
| Inventar hechos, cifras o citas | Guardián; abstención si falta evidencia |
| Inyección desde una fuente o una pregunta | Las fuentes son datos; las instrucciones se rechazan |
| Confundir repetición con corroboración | Procedencia solo por origen declarado |
| Presentar un dato anual como actual | Año, unidad y aviso explícito |
| Derechos de autor | Solo titulares y metadatos |
| Privacidad y reputación | Sin datos personales; acusaciones atribuidas a su medio |
| Credenciales | Ninguna clave necesaria |

---

## 7. Una prueba fallida y su corrección
Con noticias reales, el modelo escribió «¡Reserva tu crucero ahora y prepárate para una aventura inolvidable!» y expandió «RSE» como «Resolución de Situaciones Económicas». El guardián validaba las afirmaciones, pero no la prosa libre. Ahora cada oración pasa por el guardián y lo retirado sale con su motivo, con prueba automática sobre esos casos reales. Otros fallos encontrados y corregidos con datos reales: el centroide unía 102 titulares sin relación; «turistas en septiembre de 2026» citaba cruceros por el «2026»; un umbral heredado dejaba todos los titulares sin tema.

---

## 8. Estructura del repositorio
| Carpeta | Contenido |
|---|---|
| `src/ia/` | Embeddings, clasificador, agrupación, consulta, redacción, guardián, contradicciones |
| `src/editorial/` | Cronómetro, formatos, criterios y Generar versión |
| `src/interfaz/` | Servidor local e interfaz |
| `scripts/` | Extracción, importación, preparación de la demo, benchmark, puertas sin red y de contraste, verificación viva |
| `data/snapshot-dev/` | Snapshot real con manifest SHA-256 |
| `evaluation/` | Benchmark, matriz, etiquetas humanas y resultados |
| `verificacion/` | Prueba sin red, verificación viva y capturas |
| `contracts/` | Esquema SQLite y diccionario de datos |
| `docs/` | Dossier, marca y documentación por módulo |
