# Búsqueda editorial baseline

Estado: primera versión funcional sobre la agenda local. Busca únicamente casos que ya existen en el snapshot; no consulta internet ni genera respuestas.

La interfaz permite combinar texto libre, tema, estado de evidencia, medio y rango de publicación. La consulta de texto normaliza mayúsculas y acentos, elimina palabras comunes y exige al menos una palabra coincidente en los titulares del grupo. Los resultados se ordenan por proporción de palabras coincidentes y luego por prioridad editorial.

Cada resultado declara sus palabras coincidentes o indica que coincide por filtros. Si no existe un caso sustentado, la respuesta queda vacía y muestra una abstención explícita. La interfaz también presenta el tiempo de la consulta y la versión `palabras-clave-v1`.

API local:

```text
GET /api/search?q=economico&tema=economia&evidencia=parcial&medio=Medio&desde=2024-06-01&hasta=2024-06-02
```

Los parámetros son opcionales. Las fechas usan `YYYY-MM-DD`; un tema, estado o rango inválido devuelve HTTP 400.

## Límites conocidos

- No entiende sinónimos, intención, entidades ni relaciones semánticas.
- Una coincidencia léxica no demuestra que dos publicaciones corroboren un hecho.
- Busca titulares y metadatos autorizados; no amplía el alcance de uso de las fuentes.
- El tiempo local observado sirve para detectar regresiones, pero todavía no es un benchmark representativo.
- Debe compararse con consultas y relevancia etiquetadas por personas antes de afirmar calidad editorial.
