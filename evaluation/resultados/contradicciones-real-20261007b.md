# Evaluación T05: contradicciones en datos reales

Comando reproducible (desde la raíz del repo, con la base que imprime `preparar_demo.py`):

```sh
python scripts/evaluar_contradicciones.py --db data/local/demo-<marca>.sqlite
```

Base: `demo-20261008T051225Z.sqlite` (snapshot `real-20261007b`), 2026-10-08.

| Métrica | Valor |
|---|---|
| Casos totales | 275 |
| Casos con dos o más medios | 1 (donación de EE.UU.: Crítica y TVN) |
| Cifras extraídas de los titulares | 44 |
| Casos con cifras incompatibles | 0 |

**Lectura honesta:** en el snapshot real no hay ninguna contradicción. El único caso con dos medios dice «$500 mil» y «$500,000», que son la misma cifra (control negativo: no se marca). La detección se ejerce con un par sintético marcado `SYN` ($500 mil frente a $5 millones) en `tests/test_contradicciones.py`.

**Auditoría del extractor (2026-10-08):** la primera versión tomaba fechas como conteos («7 de octubre» → 7 «de») y «sismo con 53 muertos» como magnitud 53; se corrigió (51 → 36 titulares con cifras, 60 → 44 cifras) y quedó una prueba de regresión con esos titulares reales.

Límite: solo titulares y metadatos; no se leyó el cuerpo de la nota ni la fuente primaria.
