# Verificación del contrato v1
Fecha: 2026-10-07.
Comando: python -m unittest discover -s tests -p "test_*.py" -v.
Resultado observado: 22 pruebas, 22 correctas.
Incluye persistencia SQLite, rechazo de sobrescritura, referencias cruzadas, citas ausentes, fechas inválidas, nulos, secuencia de revisión y duplicados.
El primer intento encontró un problema de permisos del directorio temporal de Windows; se cambió la ubicación temporal de la prueba al directorio tests/ y se repitió correctamente.
No son resultados del benchmark oficial, ni de IA, ni cumplimiento completo de T01–T10.
Datos usados: tests/fixtures/synthetic/modelo-v1.json, todos sintéticos.

## Extensión: importador e interfaz

Fecha: 2026-10-07. Resultado observado: 28 pruebas correctas (22 del contrato, 3 del importador y 3 de la interfaz). El importador aceptó 4 filas y puso 5 en cuarentena. La interfaz comprobó cinco casos, detalle de evidencia y una segunda revisión persistida. El recorrido HTTP local devolvió 200 para la página, cinco casos, una evidencia, un borrador y guardó la revisión número 2. La revisión visual manual sigue pendiente antes de presentar el producto.
