# Etiquetas humanas: clasificación de tema y agrupación (2026-10-08)

**Etiquetado:** pre-etiquetado por Codex y revisado fila por fila por las tres personas del equipo (Josué, Juanchi y Diego; ~95 titulares y 13–14 pares cada una). 284 temas (81 corregidos por la persona) y 40 pares. Archivos: `evaluation/etiquetas/temas.csv` y `pares.csv`, con el nombre de quien revisó cada fila. Consolidación: `python scripts/consolidar_etiquetas.py <hojas .xlsx>`.

## Clasificación de tema (validación cruzada estratificada de 5 pliegues, 283 etiquetas)

| Método | Macro-F1 | Aciertos exactos |
|---|---|---|
| **Regresión logística sobre embeddings locales, entrenada con las etiquetas humanas** | **0,449** | 179/283 |
| Reglas por palabras clave (línea base sin IA) | 0,259 | 185/283 |
| Prototipos de embeddings sin entrenar (zero-shot) | 0,163 | 30/283 |

F1 por tema (supervisado frente a reglas): regulación 0,52 / 0,13 · servicios públicos 0,44 / 0,32 · economía 0,40 / 0,31 · eventos naturales 0,33 / 0,00 · turismo 0,20 / 0,00 · sin clasificar 0,80 / 0,79.

**Lectura honesta:** el clasificador entrenado sube el macro-F1 de 0,26 a 0,45 y acierta en temas que las reglas nunca ven. En aciertos exactos las reglas quedan apenas arriba porque mandan casi todo a «sin clasificar», la clase mayoritaria (181 de 284). Conjunto pequeño y desbalanceado; en la agenda se ven errores (p. ej. notas de espectáculos clasificadas como regulación).

**Decisiones con evidencia:**
- *Umbral de confianza:* el heredado (0,45) dejaba todos los titulares sin tema (confianza máxima mediana 0,20 con 6 clases); como «sin clasificar» ya es una clase etiquetada, el umbral es 0.
- *Clases con menos de 5 ejemplos:* una sola etiqueta de «logística y Canal» impedía entrenar el modelo entero; ahora esas clases quedan fuera del entrenamiento y se declaran (`sin_clases_pequenas`).

Reporte completo: `clasificacion-20261008-etiquetas-humanas.md`.

## Agrupación de titulares (40 pares revisados; 22 son el mismo evento)

| Umbral de similitud | Precisión en los pares | Cobertura en los pares | Casos con 2+ titulares en el snapshot | Caso más grande |
|---|---|---|---|---|
| 0,900 | 0,53 | 0,77 | 63 | 6 |
| 0,910 | 0,48 | 0,64 | 47 | 4 |
| 0,920 | 0,44 | 0,50 | 33 | 4 |
| **0,945 (en uso)** | **0,50** | **0,14** | **9** | **2** |

**Decisión:** se mantiene 0,945. En los 40 pares la precisión es parecida en todos los umbrales (los pares se eligieron cerca del límite: miden el caso difícil), pero al revisar el snapshot completo con 0,90 aparecen fusiones absurdas: Amber Heard con una reforma de seguridad chilena; el contrato de laptops del Meduca con la suspensión de clases en Bocas y una defensa de un nombramiento; cuatro notas de fútbol distintas en un solo caso. Fusionar hechos distintos esconde uno en la agenda; dejar dos tarjetas del mismo hecho cuesta un clic. Con el cuerpo de la nota (no solo el titular) la separación debería mejorar.

Reproducir: `scripts/procesar_snapshot.py` incluye `evaluacion_pares` en su reporte; la curva y la revisión por umbral se calcularon con los embeddings guardados en la base de la demo.
