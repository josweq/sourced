# Reporte de clasificación temática

Fecha UTC: `20261008-etiquetas-humanas`
Conjunto: 189/189 filas etiquetadas.
Método de etiquetado: CSV de etiquetas humanas; filas vacías ignoradas.

## reglas_tematicas
- Macro-F1: 0.2536 (125/189 aciertos exactos).
- Matriz de confusión labels=['economia', 'eventos_naturales', 'regulacion', 'servicios_publicos', 'sin_clasificar', 'turismo']
- Valores: `[[3, 0, 0, 0, 10, 0], [0, 0, 0, 0, 8, 0], [2, 0, 1, 0, 18, 0], [0, 0, 0, 4, 15, 0], [0, 1, 0, 2, 117, 2], [1, 0, 0, 0, 3, 0]]`

## prototipos_e5_zero_shot
- Macro-F1: 0.2098 (23/189 aciertos exactos).
- Matriz de confusión labels=['economia', 'eventos_naturales', 'regulacion', 'servicios_publicos', 'sin_clasificar', 'turismo']
- Valores: `[[4, 1, 0, 4, 0, 0], [0, 6, 0, 1, 0, 0], [1, 1, 3, 9, 0, 0], [0, 3, 1, 10, 0, 1], [0, 11, 2, 56, 0, 14], [0, 0, 0, 1, 0, 0]]`

## logreg_supervisado
- Macro-F1: 0.4785 (121/189 aciertos exactos).
- Matriz de confusión labels=['economia', 'eventos_naturales', 'regulacion', 'servicios_publicos', 'sin_clasificar', 'turismo']
- Valores: `[[3, 1, 3, 3, 2, 1], [0, 6, 0, 1, 1, 0], [2, 0, 12, 5, 2, 1], [2, 1, 3, 10, 2, 1], [5, 3, 11, 9, 87, 7], [0, 1, 0, 0, 1, 3]]`
