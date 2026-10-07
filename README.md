# Jajanken Lupa
**Antes de contar una historia, mostramos qué la sostiene.**

Copiloto editorial para el reto TVN Media. Equipo: **Josué, Juanchi y Diego**.
Convierte noticias públicas e indicadores oficiales en agenda priorizada, fichas trazables y borradores para revisión humana.

## Estado real
Base documental y modelo de datos de referencia ejecutable con SQLite. Hay ejemplos sintéticos y pruebas de integridad; el prototipo editorial, datos reales y métricas de IA siguen pendientes. No hay tareas ni roles asignados por persona. El stack de la aplicación sigue abierto.

## Empieza aquí
1. Lee [AGENTS.md](AGENTS.md), también con una IA que no lo cargue automáticamente.
2. Revisa [producto](docs/01-producto.md), [requisitos](docs/02-requisitos.md) y [backlog](docs/06-backlog.md).
3. Usa [la guía para tu IA](prompts/README.md).
4. Trabaja en una rama y abre un PR siguiendo [CONTRIBUTING.md](CONTRIBUTING.md).

## Documentación
- [Producto y demo](docs/01-producto.md)
- [Requisitos y rúbrica](docs/02-requisitos.md)
- [Arquitectura propuesta](docs/03-arquitectura.md)
- [Datos y contratos](docs/04-datos.md)
- [Pruebas y métricas](docs/05-pruebas.md)
- [Backlog sin asignaciones](docs/06-backlog.md)
- [Plantilla de Notion y pitch](docs/07-notion.md)
- [Decisiones y dudas abiertas](docs/08-decisiones.md)
- [Seguridad y derechos](docs/09-seguridad.md)

## Flujo
Snapshot → validación → organización → contexto → ranking → ficha → borrador → revisión humana → Notion.

## Reglas esenciales
Notion es obligatorio para ejecutar, documentar y presentar; GitHub no lo reemplaza.
No publicar automáticamente. No inventar cifras, citas ni resultados.
Separar prioridad editorial de suficiencia de evidencia.
La demo debe funcionar sin internet con fallback documentado.

## Origen
Plan derivado del PDF de 12 páginas «hackIAthon - reto TVN Media.pdf» facilitado por Diego, cuyas fuentes llevan fecha de consulta 05/10/2026. No se incluye el PDF ni contenido protegido. Confirmar reglas definitivas y snapshot con organización.

## Estructura compartida
Consulta [el mapa de módulos](docs/10-estructura.md), [los contratos propuestos](contracts/README.md) y [las plantillas](templates/tarea.md). src/, tests/ y evaluation/ preparan la organización; no son un producto ejecutable.

## Restricción vigente
**No acceder, subir, crear, editar ni sincronizar contenido en Notion por el momento.** La plantilla se conserva solo como preparación en GitHub. Nadie tiene tareas asignadas; cada integrante decide qué explorar con su IA.

## Probar el modelo de datos
Lee el [modelo y diagrama](docs/11-modelo-datos.md) y el [diccionario](contracts/diccionario.md).
Python 3.10+ con SQLite 3.37+, sin paquetes adicionales:

```sh
python scripts/modelo_datos.py
python -m unittest discover -s tests -p "test_*.py" -v
python scripts/modelo_datos.py --output data/local/modelo-demo.sqlite
```

El último comando crea una base nueva y nunca sobrescribe. Todos los ejemplos son sintéticos. [Resultados y límites de la verificación](evaluation/modelo-datos-v1.md).
