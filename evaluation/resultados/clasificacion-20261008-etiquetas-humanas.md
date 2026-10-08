# Reporte de clasificación temática

Fecha UTC: `20261008-etiquetas-humanas`
Conjunto: 283/283 filas etiquetadas.
Método de etiquetado: CSV de etiquetas humanas; filas vacías ignoradas.

## reglas_tematicas
- Macro-F1: 0.2587 (185/283 aciertos exactos).
- Matriz de confusión labels=['economia', 'eventos_naturales', 'regulacion', 'servicios_publicos', 'sin_clasificar', 'turismo']
- Valores: `[[4, 0, 0, 0, 15, 0], [0, 0, 0, 0, 9, 0], [2, 0, 3, 2, 35, 1], [0, 0, 0, 6, 18, 0], [0, 2, 0, 5, 172, 2], [1, 0, 0, 0, 4, 0]]`

## prototipos_e5_zero_shot
- Macro-F1: 0.1635 (30/283 aciertos exactos).
- Matriz de confusión labels=['economia', 'eventos_naturales', 'regulacion', 'servicios_publicos', 'sin_clasificar', 'turismo']
- Valores: `[[4, 1, 0, 7, 0, 0], [0, 6, 0, 2, 0, 0], [2, 1, 6, 18, 0, 3], [0, 4, 1, 14, 0, 1], [3, 20, 4, 85, 0, 18], [0, 0, 0, 2, 0, 0]]`

## logreg_supervisado
- Macro-F1: 0.4490 (179/283 aciertos exactos).
- Matriz de confusión labels=['economia', 'eventos_naturales', 'regulacion', 'servicios_publicos', 'sin_clasificar', 'turismo']
- Valores: `[[8, 1, 2, 4, 2, 2], [0, 5, 1, 1, 1, 1], [5, 3, 22, 8, 3, 3], [1, 1, 4, 14, 3, 1], [7, 10, 11, 12, 127, 14], [0, 1, 1, 0, 1, 3]]`

## Advertencias
- Clases fuera del entrenamiento por tener menos de 5 ejemplos: {'logistica_canal': 1}.
