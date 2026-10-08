# Presentación · Pitch Day

![Sourced](../marca/logo-completo.png)

## Nada sin fuente.
Copiloto editorial para la redacción de TVN · Equipo **Jajanken** · hackIAthon Panamá 2026 · Reto «De la señal a la decisión»

---

# 1 · El problema

> **Que una noticia circule no significa que esté confirmada.**

- Cinco medios repiten la misma nota y **parece** verificada.
- Un dato de 2024 se lee como si fuera **de hoy**.
- Con prisa, una IA generativa **rellena** con cifras que nadie dijo.

El problema no es escribir más rápido. Es **saber qué sostiene cada cosa antes de contarla**.

---

# 2 · Qué es Sourced

> Un copiloto editorial que separa siempre dos preguntas: **¿qué tan importante es?** y **¿qué tan respaldado está?**

- Agenda priorizada que explica el porqué de cada tema.
- Borradores donde **cada oración lleva su cita**.
- Cuando no hay evidencia, **lo dice**.
- Corre en una laptop: **sin internet, sin GPU, sin claves, costo cero por uso**.

![Sourced con datos reales](../../verificacion/capturas/sourced-escritorio.png)

---

# 3 · Con datos reales del 7 de octubre

| 284 | 5 | 540 | 82 |
|---|---|---|---|
| titulares | medios panameños | valores oficiales del Banco Mundial | sismos de USGS |

TVN · La Prensa · Crítica · Panamá América · En Segundos — solo titular y metadatos, en un snapshot con huella SHA-256.

---

# 4 · Dos medios no son dos fuentes

> Crítica y TVN publican la misma donación de EE.UU. Sourced las une en **un caso**… y la evidencia sigue **insuficiente**: ninguno declara de dónde sale el dato.

![Un hecho, dos medios](../../verificacion/capturas/sourced-dos-medios.png)

---

# 5 · La nota que pides, sin inventar

> Formato, duración, palabras, tono, enfoque y público: **eliges solo lo que quieres**. Sourced arma las instrucciones, el modelo redacta y un guardián revisa cada oración.

**Si la evidencia no alcanza, no rellena:** «alcanza para ~16 palabras; para llegar a 30 s hace falta la fuente primaria».

![Generar versión](../../verificacion/capturas/sourced-generar-version.png)

---

# 6 · Responde con cita… o no responde

| «¿Cuál es la inflación de Panamá hoy?» | «Precio del oro en Bolivia» |
|---|---|
| Panamá, 2024: 0,7 %. Dato anual del Banco Mundial; **no es una medición actual**. | **Me abstengo:** no hay evidencia en el snapshot. |

![Cifra oficial con aviso](../../verificacion/capturas/sourced-cifra-oficial.png)

---

# 7 · La IA, medida

| | Sourced | Búsqueda por palabras clave |
|---|---|---|
| Aciertos (40 preguntas) | **37/40** | 35/40 |
| Se abstiene cuando no hay respuesta | **7/7** | 4/7 |

| Clasificación de tema (284 etiquetas revisadas por el equipo) | Macro-F1 |
|---|---|
| Entrenada con etiquetas humanas | **0,45** |
| Reglas | 0,26 |

> Las palabras clave, sin evidencia, citan «el precio del clientelismo» para el precio del oro. **Una cita equivocada es peor que una abstención.**

---

# 8 · Confiable de punta a punta

- **10/10** pruebas de aceptación del reto (T01–T10).
- **Sin internet de verdad:** probado con el Wi-Fi cortado — 0 de 52 intentos salieron a la red.
- **Seguridad:** auditoría OWASP/CWE con 0 hallazgos críticos o altos; el resto, corregido.
- **125** pruebas automáticas · instalación probada desde cero en otro entorno.
- **Nada se publica solo:** el máximo estado es «aprobado como borrador», con nombre y hora de quien revisó.

---

# 9 · Valor, límites y próximo paso

**Hipótesis de valor (no medida):** no publicar algo que no se sostiene.

