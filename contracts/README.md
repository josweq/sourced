# Contrato de datos v1.0.0
Referencia ejecutable para revisión e integración; no fija el stack final.

- [Modelo y diagrama](../docs/11-modelo-datos.md).
- [Diccionario y mapeo](diccionario.md).
- [SQL normativo de esta referencia](sqlite/schema.sql).
- [Fixture sintético](../tests/fixtures/synthetic/modelo-v1.json).
- [Validador](../scripts/modelo_datos.py) y [pruebas](../tests/test_modelo_datos.py).

Claves por snapshot, UTC, nulos conservados y citas por afirmación. Validaciones adicionales en Python; SQL directo no las sustituye. El JSON de prueba no cambia los archivos oficiales del reto.
Cambios incompatibles requieren nueva versión y migración. Esta versión solo crea bases nuevas.
