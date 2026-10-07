# Diccionario y mapeo v1
Tipos y nulabilidad exactos: [schema.sql](sqlite/schema.sql).
Tablas principales: clave (snapshot_id,id); tablas puente: claves compuestas. Las referencias incluyen snapshot_id.

| Archivo oficial | Destino | Mapeo |
|---|---|---|
| manifest.json | snapshots y archivo original | versión → version, fecha_corte_UTC → fecha_corte_utc; ID estable asignado por importador. Naturaleza explícita. Consultas, conteos, condiciones, SHA-256 y transformaciones permanecen en manifest; importador pendiente. |
| fuentes.json | fuentes | ID, nombre, familia, URL, condiciones y extracción; adaptador pendiente, el PDF no define completamente este JSON. |
| noticias.csv | noticias | id_noticia → id; resto de campos oficiales conservados. fuente_id enlaza catálogo. |
| indicadores.csv | indicadores | Campos oficiales conservados; id interno adicional. Único por snapshot/país/indicador/año. null no se convierte a cero. |
| fichas.jsonl | casos y relaciones | id_caso → id. Afirmaciones, citas, prioridad, borrador y revisión requieren exportador de ensamblaje, pendiente. |
| eventos.geojson | Pendiente | USGS opcional; no forzar eventos sísmicos en noticias/indicadores. |

## Objetos derivados
- grupos + grupo_noticias: evento, miembros y procedencia. procedencia_id identifica origen editorial con justificación, no medio ni recolector por defecto.
- evidencias: noticia O indicador y campo no nulo; dato leído desde su registro para conservar contexto.
- caso_evidencias: evidencias pertinentes a cada caso.
- priorizaciones: versión de reglas, componentes/pesos JSON serializados, puntaje, explicación y fecha.
- borradores: versión por caso, título, enfoque, brief, guion, copy, tres preguntas JSON, alcance, generador, modelo/prompt y fecha.
- afirmaciones: texto dentro de una sección y versión específica; hecho/declaracion/inferencia/hipotesis.
- citas: sustenta/contradice/contextualiza con explicación. Contradicción no cuenta como sustento.
- revisiones: persona, borrador cuando corresponde, secuencia, estado, comentario y fecha.
- estado_casos: última revisión por secuencia; sin revisiones, nuevo.
- procedencias_grupos: publicaciones, procedencias identificadas y origen desconocido. No certifica independencia ni verdad.

## Fechas, IDs y enums
UTC ISO 8601 con Z. Publicación y detección separadas. Fecha ausente → null, no copiar seendate.
IDs estables; en fixtures se usa SYN-. La política de IDs del importador real queda pendiente.
Enums técnicos sin acentos, etiquetas UI en español.
sin_clasificar admite registros aún no procesados por NLP.
texto_disponible nullable; titular_metadatos no autoriza usarlo como pasaje.
Las fechas son TEXT en SQL y se validan en Python; escrituras directas SQL deben ejecutar validaciones equivalentes.
No aplicar el filtro temporal ambiguo del PDF hasta aclararlo.

## Fixture JSON
contract_version: 1.0.0; warning: aviso sintético; tables: colecciones con las columnas SQL.
No sustituye CSV/JSONL oficiales. El loader solo admite naturaleza sintetico, IDs SYN- y URLs example.invalid.

