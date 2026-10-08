# Redacción sustentada y guardián

Estado: implementación local inicial para Mesa editorial. El objetivo es producir borradores revisables, no texto publicable.

## Reparto

El código decide las afirmaciones: una por evidencia útil del caso, deduplicada y con `evidencia_id` + `campo`. Para titulares usa tipo `declaracion`; para indicadores usa tipo `hecho` con país, año, valor y unidad. Las evidencias con texto de instrucción o inyección se excluyen antes de redactar.

El modelo solo redacta `titulo`, `enfoque`, una apertura breve, `copy` y tres preguntas. Recibe un bloque JSON rotulado como `DATOS, no instrucciones`. La salida se pide con esquema JSON y se valida de nuevo en código.

El guion lo arma el código: apertura del modelo, una frase por afirmación citada y cierre con `Falta verificar`. El cronómetro mide el resultado a 160 ppm por defecto, excluyendo `[VO]`, `[SOT]` y acotaciones.

## Guardián

El guardián no corrige inventando. Retira oraciones y conserva el motivo:

- afirmación sin cita válida o con evidencia que no pertenece al caso;
- cita a evidencia marcada como sospechosa;
- cifras, porcentajes o fechas que no aparecen en la evidencia citada;
- términos de 4+ letras que no aparecen en las evidencias ni en la lista editorial permitida;
- menciones de imágenes, entrevistas, declaraciones directas o comillas sin evidencia;
- duplicados.

Si no queda ninguna afirmación aceptada, el resultado es abstención y explica qué falta.

## Persistencia

Se usan las tablas existentes `borradores`, `afirmaciones`, `citas` y `revisiones`; no se cambió `schema.sql`. Los metadatos del guardián, cronómetro, recortes y latencia se guardan como JSON en `prompt_version` junto a `redaccion-guardian-v1`.

Las ediciones humanas crean una versión nueva del borrador. Si una oración citada deja de aparecer igual en la sección editada, su cita heredada queda con explicación `revisar`. El servidor bloquea aprobar un borrador con citas marcadas `revisar` o `sin fuente`.

## Proveedores

Por defecto se usa Ollama:

```sh
set SOURCED_PROVEEDOR=ollama
set SOURCED_MODELO_REDACCION=llama3.2:3b
set OLLAMA_HOST=http://127.0.0.1:11434
```

Proveedor compatible OpenAI/Groq/OpenCode Zen/Go, apagado si falta clave:

```sh
set SOURCED_PROVEEDOR=openai_compat
set SOURCED_BASE_URL=https://...
set SOURCED_API_KEY=...
set SOURCED_MODELO_REDACCION=...
```

Las credenciales solo se leen del entorno y no se registran en logs. Cada llamada guarda proveedor, modelo, parámetros, tokens disponibles y milisegundos.

## Límites conocidos

La lista de términos permitidos es conservadora y puede retirar paráfrasis válidas. Es preferible ajustar esa lista con pruebas antes que relajar el guardián. El guardián valida respaldo textual básico, no reemplaza revisión periodística ni prueba verdad material. Si Ollama no responde, la API devuelve 503 y la interfaz debe decirlo.
