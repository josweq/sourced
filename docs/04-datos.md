# Datos y contratos
Estado (8 de octubre de 2026): el snapshot real `real-20261007b` ya existe y es el que usa la demo; su contenido, conteos y condiciones están en [`data/README.md`](../data/README.md) y en [`15-snapshot-dev.md`](15-snapshot-dev.md). Lo que sigue es el contrato de datos que se planteó al inicio del reto, antes de tener datos.

## A obligatorio: TVN RSS + GDELT DOC 2.0
Meta 200 únicos; mínimo 100 y al menos 20 TVN.
Noticias 30 días previos a extracción, ampliables a 90 con cobertura documentada.
GDELT máximo 250 por consulta; dividir por fecha y deduplicar URL.
noticias.csv y fuentes.json; no exigir cuerpos ni videos.

## B obligatorio: Banco Mundial
PAN, CRI, COL, DOM, MEX, GTM. 2010–2024.
NY.GDP.MKTP.KD.ZG (PIB), FP.CPI.TOTL.ZG (inflación), SL.UEM.TOTL.ZS (desempleo), SP.POP.TOTL (población), IT.NET.USER.ZS (internet), NE.EXP.GNFS.ZS (exportaciones/PIB).
1.350 combinaciones, no 1.350 valores válidos; conservar nulos.
Documento indica CC BY 4.0 general salvo excepciones; registrar condiciones por indicador.

## Opcionales
USGS: 2024, latitud 5–12, longitud -86 a -76, magnitud mínima 3; todos los eventos devueltos. Caja regional no es territorio de Panamá. No sustenta inundaciones o pérdidas.
SBP: doce informes mensuales disponibles; extensión bancaria fuera del MVP.

## Campos mínimos
- noticias.csv: id_noticia, titulo, url, medio, idioma, fecha_publicacion, fecha_deteccion, fecha_extraccion, tema, origen, alcance_texto.
- indicadores.csv: pais_iso3, indicador_id, anio, valor nullable, unidad, fuente_url, fecha_extraccion, licencia.
- eventos.geojson (si aplica): id, magnitude, time, updated, longitude, latitude, depth, place, status, URL del evento.
- fichas.jsonl: id_caso, modalidad, ids_fuente, afirmaciones, citas, puntaje, componentes, estado_evidencia, borrador, estado_revision.
- manifest.json: versión, fecha_corte_UTC, consultas, cantidad por archivo, licencia/condiciones, SHA-256, transformaciones.
Acordar estructura de campos compuestos; añadir responsable y registro de revisión.

## Integridad
UTF-8, IDs estables, ISO 8601 UTC; hora Panamá en UI.
seendate GDELT es detección, no publicación.
Conservar nulos y unidades; no reemplazar ausencias con cero.
Cita = ID + campo/pasaje/página realmente sustentante.
raw/, processed/, diccionario, consultas, revisiones y registros excluidos.
Si hay restricciones, entregar metadatos y receta, no contenido protegido.

## Ambigüedad pendiente
Filtro sección 7 [2024-01-01, 2025-10-01) contradice su aplicación universal a 2010–2024 y noticias recientes. Consultar organización; no recortar silenciosamente.
