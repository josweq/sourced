# Datos

Esta carpeta guarda el paquete de datos públicos con el que corre la demo. No hay datos privados de TVN, datos de clientes ni contenido detrás de muros de pago.

## Qué hay aquí

| Ruta | Contenido |
|---|---|
| `snapshot-dev/real-20261007b/processed/` | Snapshot real congelado el 2026-10-08T00:08:55Z (noche del 7 de octubre en Panamá). Es el que usa la demo |
| `raw/`, `processed/` | Reservadas para el paquete oficial de la organización; hoy solo tienen `.gitkeep` |
| `local/` | Bases SQLite que genera cada persona al preparar la demo. No se versiona |

## Archivos del snapshot `real-20261007b`

| Archivo | Registros | Qué contiene |
|---|---|---|
| `noticias.csv` | 284 | Titulares y metadatos de cinco medios panameños: TVN (159), La Prensa (100), Crítica (10), En Segundos (10) y Panamá América (5). Todas las filas llevan `alcance_texto = titular_metadatos` |
| `indicadores.csv` | 540 | Banco Mundial: 6 países (PAN, CRI, COL, DOM, MEX, GTM) × 6 indicadores × 15 años (2010–2024), con unidad, URL de origen y licencia por fila |
| `eventos.geojson` | 82 | Sismos de USGS de 2024 en la caja regional latitud 5–12, longitud −86 a −76, magnitud mínima 3 |
| `fuentes.json` | 8 | Catálogo de fuentes: ID, nombre, familia, URL, condiciones y fecha de extracción |
| `excluidos.json` | 322 | Registros que quedaron fuera al construir el snapshot, con su causa. En este snapshot todos son titulares repetidos (misma URL normalizada); se anotan para que nada se descarte en silencio |
| `manifest.json` | — | Versión, fecha de corte en UTC, consultas exactas, conteos, condiciones por fuente, transformaciones y hash SHA-256 de cada archivo |

El significado de cada campo está en [`contracts/diccionario.md`](../contracts/diccionario.md).

## Cómo comprobar que el snapshot no cambió

`manifest.json` guarda el SHA-256 de los otros cinco archivos. Para recalcularlos:

```sh
# macOS / Linux / Git Bash
sha256sum data/snapshot-dev/real-20261007b/processed/noticias.csv

# Windows PowerShell
Get-FileHash data\snapshot-dev\real-20261007b\processed\noticias.csv -Algorithm SHA256
```

El resultado debe coincidir con el valor de `sha256` en el manifest. Si no coincide, el archivo fue modificado después del corte.

## Derechos y límites

- De los medios solo se guardan titular y metadatos (URL, medio, fechas). No se copian descripciones, cuerpos de artículo, imágenes ni videos. Por eso las capturas crudas del RSS (`raw/`) no se versionan.
- Banco Mundial: CC BY 4.0, con excepciones posibles por indicador. Son cifras anuales; no describen el día de hoy.
- USGS: la caja regional no equivale al territorio de Panamá y solo sustenta hechos sísmicos, no daños ni pérdidas.
- GDELT quedó fuera de este snapshot: respondió HTTP 429 a todas las consultas el 7 de octubre de 2026. Está declarado en `cobertura_temporal_efectiva` del manifest.
- La cuadrícula del Banco Mundial da 540 combinaciones, no las 1.350 que menciona el documento del reto; no se inventaron países, indicadores ni años para alcanzar esa cifra.
- Nunca incluir aquí el benchmark reservado del jurado.

Más detalle: [contrato de datos](../docs/04-datos.md) y [cómo se construye el snapshot](../docs/15-snapshot-dev.md).
