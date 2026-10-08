# Sourced
*Nada sin fuente.*
**Antes de contar una historia, mostramos qué la sostiene.**

Copiloto editorial para el reto TVN Media. Equipo: **Josué, Juanchi y Diego**.
Convierte noticias públicas e indicadores oficiales en agenda priorizada, fichas trazables y borradores para revisión humana.

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
| Benchmark de desarrollo (40 preguntas) | 37/40 · abstención correcta 7/7 · citas 33/33 · mediana 92 ms; línea base sin IA (palabras clave): 35/40 y abstención correcta 4/7 (`evaluation/resultados/`) |
| Matriz T01–T10 | 10/10 cumplen; T05 detecta cifras incompatibles entre medios (0 en el snapshot real, sintético SYN detectado); T10 corrida con el Wi-Fi cortado: 5/5 pasos y 0 salidas a la red (`evaluation/matriz-T01-T10.md`, `verificacion/prueba-local.md`) |
| Dossier | [`docs/notion/dossier.md`](docs/notion/dossier.md): fuente completa con capturas, decisiones, fichas, pruebas, riesgos, guion del pitch y bitácora. Copia en el espacio de Notion «hackIAthon 4taEd» (la organización indicó avanzar sin depender de Notion) |

Pruebas: 125/125. Instalación probada desde cero en un entorno limpio (clon nuevo, venv nuevo, caché de modelos vacía). Verificación viva en verde dos veces (contraste en ambos temas, 360/390 px) en `verificacion/`. Prueba sin red: `python scripts/smoke_sin_red.py --db <base>` y puerta estática `python scripts/check_sin_red.py`.

## Probar en 6 pasos (Windows, macOS o Linux; sin GPU, sin claves)
Requisitos: Git, Python 3.10+ y [Ollama](https://ollama.com/download) instalado. Un comando por línea (funciona igual en PowerShell 5.1, PowerShell 7, cmd y bash).

```sh
git clone https://github.com/pixeltabletop/jajanken-lupa.git
cd jajanken-lupa
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

## Empieza aquí
1. Lee [AGENTS.md](AGENTS.md), también con una IA que no lo cargue automáticamente.
2. Revisa [producto](docs/01-producto.md), [requisitos](docs/02-requisitos.md) y [backlog](docs/06-backlog.md).
3. Usa [la guía para tu IA](prompts/README.md).
4. Trabaja en una rama y abre un PR siguiendo [CONTRIBUTING.md](CONTRIBUTING.md).

## Documentación
- [Producto y demo](docs/01-producto.md)
- [Requisitos y rúbrica](docs/02-requisitos.md)
- [Arquitectura propuesta](docs/03-arquitectura.md)
- [Datos y contratos](docs/04-datos.md)
- [Pruebas y métricas](docs/05-pruebas.md)
- [Backlog sin asignaciones](docs/06-backlog.md)
- [Plantilla de Notion y pitch](docs/07-notion.md)
- [Decisiones y dudas abiertas](docs/08-decisiones.md)
- [Seguridad y derechos](docs/09-seguridad.md)
- [Búsqueda editorial baseline](docs/14-busqueda-baseline.md)

## Flujo
Snapshot → validación → organización → contexto → ranking → ficha → borrador → revisión humana → Notion.

## Reglas esenciales
La documentación del reto (decisiones, fichas, pruebas, riesgos y pitch) está en el dossier; Notion la replica cuando la cuenta del reto lo permite.
No publicar automáticamente. No inventar cifras, citas ni resultados.
Separar prioridad editorial de suficiencia de evidencia.
La demo debe funcionar sin internet con fallback documentado.

## Origen
Plan derivado del PDF de 12 páginas «hackIAthon - reto TVN Media.pdf» facilitado por Diego, cuyas fuentes llevan fecha de consulta 05/10/2026. No se incluye el PDF ni contenido protegido. Confirmar reglas definitivas y snapshot con organización.

## Estructura compartida
Consulta [el mapa de módulos](docs/10-estructura.md), [los contratos propuestos](contracts/README.md) y [las plantillas](templates/tarea.md). `src/`, `scripts/`, `tests/` y `evaluation/` contienen el prototipo local, sus utilidades y la evidencia de prueba.

## Notion
La organización indicó avanzar sin depender de Notion porque la cuenta Business del reto no funciona. La documentación completa está en [`docs/notion/dossier.md`](docs/notion/dossier.md) y hay una copia en el espacio «hackIAthon 4taEd».

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
