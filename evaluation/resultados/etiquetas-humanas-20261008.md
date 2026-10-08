# Etiquetas humanas: clasificación de tema y agrupación (2026-10-08)

**Etiquetado:** pre-etiquetado por Codex y revisado fila por fila por dos personas del equipo (Josué y Juanchi). 189 temas (72 corregidos por la persona) y 27 pares. La hoja de Diego no llegó a tiempo. Archivos: `evaluation/etiquetas/temas.csv` y `pares.csv` (con el nombre de quien revisó cada fila). Consolidación: `python scripts/consolidar_etiquetas.py <hojas .xlsx>`.

## Clasificación de tema (validación cruzada estratificada de 5 pliegues)

| Método | Macro-F1 | Aciertos exactos |
|---|---|---|
| **Regresión logística sobre embeddings locales, entrenada con las etiquetas humanas** | **0,479** | 121/189 |
| Reglas por palabras clave (línea base sin IA) | 0,254 | 125/189 |
| Prototipos de embeddings sin entrenar (zero-shot) | 0,210 | 23/189 |

F1 por tema (supervisado frente a reglas): regulación 0,47 / 0,09 · eventos naturales 0,60 / 0,00 · turismo 0,33 / 0,00 · servicios públicos 0,43 / 0,32 · economía 0,24 / 0,32 · sin clasificar 0,80 / 0,80.

**Lectura honesta:** el clasificador entrenado casi duplica el macro-F1 de las reglas. En aciertos exactos las reglas quedan apenas arriba porque mandan casi todo a «sin clasificar», la clase mayoritaria (122 de 189); el macro-F1 premia acertar en todas las clases. Conjunto pequeño y desbalanceado: turismo tiene 5 ejemplos; «logística y Canal» no recibió ninguna etiqueta humana y por eso el modelo no la predice.

**Calibración:** el umbral de confianza heredado (0,45) dejaba todos los titulares sin tema (la confianza máxima mediana es 0,20 con 6 clases); como «sin clasificar» ya es una clase etiquetada, el umbral se fijó en 0. Reporte completo: `clasificacion-20261008-etiquetas-humanas.md`.

## Agrupación de titulares (27 pares revisados; 17 son el mismo evento)

| Umbral de similitud | Precisión | Cobertura |
|---|---|---|
| 0,900 | 0,59 | 0,76 |
| 0,920 | 0,56 | 0,59 |
| 0,930 | 0,50 | 0,24 |
| 0,940 | 0,67 | 0,24 |
| **0,945 (en uso)** | **0,75** | **0,18** |

**Decisión:** se mantiene 0,945, que prioriza la precisión. Con solo titulares, los pares del mismo evento (0,889–0,961) y los distintos (0,898–1,0; hay un par de títulos idénticos sobre hechos distintos) se superponen. Fusionar dos hechos distintos esconde uno en la agenda; dejar dos tarjetas del mismo hecho solo cuesta un clic. Los pares se eligieron cerca del umbral, así que miden el caso difícil, no el promedio. Con el cuerpo de la nota (no solo el titular) la separación debería mejorar.
