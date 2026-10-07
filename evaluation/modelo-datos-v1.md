# Verificación del contrato v1
Fecha: 2026-10-07.
Comando: python -m unittest discover -s tests -p "test_*.py" -v.
Resultado observado: 22 pruebas, 22 correctas.
Incluye persistencia SQLite, rechazo de sobrescritura, referencias cruzadas, citas ausentes, fechas inválidas, nulos, secuencia de revisión y duplicados.
El primer intento encontró un problema de permisos del directorio temporal de Windows; se cambió la ubicación temporal de la prueba al directorio tests/ y se repitió correctamente.
No son resultados del benchmark oficial, ni de IA, ni cumplimiento completo de T01–T10.
Datos usados: tests/fixtures/synthetic/modelo-v1.json, todos sintéticos.
