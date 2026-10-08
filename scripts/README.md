# Scripts

Utilidades de línea de comandos del proyecto. Se ejecutan desde la raíz del repositorio con el entorno virtual activo, por ejemplo `python scripts/preparar_demo.py --help`.

## Para preparar y correr la demo

| Script | Para qué sirve |
|---|---|
| `preparar_modelos.py` | Descarga y verifica el modelo local de embeddings y comprueba que Ollama esté presente. Se corre una vez |
| `preparar_demo.py` | Prepara en un paso la base de la demo a partir de un snapshot: importa, procesa con IA y genera borradores. Al terminar imprime el comando para abrir la interfaz |

Los pasos completos están en «Probar en 6 pasos» del [README principal](../README.md).

## Piezas que `preparar_demo.py` usa por dentro

| Script | Para qué sirve |
|---|---|
| `importar_csv.py` | Importa `noticias.csv` e `indicadores.csv` fila por fila; las filas inválidas van a cuarentena sin bloquear la carga (T01) |
| `procesar_snapshot.py` | Tubería de IA: embeddings, tema, grupos semánticos, casos y ranking |
| `procesar_agenda.py` | Línea base sin IA: agrupa por título, crea casos y calcula la prioridad. Sirve para comparar contra la IA |
| `modelo_datos.py` | Contrato de referencia del modelo de datos con ejemplos sintéticos; sin red ni IA |

## Construcción del snapshot (`extraccion/`)

| Script | Para qué sirve |
|---|---|
| `extraccion/construir_snapshot.py` | Arma el snapshot reproducible y su `manifest.json`. Nunca sobrescribe una versión existente |
| `extraccion/rss_medios.py`, `extraccion/tvn_rss.py` | Leen capturas RSS de los medios; conservan solo titular y metadatos |
| `extraccion/banco_mundial.py` | Indicadores obligatorios del Banco Mundial |
| `extraccion/usgs.py` | Sismos regionales de USGS |
| `extraccion/gdelt.py` | Titulares y metadatos de GDELT DOC 2.0 (sin aportes en el snapshot actual: HTTP 429) |
| `extraccion/comun.py`, `extraccion/red.py` | Normalización compartida y cliente HTTP con reintentos |

Estos scripts consultan las fuentes públicas por internet y solo hacen falta para construir un snapshot nuevo; la demo corre con el snapshot ya guardado y sin red (aparte de ellos, solo `preparar_modelos.py` descarga algo: el modelo de embeddings, una vez). Detalle en [`docs/15-snapshot-dev.md`](../docs/15-snapshot-dev.md).

## Evaluación y etiquetas

| Script | Para qué sirve |
|---|---|
| `evaluar_benchmark.py` | Ejecuta el benchmark de desarrollo contra la base de la demo y guarda salidas y métricas en `evaluation/resultados/` |
| `evaluar_contradicciones.py` | Busca cifras incompatibles entre medios en una base derivada, abriéndola en solo lectura (T05) |
| `preparar_etiquetado.py` | Genera las hojas de revisión humana para temas y pares del mismo evento |
| `consolidar_etiquetas.py` | Convierte las hojas revisadas por el equipo en `evaluation/etiquetas/temas.csv` y `pares.csv` |

## Puertas de calidad

| Script | Para qué sirve |
|---|---|
| `check_sin_red.py` | Revisión estática para T10: el código que corre en la demo no puede salir del equipo. Sale con 0 si pasa |
| `smoke_sin_red.py` | Prueba de humo para T10: ejerce las piezas locales y sale con 0 solo si todas funcionan |
| `check_contraste.py` | Contraste WCAG de los colores de la interfaz |
| `verificacion-viva/*.mjs` | Recorrido de la aplicación en ejecución con Node: contraste real, anchos de teléfono y capturas. Resultados en `verificacion/` |

Comprobaciones rápidas, las mismas que corre el equipo:

```sh
python -m unittest discover -s tests -p "test_*.py"
python scripts/check_sin_red.py
python scripts/check_contraste.py
```
