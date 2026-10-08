# Sourced
*Nada sin fuente.*
**Antes de contar una historia, mostramos qué la sostiene.**

Copiloto editorial para el reto TVN Media. Equipo Jajanken: **Josué Carrillo, Diego Laverde y Juan Andrés López**.

**Cómo trabajamos.** Sourced es obra del equipo Jajanken completo: Josué Carrillo, Diego Laverde y Juan Andrés López decidimos juntos el alcance, el diseño y la identidad, etiquetamos y revisamos los datos a mano, probamos la herramienta y preparamos la documentación y la presentación. Por practicidad, el código se integró y publicó desde un solo equipo y una sola cuenta de GitHub, por eso la mayoría de los commits aparecen con un mismo autor. Usamos asistentes de IA (Codex para construir partes del código y Claude para auditarlo y documentarlo), siempre bajo revisión del equipo.
Convierte noticias públicas e indicadores oficiales en agenda priorizada, fichas trazables y borradores para revisión humana.

**Video de demostración (4:43):** [`docs/demo/sourced-demo.mp4`](docs/demo/sourced-demo.mp4), también adjunto al [release v1.0.0](https://github.com/josweq/sourced/releases/tag/v1.0.0). Recorre la aplicación real con datos reales y explica qué hace la IA local en cada etapa. Música: «Inspired», de Kevin MacLeod (incompetech.com), bajo Creative Commons Atribución 4.0; no forma parte de la aplicación.

## Estado real (2026-10-08, rama `main`)
Prototipo local funcionando de punta a punta con **datos reales del 7 de octubre de 2026**: 284 titulares de cinco medios panameños (TVN, La Prensa, Crítica, Panamá América, En Segundos; solo titular y metadatos), 540 valores del Banco Mundial y 82 sismos de USGS. GDELT quedó fuera: respondió HTTP 429 a todas las consultas.

| Pieza | Estado |
|---|---|
| Snapshot reproducible con manifest SHA-256 | Hecho (`data/snapshot-dev/real-20261007b/processed`) |
| Embeddings locales (multilingual-e5-small, CPU), agrupación semántica calibrada, búsqueda híbrida | Hecho |
| Clasificación de tema supervisada | Hecho con 284 etiquetas revisadas por las tres personas del equipo: macro-F1 0,449 frente a 0,259 de reglas y 0,163 sin entrenar; agrupación evaluada con 40 pares (`evaluation/resultados/etiquetas-humanas-20261008.md`) |
| Redacción con Ollama `llama3.2:3b` + guardián (citas, cifras, términos sin respaldo, tono publicitario, inyección) | Hecho |
| Mesa editorial: brief, guion con cronómetro, copy, preguntas, versiones, revisión humana | Hecho |
| Preguntas en español con respuesta citada o abstención (CU-02, CU-04, CU-05) | Hecho |
| Generar versión: formato, duración, palabras, tono, enfoque, público y énfasis como criterios opcionales; arma el prompt, el guardián valida y no rellena lo que la evidencia no sostiene | Hecho |
| Seguridad: auditoría OWASP/CWE sin hallazgos críticos ni altos; los medios y bajos corregidos con prueba (Host, cuerpo JSON, timeout, negaciones en el guardián) | Hecho |
| Guías «qué significa» en cada sección y guía rápida «Cómo leer Sourced» | Hecho |
| Benchmark de desarrollo (40 preguntas) | 37/40 · abstención correcta 7/7 · citas 33/33 · mediana 84 ms; línea base sin IA (palabras clave): 35/40 y abstención correcta 4/7 (`evaluation/resultados/`) |
| Matriz T01–T10 | 10/10 cumplen; T05 detecta cifras incompatibles entre medios (0 en el snapshot real, sintético SYN detectado); T10 corrida con el Wi-Fi cortado: 5/5 pasos y 0 salidas a la red (`evaluation/matriz-T01-T10.md`, `verificacion/prueba-local.md`) |
| Dossier | [`docs/notion/dossier.md`](docs/notion/dossier.md): fuente completa con capturas, decisiones, fichas, pruebas, riesgos, presentación y bitácora. Publicado en Notion (ver sección «Notion») |

Pruebas: 125/125. Instalación probada desde cero en un entorno limpio (clon nuevo, venv nuevo, caché de modelos vacía). Verificación viva en verde dos veces (contraste en ambos temas, 360/390 px) en `verificacion/`. Prueba sin red: `python scripts/smoke_sin_red.py --db <base>` y puerta estática `python scripts/check_sin_red.py`.

## Probar en 6 pasos (Windows, macOS o Linux; sin GPU, sin claves)
Requisitos: Git, Python 3.10+ y [Ollama](https://ollama.com/download) instalado. Un comando por línea (funciona igual en PowerShell 5.1, PowerShell 7, cmd y bash).

```sh
git clone https://github.com/josweq/sourced.git
cd sourced
python -m venv .venv
.venv\Scripts\activate                                 # macOS/Linux: source .venv/bin/activate · si PowerShell lo bloquea: Set-ExecutionPolicy -Scope Process Bypass
pip install -r requirements.txt                        # ~5 min la primera vez (PyTorch para CPU)
ollama pull llama3.2:3b
python scripts/preparar_modelos.py                     # descarga y verifica el modelo de embeddings (una vez); el aviso sobre HF_TOKEN es normal: no hace falta clave
python scripts/preparar_demo.py --snapshot data/snapshot-dev/real-20261007b --borradores 3
```
El último paso termina con **«Siguiente paso (cópialo tal cual)»**: copia esa línea (`python src/interfaz/app.py --db "data/local/demo-<marca>.sqlite"`) y abre `http://127.0.0.1:8765`. Con `--borradores 0` el paso tarda ~1–3 minutos; cada borrador con el modelo local suma ~60–90 s en CPU. Al arrancar, la interfaz precarga el modelo de embeddings: espera unos 20 s antes de la primera pregunta.

Comprobaciones opcionales (las mismas que corre el equipo):
```sh
python -m unittest discover -s tests -p "test_*.py"
python scripts/check_sin_red.py
python scripts/check_contraste.py
```

## Cómo está organizado
| Carpeta | Qué contiene |
|---|---|
| `src/ia/` | Embeddings locales, clasificador de tema, agrupación, búsqueda, consulta con abstención, redacción y guardián, contradicciones |
| `src/editorial/` | Cronómetro, formatos y «Generar versión» (criterios → prompt) |
| `src/interfaz/` | Servidor local (solo 127.0.0.1) y la interfaz HTML/CSS/JS sin dependencias externas |
| `scripts/` | Extracción del snapshot, importación, preparación de la demo, benchmark, puertas sin red y de contraste, verificación viva |
| `data/snapshot-dev/` | Snapshot real del 7-oct-2026 con manifest SHA-256 |
| `evaluation/` | Benchmark, matriz T01–T10, etiquetas humanas y resultados |
| `verificacion/` | Prueba sin red, verificación viva y capturas |
| `contracts/` | Esquema SQLite y diccionario de datos |
| `docs/` | Dossier del reto, marca y documentación técnica |

## Documentación
- [Dossier del reto (decisiones, fichas, pruebas, riesgos, pitch y bitácora)](docs/notion/dossier.md)
- [Marca Sourced: dirección visual y conceptos de logo](docs/marca/README.md)
- [Blueprint de arquitectura](docs/00-blueprint.md)
- [Producto y demo](docs/01-producto.md) · [Requisitos y rúbrica](docs/02-requisitos.md) · [Arquitectura](docs/03-arquitectura.md) · [Datos](docs/04-datos.md) · [Pruebas](docs/05-pruebas.md)
- [Decisiones](docs/08-decisiones.md) · [Seguridad y derechos](docs/09-seguridad.md)
- [Modelo de datos](docs/11-modelo-datos.md) · [Importador e interfaz](docs/12-importador-interfaz.md) · [Agrupación y ranking](docs/13-agrupacion-ranking.md) · [Búsqueda baseline](docs/14-busqueda-baseline.md)
- [Snapshot](docs/15-snapshot-dev.md) · [Sistema visual](docs/16-sistema-visual.md) · [Capa de IA](docs/17-capa-ia.md) · [Redacción y guardián](docs/18-redaccion-guardian.md) · [Formatos](docs/19-formatos.md)
- [Guía para asistentes de IA que trabajen en el repo](AGENTS.md)

## Flujo
Snapshot → validación → embeddings y temas → agrupación → ranking explicable → ficha → borrador citado → guardián → revisión humana.

## Reglas esenciales
No publicar automáticamente. No inventar cifras, citas ni resultados.
Separar prioridad editorial de suficiencia de evidencia.
La demo funciona sin internet (prueba con la red cortada en `verificacion/prueba-local.md`).

## Origen
Plan derivado del documento del reto «hackIAthon - reto TVN Media» (fuentes consultadas el 05/10/2026). No se incluye el PDF ni contenido protegido.

## Notion
Publicado y accesible sin sesión: la página pública del equipo en Notion tiene la [documentación técnica](https://conscious-handbell-91a.notion.site/Documentaci-n-t-cnica-3f36d0f0b114803e8a83dba0c7d1cfc4), la [documentación funcional](https://conscious-handbell-91a.notion.site/Documentaci-n-funcional-3f36d0f0b11480d89602d5296e6d6846) y la [presentación para el Pitch Day](https://conscious-handbell-91a.notion.site/Presentaci-n-Pitch-Day-3f36d0f0b114807081ebdfc46ca9e875), con el video. Las fuentes de esas páginas están en [`docs/notion/`](docs/notion/) y el expediente completo en [`docs/notion/dossier.md`](docs/notion/dossier.md).

## Probar el modelo de datos
Lee el [modelo y diagrama](docs/11-modelo-datos.md) y el [diccionario](contracts/diccionario.md).
Python 3.10+ con SQLite 3.37+, sin paquetes adicionales:

```sh
python scripts/modelo_datos.py
python -m unittest discover -s tests -p "test_*.py" -v
python scripts/modelo_datos.py --output data/local/modelo-demo.sqlite
```

El último comando crea una base nueva y nunca sobrescribe. Todos los ejemplos son sintéticos. [Resultados y límites de la verificación](evaluation/modelo-datos-v1.md).

## Importador e interfaz local

El [recorrido local](docs/12-importador-interfaz.md) incluye carga CSV con cuarentena de filas inválidas y una primera interfaz de agenda, evidencia, borrador y revisión. Funciona con biblioteca estándar de Python; hoy se usa con el snapshot real `real-20261007b` (ver «Probar en 6 pasos»).

El [baseline de agrupación y ranking](docs/13-agrupacion-ranking.md) conecta la importación con la agenda. Es una comparación determinista y explicable, no la capacidad de IA requerida por el reto.

La [búsqueda editorial](docs/14-busqueda-baseline.md) filtra la agenda por texto y metadatos, explica coincidencias y se abstiene cuando no encuentra un caso sustentado.

## Licencia

MIT (ver `LICENSE`). Las fuentes tipográficas incluidas conservan su licencia SIL OFL 1.1.
