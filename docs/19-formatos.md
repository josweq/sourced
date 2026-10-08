# Adaptación a formatos

Estado: implementación local acotada para la entrega del 8 de octubre.

## Qué hace

`src/editorial/formatos.py` adapta un paquete de borrador citado a cinco salidas:

- `tv`: guion de referencia 45-60 s, compatible con el cronómetro actual.
- `radio`: guion breve de 30 s.
- `vertical`: video vertical de 60 s en tres bloques: `Lo que se reporta`, `Qué se sabe` y `Qué falta verificar`, con marcas aproximadas 0-5 s, 5-45 s y 45-60 s.
- `web`: nota breve de hasta 250 palabras con subtítulos `Qué se reporta`, `Contexto` cuando hay indicador citado y `Qué falta verificar`.
- `alerta`: texto de hasta 140 caracteres con el hecho atribuido, sin adjetivos.

La adaptación no llama al modelo y no guarda nada. La API `POST /api/borradores/{id}/adaptar` devuelve la versión adaptada; si la persona la acepta, el `PUT /api/borradores/{id}` existente la guarda como versión nueva.

## Límites

La función solo reordena, recorta y empaqueta afirmaciones que ya tienen `evidencia_id` y `campo`. Cada oración candidata vuelve a pasar por el guardián determinista; si una oración queda sin cita, cita evidencia ajena, introduce cifras o usa términos sin respaldo, sale en `retiradas` con motivo.

`duracion_s` solo reduce cuántas afirmaciones entran, priorizando las primeras según el énfasis. No se rellena texto para llegar al tiempo.

Los avisos `Borrador generado por IA — requiere revisión humana` y `Basado únicamente en titular/metadatos` se devuelven como avisos de presentación, no como afirmaciones factuales.

## Énfasis y tono

`enfasis=noticia` abre con la afirmación principal. `enfasis=dato` abre con el indicador oficial citado cuando existe; si no existe, lo declara en avisos y abre con la noticia. `enfasis=verificacion` abre con lo que falta verificar, citado contra la primera evidencia del paquete para que el guardián lo controle.

`tono=sobrio` mantiene las afirmaciones tal cual. `tono=explicativo` solo agrega conectores didácticos por código sobre lo ya citado; el guardián puede retirarlos si no sobreviven.

## Por qué no hay control de gravedad

No existe selector de gravedad ni tono urgente porque el reto prohíbe empujar sensacionalismo. La gravedad se expresa como contexto verificable: prioridad editorial, estado de evidencia, suficiencia de citas y pendientes de verificación. El formato cambia la estructura, no la verdad ni la intensidad del caso.
