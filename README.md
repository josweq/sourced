# Jajanken Lupa
**Antes de contar una historia, mostramos qué la sostiene.**

Copiloto editorial para el reto TVN Media. Equipo: **Josué, Juanchi y Diego**.
Convierte noticias públicas e indicadores oficiales en agenda priorizada, fichas trazables y borradores para revisión humana.

## Estado real (2026-10-08, rama `josue/integracion`)
Prototipo local funcionando de punta a punta con **datos reales del 7 de octubre de 2026**: 284 titulares de cinco medios panameños (TVN, La Prensa, Crítica, Panamá América, En Segundos; solo titular y metadatos), 540 valores del Banco Mundial y 82 sismos de USGS. GDELT quedó fuera: respondió HTTP 429 a todas las consultas.

| Pieza | Estado |
|---|---|
| Snapshot reproducible con manifest SHA-256 | Hecho (`data/snapshot-dev/real-20261007b/processed`) |
| Embeddings locales (multilingual-e5-small, CPU), agrupación semántica calibrada, búsqueda híbrida | Hecho |
| Clasificación de tema supervisada | Código listo; **faltan las etiquetas humanas** (hoja de etiquetado repartida). Mientras tanto usa reglas y lo declara |
| Redacción con Ollama `llama3.2:3b` + guardián (citas, cifras, términos sin respaldo, tono publicitario, inyección) | Hecho |
| Mesa editorial: brief, guion con cronómetro, copy, preguntas, versiones, revisión humana | Hecho |
| Preguntas en español con respuesta citada o abstención (CU-02, CU-04, CU-05) | Hecho |
| Adaptar la nota: TV, radio 30 s, video vertical 60 s, web y alerta (duración, énfasis, tono) | Hecho |
| Guías «qué significa» en cada sección y guía rápida «Cómo leer Lupa» | Hecho |
| Benchmark de desarrollo (40 preguntas) | 37/40 · abstención correcta 7/7 · citas 33/33 · mediana 92 ms; línea base sin IA (palabras clave): 35/40 y abstención correcta 4/7 (`evaluation/resultados/`) |
| Matriz T01–T10 | 9 cumplen y T05 parcial; T10 corrida con el Wi-Fi cortado: 5/5 pasos y 0 salidas a la red (`evaluation/matriz-T01-T10.md`, `verificacion/prueba-local.md`) |
| Notion | Dossier listo para importar (`docs/notion/dossier.md`) |

Pruebas: 100/100. Verificación viva en verde dos veces (contraste en ambos temas, 360/390 px) en `verificacion/`. Prueba sin red: `python scripts/smoke_sin_red.py --db <base>` y puerta estática `python scripts/check_sin_red.py`.

## Probar en 5 pasos (Windows, macOS o Linux; sin GPU, sin claves)
```sh
python -m venv .venv && .venv\Scripts\activate        # en macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
ollama pull llama3.2:3b                                # requiere Ollama instalado
python scripts/preparar_modelos.py                     # descarga y verifica el modelo de embeddings (una vez)
python scripts/preparar_demo.py --snapshot data/snapshot-dev/real-20261007b --borradores 3
python src/interfaz/app.py --db <ruta que imprimió el paso anterior>
```
Abrir `http://127.0.0.1:8765`. Con `--borradores 0` el paso 5 tarda ~1 minuto; cada borrador con el modelo local suma ~60–90 s en CPU.

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
Notion es obligatorio para ejecutar, documentar y presentar; GitHub no lo reemplaza.
No publicar automáticamente. No inventar cifras, citas ni resultados.
Separar prioridad editorial de suficiencia de evidencia.
La demo debe funcionar sin internet con fallback documentado.

## Origen
Plan derivado del PDF de 12 páginas «hackIAthon - reto TVN Media.pdf» facilitado por Diego, cuyas fuentes llevan fecha de consulta 05/10/2026. No se incluye el PDF ni contenido protegido. Confirmar reglas definitivas y snapshot con organización.

## Estructura compartida
Consulta [el mapa de módulos](docs/10-estructura.md), [los contratos propuestos](contracts/README.md) y [las plantillas](templates/tarea.md). `src/`, `scripts/`, `tests/` y `evaluation/` contienen el prototipo local, sus utilidades y la evidencia de prueba.

## Restricción vigente
**No acceder, subir, crear, editar ni sincronizar contenido en Notion por el momento.** La plantilla se conserva solo como preparación en GitHub. Nadie tiene tareas asignadas; cada integrante decide qué explorar con su IA.

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

El [recorrido local](docs/12-importador-interfaz.md) incluye carga CSV con cuarentena de filas inválidas y una primera interfaz de agenda, evidencia, borrador y revisión. Funciona con biblioteca estándar de Python y datos sintéticos; los datos oficiales siguen pendientes.

El [baseline de agrupación y ranking](docs/13-agrupacion-ranking.md) conecta la importación con la agenda. Es una comparación determinista y explicable, no la capacidad de IA requerida por el reto.

La [búsqueda editorial](docs/14-busqueda-baseline.md) filtra la agenda por texto y metadatos, explica coincidencias y se abstiene cuando no encuentra un caso sustentado.

## Licencia

MIT (ver `LICENSE`). Las fuentes tipográficas incluidas conservan su licencia SIL OFL 1.1.
