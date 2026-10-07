# Verificación del contrato v1
Fecha: 2026-10-07.
Comando: python -m unittest discover -s tests -p "test_*.py" -v.
Resultado observado: 22 pruebas, 22 correctas.
Incluye persistencia SQLite, rechazo de sobrescritura, referencias cruzadas, citas ausentes, fechas inválidas, nulos, secuencia de revisión y duplicados.
El primer intento encontró un problema de permisos del directorio temporal de Windows; se cambió la ubicación temporal de la prueba al directorio tests/ y se repitió correctamente.
No son resultados del benchmark oficial, ni de IA, ni cumplimiento completo de T01–T10.
Datos usados: tests/fixtures/synthetic/modelo-v1.json, todos sintéticos.

## Extensión: importador e interfaz

Fecha: 2026-10-07. En esa versión se observaron 28 pruebas correctas (22 del contrato, 3 del importador y 3 de la interfaz). El importador aceptó 4 filas y puso 5 en cuarentena. La interfaz comprobó cinco casos, detalle de evidencia y una segunda revisión persistida. El recorrido HTTP local devolvió 200 para la página, cinco casos, una evidencia, un borrador y guardó la revisión número 2. Esta medición histórica fue ampliada por la prueba de agenda descrita abajo.

## Extensión: agenda baseline

Fecha: 2026-10-07. Resultado observado: 32 pruebas correctas. El flujo CLI aceptó 3 noticias y 2 indicadores, rechazó 5 filas, agrupó dos titulares económicos en un caso y dejó el titular turístico como otro. Los puntajes fueron 63.00 y 45.75. La prueba HTTP devolvió 200, dos casos ordenados, dos publicaciones, una procedencia identificada, dos evidencias y guardó la primera revisión del caso generado. No se relacionaron indicadores automáticamente. Esto demuestra el baseline y la integración, no calidad NLP, utilidad editorial ni cumplimiento completo de T02/T08.
