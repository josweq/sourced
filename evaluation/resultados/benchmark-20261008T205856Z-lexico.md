# Benchmark de desarrollo — 20261008T205856Z — búsqueda lexico

Base: `demo-20261008T184723Z.sqlite` · 40 preguntas (20 sustentadas, 7 ambiguas/contradicción, 7 sin respuesta, 6 adversariales).
Etiquetado: propuesto por Claude, **revisión humana pendiente**. No incluye el conjunto reservado del jurado.

| Métrica | Resultado |
|---|---|
| Aciertos totales | 35/40 (88 %) |
| Aciertos · sustentada | 18/20 (90 %) |
| Aciertos · ambigua | 4/4 (100 %) |
| Aciertos · contradiccion | 3/3 (100 %) |
| Aciertos · sin_respuesta | 4/7 (57 %) |
| Aciertos · adversarial | 6/6 (100 %) |
| Abstención correcta (sin respuesta) | 4/7 (57 %) |
| Abstención indebida (sustentadas) | 1/20 (5 %) |
| Cobertura de citas | 47/47 (100 %) |
| Latencia mediana / p95 / máx. | 16 / 26 / 34 ms |
| Validez de sustento | Pendiente de revisión humana |

## Fallos

- **B01** (sustentada) «¿Qué se sabe del contrato de laptops para docentes del Meduca?»: no cita ['N-09ff7132e4ca8010']
- **B09** (sustentada) «denuncia de la OIR sobre cambios al sistema de pensiones de la CSS»: estado abstencion (esperado respondida); no cita ['N-53f4e8fda2e04a50']
- **B28** (sin_respuesta) «precio del oro en Bolivia»: estado respondida (esperado abstencion)
- **B29** (sin_respuesta) «resultado de las elecciones en Japón»: estado respondida (esperado abstencion)
- **B34** (sin_respuesta) «resultado del clásico entre Real Madrid y Barcelona»: estado respondida (esperado abstencion)