**Límites que declaramos:**
- Solo titulares → casi todo queda «insuficiente». Con el cuerpo de la nota, la evidencia sube.
- Un modelo local pequeño redacta sobrio; el guardián retira mucho.
- La clasificación de tema todavía se equivoca a la vista.

**Próximo paso:** piloto con una mesa de TVN, con comunicados oficiales como fuente primaria.

---

# Antes de contar una historia, mostramos qué la sostiene.

**Sourced · nada sin fuente.**

- Repositorio público: https://github.com/pixeltabletop/jajanken-lupa
- Documentación técnica y funcional: en esta misma página del equipo, en Notion.

Equipo Jajanken: Josué Carrillo · Diego Laverde · Juan Andrés López

---
---

# Guion del orador (no se proyecta)

**Antes de empezar (5 min antes):** servidor arriba, navegador en `http://127.0.0.1:8765`, tema Redacción, Ollama abierto, una pregunta de calentamiento hecha, esta página en otra pestaña, **Wi-Fi apagado a la vista del jurado**.

| Tiempo | Diapositiva | Qué decir / hacer |
|---|---|---|
| 0:00–1:00 | 1 · El problema | Los tres errores con ejemplos. Cerrar con «saber qué sostiene cada cosa antes de contarla». |
| 1:00–2:00 | 2 · Qué es · 3 · Datos | Las dos preguntas (importancia y respaldo). Datos reales del 7 de octubre, sin internet. |
| 2:00–6:00 | **Demo en vivo** (4 · 5 · 6) | **Agenda** (30 s): puntaje desglosado y, aparte, «insuficiente». **Radiografía** (45 s): donación de EE.UU., dos medios, «dos medios no son dos fuentes». **Mesa** (60 s): borrador de cruceros, chips de cita, «Retirado por el guardián»; **Generar versión** reel 30 s tono cercano → aviso de alcance. **Preguntar** (60 s): inflación de hoy → dato 2024 con aviso; oro en Bolivia → abstención. **Revisión** (45 s): marcar «requiere evidencia» con comentario; «no existe el botón publicar». |
| 6:00–8:00 | 7 · IA medida · 8 · Confiable | 7/7 contra 4/7; el ejemplo del «precio del clientelismo». Prueba sin red y seguridad. Contar una prueba fallida: el guardián dejaba pasar «¡Reserva tu crucero ahora!» → ahora revisa cada oración. |
| 8:00–9:00 | 9 · Valor y límites | Hipótesis, no medida. Límites sin pena. Piloto con TVN. |
| 9:00–10:00 | Cierre | Frase final y enlaces. |

**Plan B:** si el servidor no arranca, mostrar las capturas de esta página; si el modelo tarda, el borrador ya está guardado; si una pregunta sale rara, decirlo y pasar a la siguiente.

### Preguntas probables del jurado
| Pregunta | Respuesta corta |
|---|---|
| ¿De dónde sale esa cifra y de qué año es? | Banco Mundial, FP.CPI.TOTL.ZG, 2024, con unidad y aviso de que no es actual. Si se pide 2026, se abstiene. |
| Cinco medios replican una agencia: ¿cuántas fuentes cuentas? | Una. La procedencia solo cuenta si se declara. |
| ¿Por qué la agenda dice «0 fuentes»? | Los RSS no declaran su fuente primaria; Sourced no la inventa. Es el control, no un error. |
| ¿Y si una fuente trae instrucciones ocultas? | Se trata como dato y se aparta. En el banco de modelos uno la citó: por eso la regla vive en el código. |
| ¿Qué mejora la IA frente a algo simple? | Abstención correcta 7/7 contra 4/7; clasificación 0,45 contra 0,26. |
| ¿Funciona sin internet de verdad? | Sí: Wi-Fi cortado, 5/5 pasos, la sonda probó 52 veces y no salió nada. |
| ¿Cuánto cuesta? | Cero por uso: todo local, sin claves ni API de pago. |
| ¿Por qué no está en línea? | Por diseño: la redacción trabaja sin depender de la red ni enviar datos a terceros. El repositorio se instala en ~8 minutos. |
