# Sistema visual

> **Actualizado el 8-oct-2026:** la paleta azul/lima de este documento fue reemplazada por la identidad Sourced (papel, tinta y resaltador; familia Adobe Source). Ver [docs/marca/README.md](marca/README.md) y `src/interfaz/static/tokens.css`. Las reglas de accesibilidad y las puertas de contraste siguen vigentes.

Estado: D-VIS-01 aprobado para el prototipo local. No usa marca, logo ni azul exacto de TVN.

## Tokens

Los tokens viven en `src/interfaz/static/tokens.css`. El tema por defecto es Redacción: fondo claro, superficies blancas, tinta oscura y primario azul propio `#0b4f7c`. El tema Sala se activa con `[data-tema="sala"]`: fondo oscuro, primario celeste y acento lima `#c9ff68`.

La tipografía está servida desde `src/interfaz/static/fonts/` con `font-display: swap`: Inter para UI, Source Serif 4 para lectura y JetBrains Mono para puntajes, IDs y citas. La escala mínima visible es 13 px; Redacción usa base 14 px y Sala sube a 16 px.

Espaciado: 4, 8, 12, 16, 24, 32 y 48 px. Radios: 6 px para controles y 10 px para tarjetas. Movimiento: 180 a 220 ms, anulado con `prefers-reduced-motion: reduce`.

## Reglas

- Ningún estado se comunica solo por color: todos llevan icono y texto.
- La agenda muestra primero puntaje, nivel, evidencia, publicaciones, fuentes y hora de Panamá.
- Las horas se rotulan como Publicado o Detectado y se muestran en UTC−5 fijo, con UTC en `title`.
- Los bloques sin datos se muestran deshabilitados con explicación; no se inventa contenido.
- El resaltado de citas usa fondo sobre el texto, apto para varias líneas.
- Los controles tienen foco visible de 2 px con separación y áreas de clic mínimas de 24 px.
- La interfaz evita desbordamiento horizontal en móvil con una sola columna y pestañas.

## Puerta de contraste

Ejecutar:

```sh
python scripts/check_contraste.py
```

La puerta lee `tokens.css`, evalúa pares explícitos en Redacción y Sala, exige 4,5:1 para texto y 3:1 para foco/borde, imprime una tabla y sale con código distinto de cero si algo falla.
