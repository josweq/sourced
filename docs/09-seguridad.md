# Seguridad y derechos
Plan, no controles ya verificados.
- Estados: nuevo, en revisión, requiere evidencia, aprobado como borrador, descartado. Registrar responsable/corrección. No publicar.
- Citas: validar IDs y sustento, abstenerse sin información.
- Inyección: fuentes como datos; no ejecución de órdenes, acceso a secretos ni cambio de reglas.
- Privacidad: sin perfiles sensibles ni datos reales de clientes.
- Reputación: acusaciones atribuidas como declaraciones.
- Derechos: condiciones por fuente; no redistribuir artículos/imágenes/videos sin permiso.
- Credenciales: fuera de código, logs y Notion; ejemplo sin secretos.
- Acceso: repo privado inicialmente; Notion participantes/jurado autorizados.
- Evaluación: sintéticos separados; respuestas reservadas fuera del desarrollo.
- No inferir verdad, causalidad, fraude, pérdidas, audiencia o rentabilidad a partir de volumen/tono.
Registrar riesgo, responsable, control y prueba en Notion.

## Auditoría de seguridad (2026-10-08)
Revisión OWASP Top 10 / CWE Top 25 sobre el código y el servidor vivo, con peticiones de prueba (incluidas maliciosas). Resultado: **0 críticos, 0 altos**; riesgo 11/100.

| ID | Severidad | Hallazgo | Corrección | Prueba |
|---|---|---|---|---|
| CN-001 | Media | Sin validar `Host`: una página con DNS rebinding podía leer la agenda | `host_ok()` en GET/POST/PUT: solo `127.0.0.1:<puerto>` y `localhost:<puerto>` | `test_host_ajeno_se_rechaza` |
| CN-002 | Media | El guardián solo miraba palabras de 4+ letras: aceptaba «no reduce» o «10 mil» sin respaldo | Negaciones y multiplicadores cortos deben estar en la evidencia citada | `test_rechaza_negacion_y_multiplicador_sin_respaldo` |
| CN-003 | Baja | Cuerpo `[]` o número cortaba la conexión | `leer_json`: objeto JSON obligatorio, tamaño acotado | `test_cuerpo_que_no_es_objeto_o_no_es_json_responde_400` |
| CN-004 | Baja | Sin timeout de socket | `Handler.timeout = 15` | — |
| CN-005 | Baja | Se aceptaba cuerpo sin `application/json` | Tipo de contenido obligatorio | misma prueba que CN-003 |
| CN-006 | Baja | Lista corta de instrucciones prohibidas | Ampliada (olvida, ignore, disregard, override…) | pruebas de inyección existentes |
| CN-007 | Baja | Algunos errores devolvían texto interno de Python | Mensajes propios; errores del modelo → 502 genérico | misma prueba que CN-003 |

Sin hallazgos: SQL (todo parametrizado), path traversal (12 variantes → 404), XSS (todo pasa por `esc()`), secretos (ni en HEAD ni en el historial), archivos pesados, recursos externos del front (CSP `default-src 'self'`). Pendiente declarado: `pip-audit` no se ejecutó en esta máquina y `requirements.txt` fija versiones pero no hashes.
