# Importador CSV e interfaz local v1

Estado: recorrido funcional con datos sintéticos. No descarga fuentes, no clasifica con IA y no sustituye el snapshot oficial.

## Importar CSV

El importador exige encabezados exactos del PDF, UTF-8 y URLs HTTPS. Procesa cada fila de manera independiente: las válidas entran en SQLite y las rechazadas aparecen en un JSON con archivo, fila, ID y causa. Conserva fechas ausentes y valores nulos. No aplica el filtro temporal ambiguo del reto.

```sh
python scripts/importar_csv.py \
  --noticias tests/fixtures/csv/noticias.csv \
  --indicadores tests/fixtures/csv/indicadores.csv \
  --output data/local/importacion-demo.sqlite \
  --report data/local/reporte-demo.json \
  --snapshot-id DEMO-CSV --version demo-v1 \
  --fecha-corte-utc 2024-06-02T12:00:00Z
```

Los CSV incluidos son inventados. El ejemplo acepta 3 noticias y 2 indicadores; rechaza 5 filas. La fuente temporal `example.invalid` en la tabla `fuentes` se reemplazará al implementar `fuentes.json`; cada registro conserva su URL original.

El importador nunca sobrescribe la base ni el reporte. Si una ejecución debe repetirse, use rutas nuevas o retire manualmente archivos de prueba cuyo destino haya verificado.

## Ejecutar la interfaz

Para abrir la agenda generada desde CSV, procese la importación con el [baseline explicable](13-agrupacion-ranking.md):

```sh
python scripts/procesar_agenda.py --input data/local/importacion-demo.sqlite --output data/local/agenda-demo.sqlite
python src/interfaz/app.py --db data/local/agenda-demo.sqlite --port 8765
```

Abrir `http://127.0.0.1:8765`. El servidor solo escucha en localhost. Permite:

- consultar la agenda y distinguir estado de evidencia y revisión;
- inspeccionar puntaje, componentes, publicaciones y procedencias;
- abrir fuentes, fechas, limitaciones y citas por afirmación;
- ver el borrador sintético;
- registrar una nueva revisión humana sin borrar el historial.

No tiene autenticación multiusuario y no debe exponerse a una red. No publica noticias ni llama a Notion. Los casos generados desde CSV no contienen borradores: esa fase sigue pendiente.

## Verificación

```sh
python -m unittest discover -s tests -p "test_*.py" -v
```

Las pruebas cubren contrato, cuarentena por fila, nulos, agenda, detalle y revisión persistente. No equivalen al benchmark oficial ni a todas las pruebas T01–T10.
