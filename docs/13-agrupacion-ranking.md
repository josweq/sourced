# Agrupación y ranking baseline v1

Estado: baseline determinista y explicable. Sirve para demostrar el flujo y comparar más adelante con ML/NLP; no cuenta como uso sustantivo de IA.

## Agrupación

1. Normaliza mayúsculas, acentos, puntuación y palabras funcionales.
2. Compara títulos dentro de la misma categoría mediante Jaccard de tokens.
3. Agrupa contra el primer título representativo cuando la similitud es al menos 0.55.
4. Conserva cada publicación y su URL.
5. Cuenta como procedencia únicamente el campo `origen` declarado; medio y semejanza no prueban independencia.

Es un baseline sencillo. Puede fallar con paráfrasis, títulos cortos o eventos parecidos. El método codicioso y el umbral se deben comparar con etiquetas humanas antes de adoptar decisiones editoriales.

## Ranking

Usa la fórmula sugerida `P = 30R + 25I + 20U + 15N + 10E` bajo la versión `baseline-titulos-v1`.

| Componente | Regla inicial | Límite reconocido |
|---|---|---|
| R | 0.60 si hay tema editorial; 0.20 sin clasificar | No demuestra relación con Panamá. |
| I | Valor inicial por categoría entre 0.30 y 0.70 | Requiere juicio editorial y datos de alcance. |
| U | Edad respecto al corte: 1.00/0.75/0.50/0.25/0.10; sin fecha 0.20 | Una fecha reciente no implica importancia. |
| N | 0.50 fijo | Falta historial para medir novedad; duplicados no aumentan el valor. |
| E | 0.25 base + 0.25 por procedencia identificada, máximo 0.75 | Solo hay titular/metadatos; no alcanza evidencia suficiente. |

La interfaz muestra componentes, pesos y explicación. El puntaje ordena atención y no estima verdad, impacto real ni permiso para publicar.

## Casos y evidencias

Cada grupo produce un caso y una evidencia por titular. Con procedencia declarada queda `parcial`; sin ella, `insuficiente`. Nunca asigna `suficiente_para_borrador` a partir de titulares. Tampoco relaciona indicadores automáticamente: esa asociación requiere una regla explícita o revisión humana.

## Ejecutar el recorrido

Primero importe CSV siguiendo [la guía local](12-importador-interfaz.md), y luego:

```sh
python scripts/procesar_agenda.py \
  --input data/local/importacion-demo.sqlite \
  --output data/local/agenda-demo.sqlite
python src/interfaz/app.py --db data/local/agenda-demo.sqlite --port 8765
```

El procesador crea una base nueva y conserva intacta la importación. Rechaza entradas que ya contienen datos derivados y salidas existentes.
