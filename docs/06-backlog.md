# Backlog compartido, sin asignaciones
Ninguna tarea está asignada a Josué, Juanchi o Diego. Cada integrante puede explorar opciones con su IA y elegir dónde aportar. Revisar una tarea no implica asumirla.

Estados: disponible para explorar / pendiente de decisión / depende de datos / pendiente de implementación / preparado / pausado.
No confundir documentos preparados con funcionalidades implementadas.

| ID | Trabajo | Estado | Dependencias | Evidencia de terminado |
|---|---|---|---|---|
| B01 | Base documental GitHub | Preparado | Ninguna | Documentación navegable y guías comunes |
| B02 | Aclarar calendario y filtro temporal | Disponible para explorar | Respuesta organización | Respuestas con fuente y fecha |
| B03 | Snapshot y catálogo | Snapshot de desarrollo preparado; datos oficiales pendientes | Paquete común y condiciones | `scripts/extraccion/`, `docs/15-snapshot-dev.md`, archivos procesados con hashes y catálogo `fuentes.json` |
| B04 | Ingesta y validación | Importador con catálogo opcional preparado | B03 para datos reales | CSV por fila, reporte, pruebas y carga con `--fuentes`; snapshot oficial pendiente |
| B05 | Stack e interfaces | Modelo de datos v1 preparado; stack de aplicación pendiente | Hardware y acuerdo técnico | Contrato SQLite de referencia y pruebas; integración pendiente |
| B06 | Etiquetas y baseline | Búsqueda por palabras clave v1 preparada; evaluación real pendiente | B03 para evaluación real | Método, etiquetas y salidas |
| B07 | Recuperación y agrupación | Baseline léxico preparado; NLP pendiente | B03/B06 para evaluación real | Comparar baseline con IA y etiquetas humanas; T02/T03 pendientes completos |
| B08 | Ranking explicable | Baseline v1 preparado | Revisión editorial y datos reales | Reglas/componentes visibles; validar utilidad y T08 completo |
| B09 | Agenda y ficha | Primera interfaz local preparada | Datos derivados/casos reales pendientes | Agenda, citas, fechas y revisión con fixture sintético |
| B10 | Generación sustentada | Pendiente de implementación | B07 y contratos | Brief, guion, copy; T04–T07/T09 |
| B11 | Revisión persistente | Disponible para explorar | Contrato de caso y B05 | Estados y responsable de revisión |
| B12 | Cinco casos | Depende de datos | Flujo integrado y B03 | Incluye evidencia insuficiente |
| B13 | Fallback offline | Disponible para explorar | Hardware; flujo para ejecutar T10 | Plan y ensayo sin red |
| B14 | Evaluación final | Pendiente de implementación | B06–B13 | T01–T10, métricas y correcciones |
| B15 | Entrega y pitch | Disponible para explorar | B14 para resultados finales | Guion, README ejecutable y accesos |
| B16 | Organizar Notion | Pausado por Diego | Autorización posterior explícita | Ocho secciones y accesos verificados |

## Cómo escoger un aporte
1. Leer requisitos y mapa de módulos.
2. Pedir a la IA dos o tres aportes posibles según experiencia e interés, con dependencias.
3. Elegir personalmente una tarea; comprobar que nadie ya la está trabajando.
4. Registrar la elección voluntaria en una issue o PR. No asignar a otras personas.
5. Trabajar en rama pequeña; dejar decisiones, verificación y pendientes.

Mientras no haya elección, las tareas siguen sin responsable. No crear asignaciones automáticas.
