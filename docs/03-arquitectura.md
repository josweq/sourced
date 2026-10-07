# Arquitectura propuesta
Stack y proveedores pendientes, no hay implementación.
Carga por lote → validación → almacenamiento local → recuperación/agrupación → ranking determinista → generación sustentada → interfaz → revisión → Notion.

## Responsabilidades propuestas
- load_snapshot: registros y reporte de calidad.
- retrieve: evidencias con IDs y localizadores.
- group_events: grupos, miembros y procedencias conocidas/desconocidas.
- rank: puntaje, componentes, explicación y versión.
- generate: afirmaciones, citas, vacíos y paquete editorial.
- review: decisión humana persistida.
Acordar contratos exactos antes de integrar.

## IA y baseline
Comparar recuperación semántica con búsqueda por palabras clave, mismo corpus y etiquetas humanas. No afirmar mejora antes de medir.

## Offline
Evaluar modelo local según hardware o recuperación local con generación conservadora por plantillas sustentadas. Mantener una capacidad ML/NLP real.
Salidas precalculadas deben etiquetarse, no fingir generación en vivo.
Guardar revisión local y documentar registro posterior en Notion; confirmar contingencia con organización.
Notion manual inicialmente; automatización opcional.

## Pendiente
Lenguaje/framework, modelo, almacenamiento, hardware y presupuesto. Evitar complejidad innecesaria.
