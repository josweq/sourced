# Contratos compartidos propuestos
Estado: borrador v0 para discusión, no API implementada ni schema validado.
Los campos mínimos de archivos del reto están en ../docs/04-datos.md.

## Objetos de integración
- Evidencia: ID estable, tipo/fuente, URL, fechas separadas, alcance_texto, localizador de campo/pasaje/página y contenido disponible.
- Afirmación: ID, texto, tipo (hecho/declaración/inferencia/hipótesis) y citas que la sustentan.
- Grupo: ID de evento, IDs miembros, procedencias identificadas y procedencias desconocidas. Número de publicaciones separado de fuentes independientes.
- Caso: campos mínimos de fichas.jsonl, verificaciones pendientes y versión de reglas.
- Revisión: ID de caso, persona revisora, fecha UTC, estado anterior/nuevo, comentario y corrección.
- Reporte de carga: versión de snapshot, totales aceptados/excluidos, errores por fila/campo y nulos conservados.
- Respuesta: consulta, evidencias, afirmaciones, vacíos y abstención explícita con motivo.

## Acuerdos requeridos
Nombres/tipos exactos, campos nulos, enumeraciones, esquema JSON, errores y persistencia.
No interpretar estos objetos como sustitutos del contrato oficial de CSV/JSONL.
No añadir contadores de corroboración basados únicamente en número de medios.
Versionar cambios y aportar ejemplos sintéticos cuando se formalice el contrato.
