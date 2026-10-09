# Alternativas de búsqueda con IA local · evaluación medida

Fecha: 2026-10-08 · base `demo-20261008T184723Z.sqlite` (snapshot `real-20261007b`, 284 titulares) · mismo banco de 40 preguntas para todas las variantes (`evaluation/benchmark/`). Todo corre en la laptop, sin red.

## Resultado medido

| Variante | Aciertos | Abstención correcta (sin respuesta) | Citas | Latencia mediana | Recursos | Evidencia |
|---|---:|---:|---:|---:|---|---|
| Palabras clave (línea base original) | 35/40 | 4/7 | 100 % | 16 ms | ninguno | `resultados/benchmark-20261008T205856Z-lexico.md` |
| **BM25** (Okapi, sin IA) | 36/40 | 4/7 | 34/34 | 19 ms | ninguno; Python puro | `resultados/benchmark-20261009T001433Z-bm25.md` |
| **Embeddings locales** (multilingual-e5-small) · **la que usa la app** | **37/40** | **7/7** | 33/33 | 84 ms | modelo de ~470 MB, CPU, vectores en SQLite | `resultados/benchmark-20261008T205820Z.md` |
| **Híbrida BM25 + embeddings** (fusión RRF, k=60) | 37/40 | 7/7 | 33/33 | 178 ms | los dos anteriores | `resultados/benchmark-20261009T001544Z-hibrido.md` |

Cómo repetirlo: `python scripts/evaluar_benchmark.py --db <base> --modo {lexico|bm25|semantico|hibrido}`. BM25 está en `src/ia/consulta.py` (`_bm25`, con pruebas en `tests/test_bm25.py`); la interfaz sigue usando `semantico`.

**Lectura.** BM25 mejora en una pregunta a las palabras clave, pero sigue respondiendo cuando no debe (oro en Bolivia, elecciones en Japón, clásico Real Madrid–Barcelona): 4/7. Los embeddings son los que aprenden a **no inventar** (7/7). La híbrida empata con la semántica en este banco y tarda el doble, así que hoy no aporta; con titulares de 10–15 palabras casi no hay términos raros que BM25 pueda rescatar.

## Grafo de conocimiento local (entidades)

| | Evaluación |
|---|---|
| Viabilidad | Media. Extraer entidades (personas, instituciones, lugares, cifras) con un modelo NER local en español (~40–550 MB según el modelo) es rápido; extraer **relaciones** con llama3.2:3b cuesta ~60–90 s por llamada en CPU, horas para 284 titulares |
| Valor | Filtros por institución o lugar, «quién dijo qué», unir casos por entidad además de por similitud |
| Riesgo | Una relación mal extraída es una afirmación sin fuente: cada arista tendría que pasar por el guardián con su cita |
| Velocidad de implementación | Días, no horas, si se hace con verificación |

## Recomendación

1. **Para este entorno sin conexión, la base correcta es la que ya está: embeddings locales.** Es la que mejora lo que importa en una redacción (abstenerse en vez de inventar) con un costo bajo (~470 MB, ~84 ms).
2. **Siguiente paso: híbrida, pero cuando haya texto.** BM25 rinde con documentos largos (nombres propios, siglas, cifras exactas). Con el cuerpo de la nota autorizado, la fusión RRF ya implementada es el primer cambio a activar y medir.
3. **Grafo de entidades después**, empezando por NER (sin relaciones) para filtros y para unir casos, y con cada entidad citada.

## Texto completo de las noticias

Cada noticia ya guarda su enlace (284/284 con URL en la base) y la ficha lo muestra («abrir titular»). Lo que **no** se guarda es el cuerpo, a propósito: las bases del reto piden usar los metadatos de TVN y reutilizar extractos o contenido completo solo con condiciones aplicables o autorización explícita del patrocinador, y no redistribuir artículos sin permiso. Por eso los casos quedan «insuficiente»: es la conclusión correcta con titulares, no una falla.

Camino propuesto, una vez autorizado: un **modo de lectura autorizada** que descargue el cuerpo solo de las fuentes con permiso, lo guarde en la base local (`data/local/`, nunca en el repositorio), lo trocee en pasajes con su ID, y deje que el guardián cite pasajes. Con eso la evidencia de un caso puede subir a «suficiente para borrador» y la búsqueda híbrida empieza a rendir.
