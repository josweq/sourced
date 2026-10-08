# Capa de IA local

Estado: implementación inicial de embeddings, tema, agrupación y búsqueda híbrida. No publica, no decide verdad y no convierte repetición en corroboración.

## Piezas

- `src/ia/embeddings.py`: carga `intfloat/multilingual-e5-small` por defecto (`SOURCED_EMBEDDINGS`), usa prefijos obligatorios `passage: ` y `query: `, normaliza vectores y guarda caché SQLite por `(modelo, sha256(texto prefijado))`.
- `scripts/preparar_modelos.py`: descarga/verifica embeddings y comprueba si Ollama tiene `llama3.2:3b`. Si falta Ollama o el modelo, solo lo informa y termina con salida distinta de cero; no instala nada.
- `src/ia/clasificador.py`: entrena regresión logística balanceada sobre `evaluation/etiquetas/temas.csv`. Evalúa contra reglas temáticas y prototipos e5 zero-shot en el mismo conjunto, con macro-F1, precisión, recall y matriz de confusión.
- `src/ia/agrupacion.py`: agrupa por coseno con umbral calibrable y límite de días. Conserva cada publicación, URL, medio y `origen`; la procedencia sale solo de `origen`.
- `src/ia/recuperacion.py`: búsqueda `palabras`, `semantica` o `hibrida` por fusión de rangos recíprocos. Cada resultado explica si entró por palabras, significado o ambos.
- `scripts/procesar_snapshot.py`: crea una base derivada nueva desde una importación limpia, agrega tablas auxiliares de IA, rellena `noticias.tema` solo en la derivada y genera grupos, casos, evidencias y priorización `ia-v1`.
- `scripts/preparar_etiquetado.py`: genera CSV para revisión humana de temas y pares. Las propuestas son ayuda; `etiqueta_humana` y `mismo_evento` quedan vacíos.

## Entrenar y evaluar temas

1. Genera insumos de etiquetado:

```sh
python scripts/preparar_etiquetado.py --db data/local/importacion.sqlite
```

2. Completa manualmente `evaluation/etiquetas/temas.csv` con columnas `id_noticia,titulo,etiqueta_humana`. Las filas con etiqueta vacía se ignoran.
3. Ejecuta la evaluación:

```sh
python -c "from pathlib import Path; from src.ia.clasificador import evaluar; evaluar(Path('evaluation/etiquetas/temas.csv'))"
```

El reporte queda en `evaluation/resultados/clasificacion-<fecha>.json` y `.md`. Si algún tema tiene menos de 5 ejemplos, se declara y no se inventan métricas de validación cruzada.

## Procesar una base

```sh
python scripts/preparar_modelos.py
python scripts/procesar_snapshot.py --input data/local/importacion.sqlite --output data/local/sourced-ia.sqlite
python src/interfaz/app.py --db data/local/sourced-ia.sqlite --port 8765
```

La salida nunca sobrescribe una base existente. Si no hay etiquetas suficientes, el tema usa el baseline de reglas y el reporte lo declara.

## Cómo leer reportes

- `macro_f1` compara rendimiento por tema sin favorecer el tema más frecuente.
- La matriz de confusión muestra qué tema humano terminó en qué predicción.
- El numerador/denominador de aciertos exactos ayuda a no confundir métricas con tamaño de muestra.
- En agrupación, precisión y recall de `mismo_evento` se comparan contra el Jaccard de Diego.

## Límites

- Los titulares son cortos: un embedding puede juntar eventos parecidos sin suficiente evidencia.
- El sesgo de la palabra “Panamá” hizo fallar la clasificación zero-shot por prototipos en la medición previa: márgenes de 0,001 a 0,02 y 55/151 titulares asignados a `logistica_canal`. Por eso el tema final usa clasificador supervisado cuando hay etiquetas humanas suficientes.
- Si la probabilidad máxima queda bajo 0,45, el resultado es `sin_clasificar` con motivo “confianza baja”.
- Repetición no equivale a corroboración. Varias publicaciones conservan sus URLs y medios, pero la procedencia independiente solo se toma del campo `origen`.
- Sin `preparar_modelos.py`, la ejecución normal no debe llamar a red; si el modelo no está en caché, la carga falla con mensaje explícito.

## Medición previa

Claude midió el 2026-10-07 sobre 151 titulares reales del RSS de TVN: cerca de 100 embeddings/s y 32 ms por consulta en CPU con `intfloat/multilingual-e5-small` (dimensión 384, vectores normalizados).
