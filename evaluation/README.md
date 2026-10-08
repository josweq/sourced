# Evaluación

Aquí está lo que se midió y con qué. Cada resultado identifica el snapshot, la fecha y sus fallos; las metas del reto no se presentan como resultados.

## Qué hay aquí

| Ruta | Contenido |
|---|---|
| [`matriz-T01-T10.md`](matriz-T01-T10.md) | Las diez pruebas de aceptación del reto: resultado esperado, resultado observado, evidencia y estado |
| `benchmark/desarrollo.jsonl` | 40 preguntas de desarrollo: 20 sustentadas, 7 sin respuesta, 6 adversariales, 4 ambiguas y 3 de contradicción |
| `etiquetas/temas.csv` | 284 titulares con el tema revisado a mano por las tres personas del equipo (Josué 95, Diego 95, Juanchi 94) |
| `etiquetas/pares.csv` | 40 pares de titulares revisados a mano: ¿hablan del mismo evento? |
| `etiquetas/propuesta-codex-*.csv` | Propuesta inicial hecha con IA que el equipo aceptó o corrigió fila por fila |
| `resultados/` | Salidas guardadas de cada corrida: benchmark con IA y con la línea base sin IA, clasificación, agrupación y contradicciones |
| [`banco-modelos.md`](banco-modelos.md), `banco-modelos/` | Comparación exploratoria de modelos locales de redacción y sus salidas crudas |
| [`modelo-datos-v1.md`](modelo-datos-v1.md) | Verificación del modelo de datos con ejemplos sintéticos |

## Cómo repetir las mediciones

```sh
python scripts/evaluar_benchmark.py --db data/local/<base>.sqlite
python scripts/evaluar_contradicciones.py --db data/local/<base>.sqlite
```

La base se crea con `python scripts/preparar_demo.py` (ver el [README principal](../README.md)). Cada corrida del benchmark escribe un archivo nuevo en `resultados/` con numerador, denominador y cada fallo.

## Reglas

- No guardar aquí las respuestas reservadas del jurado.
- No incluir métricas ficticias ni presentar metas como resultados.
- Las etiquetas humanas vienen de revisión del equipo, no de GDELT ni de un modelo.
- Los casos alterados o inventados se identifican como sintéticos (`SYN-`).
- Cada ejecución debe identificar commit, snapshot, modelo y prompts, entorno, entradas, salidas y fecha.
