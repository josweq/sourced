# Pruebas

Pruebas automáticas con `unittest`, la biblioteca estándar de Python. Desde la raíz del repositorio:

```sh
python -m unittest discover -s tests -p "test_*.py"
```

Agregar `-v` muestra el nombre de cada prueba. No necesitan internet ni claves. Una prueba de `test_capa_ia.py` se omite sola si el modelo de embeddings todavía no está descargado; se activa después de correr `python scripts/preparar_modelos.py`.

## Qué cubre cada archivo

| Archivo | Qué comprueba | Pruebas del reto relacionadas |
|---|---|---|
| `test_modelo_datos.py` | Contrato del modelo de datos; por ejemplo, que el estado «publicado» no existe | T08 |
| `test_importador.py` | Carga de CSV con cuarentena de filas inválidas y nulos conservados | T01 |
| `test_extraccion.py`, `test_rss_medios.py` | Extractores del snapshot con muestras guardadas, sin red | — |
| `test_agenda.py` | Agrupación y ranking de la línea base | T02 |
| `test_busqueda.py` | Búsqueda editorial y abstención cuando no hay caso sustentado | T06 |
| `test_capa_ia.py` | Embeddings, clasificador de tema y agrupación semántica | T02 |
| `test_consulta.py` | Preguntas en español con cita, o abstención; la cifra anual no se presenta como de hoy | T04, T06 |
| `test_contradicciones.py` | Cifras incompatibles entre medios: se muestran ambas, no se elige una | T05 |
| `test_redaccion_guardian.py` | Borrador con citas y guardián frente a instrucciones maliciosas en una fuente | T07, T09 |
| `test_formatos.py`, `test_generar_version.py` | Formatos editoriales y «Generar versión» | T09 |
| `test_interfaz.py` | Servidor local y sus respuestas, incluidas las peticiones que debe rechazar | — |
| `test_check_sin_red.py` | La puerta estática sin red pasa sobre el repo y falla cuando se le mete una salida a la red | T10 |
| `test_contraste.py` | Contraste de los colores de la interfaz | — |

## Datos de prueba

Todo lo que hay en `fixtures/` es de prueba: `fixtures/synthetic/` y `fixtures/csv/` son inventados (URLs `example.invalid`, titulares marcados como sintéticos) y `fixtures/extraccion/` son muestras pequeñas con la forma de cada fuente. No son el snapshot real ni cuentan como fichas del reto.

## Resultados

La matriz de aceptación con lo observado en cada prueba está en [`evaluation/matriz-T01-T10.md`](../evaluation/matriz-T01-T10.md): T01 a T10 cumplen. El plan original de pruebas y métricas está en [`docs/05-pruebas.md`](../docs/05-pruebas.md).
