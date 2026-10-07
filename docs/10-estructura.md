# Mapa de la estructura
Estructura neutral respecto al lenguaje. Los directorios contienen límites y documentación; todavía no hay servicios ni pantallas ejecutables.

| Ruta | Contenido previsto | Entrada → salida | Requisitos |
|---|---|---|---|
| src/ingesta/ | Lectura, validación, normalización | Snapshot → registros y reporte | R01–R02 |
| src/evidencia/ | Recuperación, clasificación y agrupación | Consulta/registros → evidencias y grupos | R03–R04, R06, R10–R11 |
| src/priorizacion/ | Puntaje determinista y explicación | Casos/componentes → ranking | R05 |
| src/editorial/ | Borradores sustentados | Evidencias → paquete y vacíos | R07–R08, R12 |
| src/revision/ | Historial humano | Caso/decisión → revisión persistida | R09 |
| src/interfaz/ | Agenda, radiografía y mesa | Casos → recorrido usable | R06–R09 |
| contracts/ | Formatos compartidos propuestos | Documentos de acuerdo | R02, R08–R09 |
| data/ | Snapshot permitido | Originales/procesados | R01, R16 |
| tests/fixtures/ | Ejemplos sintéticos futuros | Casos controlados | R13 |
| evaluation/ | Benchmark desarrollo y resultados reales | Ejecuciones → métricas | R11–R13 |
| templates/ | Registros de decisiones, tareas y pruebas | Trabajo → evidencia | R17–R18 |
| docs/ | Requisitos, diseño y entrega | Contexto compartido | Todos |
| prompts/ | Explorar, implementar y revisar con IA | Contexto → aporte elegido | Colaboración |

## Primer recorrido a construir
Carga de ejemplo sintético identificado → agenda → ficha con cita → borrador señalado → revisión local.
Esto valida integración; no sustituye snapshot, IA real, benchmark ni pruebas de aceptación.

## Antes del código
Acordar stack, forma de ejecución, serialización, almacenamiento e interfaces.
Usar contracts/README.md como punto de acuerdo; proponer cambios pequeños y versionados.
No hay responsable por módulo.

## Estado de Notion
El requisito del reto sigue vigente, pero cualquier operación en Notion está pausada por Diego.
Guardar aquí preparación y evidencias con fechas reales; no afirmar que ya están registradas en Notion.
