# Snapshot de desarrollo reproducible

Estado: extractor local para preparar un paquete con la misma forma esperada del snapshot oficial. No reemplaza los datos congelados de la organización.

## Cómo correrlo

Modo reproducible sin red, usando las muestras de prueba:

```sh
python scripts/extraccion/construir_snapshot.py --version dev-001 --salida data/snapshot-dev --offline
```

Salida:

- `data/snapshot-dev/<version>/raw/`: respuestas crudas o muestras copiadas.
- `data/snapshot-dev/<version>/processed/noticias.csv`
- `data/snapshot-dev/<version>/processed/indicadores.csv`
- `data/snapshot-dev/<version>/processed/eventos.geojson`
- `data/snapshot-dev/<version>/processed/fuentes.json`
- `data/snapshot-dev/<version>/processed/manifest.json`
- `data/snapshot-dev/<version>/processed/excluidos.json`

Una versión existente nunca se sobrescribe. La construcción se escribe primero en
una carpeta hermana `<version>.parcial` y solo se renombra a `<version>` al
terminar bien. Si una corrida falla, esa carpeta parcial queda como diagnóstico;
en un reintento se aparta con un sufijo de marca de tiempo y no bloquea la nueva
corrida.

## Qué hace

El extractor usa solo biblioteca estándar de Python. Normaliza URLs, genera IDs estables `N-` con SHA-256, deduplica noticias por URL normalizada y registra duplicados o rechazos en `excluidos.json`.

`noticias.csv` conserva solo titulares y metadatos. Para TVN RSS no copia `description` ni `media:content`. Para GDELT, `seendate` se registra como `fecha_deteccion`; `fecha_publicacion` queda vacía porque GDELT ArtList no la entrega.

`indicadores.csv` completa la cuadrícula explícita de países, indicadores y años del contrato: PAN, CRI, COL, DOM, MEX y GTM; seis indicadores del Banco Mundial; años 2010 a 2024. Esa combinación da 540 filas. El encargo menciona 1.350, pero no se inventan países, indicadores ni años para alcanzar ese número. Los valores ausentes quedan vacíos, nunca en cero.

`eventos.geojson` conserva eventos USGS con `id`, magnitud, tiempos, coordenadas, profundidad, lugar, estado y URL.

`manifest.json` registra versión, fecha de corte UTC, consultas exactas, consultas fallidas, conteos, condiciones por fuente, hashes SHA-256 de los archivos procesados, transformaciones y cobertura temporal efectiva. El filtro temporal ambiguo `[2024-01-01, 2025-10-01)` queda anotado como no aplicado, pendiente de la organización.

## Fallos parciales de red

El cliente HTTP mantiene los errores no recuperables como fallos de la consulta.
Para HTTP 429 y 503 hace hasta cuatro intentos. Si la respuesta trae
`Retry-After`, respeta esa espera; si no, espera 15, 30 y 60 segundos entre
intentos.

GDELT se trata como una fuente tolerante a fallos parciales: si una consulta
agota sus reintentos o devuelve un cuerpo que no es JSON, esa URL se registra en
`manifest.json` bajo `consultas_fallidas` y la extracción continúa con las demás
consultas. La pausa de 6 segundos entre consultas se mantiene. Si GDELT no aporta
noticias válidas, el snapshot puede construirse con las capturas disponibles de
TVN RSS y lo declara en `cobertura_temporal_efectiva.gdelt`.

## Importación

El importador acepta el catálogo real:

```sh
python scripts/importar_csv.py \
  --noticias data/snapshot-dev/dev-001/processed/noticias.csv \
  --indicadores data/snapshot-dev/dev-001/processed/indicadores.csv \
  --fuentes data/snapshot-dev/dev-001/processed/fuentes.json \
  --output data/local/snapshot-dev.sqlite \
  --report data/local/snapshot-dev-reporte.json \
  --snapshot-id SNAPSHOT-DEV \
  --version dev-001 \
  --fecha-corte-utc 2026-10-08T00:00:00Z
```

Sin `--fuentes`, el importador conserva el comportamiento anterior con las dos fuentes temporales `example.invalid`.

## Límites

El RSS de TVN conserva una ventana corta, cercana a un día; por eso el modo completo debe acumular capturas en `raw/tvn_rss/`. GDELT puede repetir notas entre consultas y no entrega fecha de publicación. USGS cubre una caja regional y no prueba daños, inundaciones ni pérdidas. Banco Mundial queda sujeto a condiciones y excepciones por indicador.

Este snapshot usa metadatos. No prueba lectura completa de notas, verdad factual, clasificación temática, generación de borradores ni evaluación T01–T10 completa.

## Reemplazo por el paquete oficial

Cuando llegue el paquete oficial, conservar la misma forma de `processed/`, reemplazar las fuentes crudas por las oficiales, recalcular `manifest.json` y volver a ejecutar:

```sh
python -m unittest discover -s tests -p "test_*.py"
python scripts/importar_csv.py --noticias <oficial>/noticias.csv --indicadores <oficial>/indicadores.csv --fuentes <oficial>/fuentes.json --output data/local/oficial.sqlite --report data/local/oficial-reporte.json --snapshot-id SNAPSHOT-OFICIAL --version <version> --fecha-corte-utc <fecha>Z
```

No aplicar recortes temporales dudosos sin respuesta documentada de la organización.
