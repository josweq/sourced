# Pruebas automáticas · ejecución final

Fecha: 2026-10-08 · commit base `256b122` · Windows 11, Python 3.12.10.

Comando:

```
python -m unittest discover -s tests -p "test_*.py"
```

Resultado (últimas líneas de la salida, sin editar):

```
sala       urgente/superficie         6.68     4.5  OK
sala       deshabilitado              8.88     4.5  OK
sala       cita                      13.61     4.5  OK
sala       foco/superficie           12.21     3.0  OK
```

Los registros intermedios con otros totales (100, 111, 121) corresponden a etapas anteriores del proyecto; el total vigente es este.
