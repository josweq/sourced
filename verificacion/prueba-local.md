---
skill: ia-local-verificable
estado: amarillo
fecha: 2026-10-08
commit: 93c11999985eb3cda6653e8c660c80da6fca0ec8
---

# Prueba local · jajanken-lupa

Generado por `corrida-sin-red.mjs`. Datos crudos en `prueba-local.json`.
Commit tomado de: HEAD de C:\Users\Josue Carrillo\personal\jajanken-lupa.

## Las tres capas

| Capa | Qué | Resultado |
|---|---|---|
| 1 · Estática | no se pasó | — |
| 2 · Corrida desconectada | `python scripts/smoke_sin_red.py --db data/local/demo-20261008T051225Z.sqlite` | sale con 0 en 57.4 s |
| 3 · Sonda durante | 13 tomas × 4 destinos, cada 5 s mientras corre | 0 de 52 intentos alcanzaron algo |

Calibración con la red puesta: la sonda vio la red.

## Tomas

| Momento | Hora | 1.1.1.1:443 | 8.8.8.8:443 | https://cloudflare.com/cdn-cgi/trace | example.com |
|---|---|---|---|---|---|
| antes del comando | 14:01:21 | no · EHOSTUNREACH | no · EHOSTUNREACH | no · ENOTFOUND | no · getaddrinfo ENOTFOUND example.com |
| durante el comando #1 (+1 s) | 14:01:22 | no · EHOSTUNREACH | no · EHOSTUNREACH | no · ENOTFOUND | no · getaddrinfo ENOTFOUND example.com |
| durante el comando #2 (+6 s) | 14:01:27 | no · EHOSTUNREACH | no · EHOSTUNREACH | no · ENOTFOUND | no · getaddrinfo ENOTFOUND example.com |
| durante el comando #3 (+11 s) | 14:01:32 | no · EHOSTUNREACH | no · EHOSTUNREACH | no · ENOTFOUND | no · getaddrinfo ENOTFOUND example.com |
| durante el comando #4 (+17 s) | 14:01:37 | no · EHOSTUNREACH | no · EHOSTUNREACH | no · ENOTFOUND | no · getaddrinfo ENOTFOUND example.com |
| durante el comando #5 (+22 s) | 14:01:42 | no · EHOSTUNREACH | no · EHOSTUNREACH | no · ENOTFOUND | no · getaddrinfo ENOTFOUND example.com |
| durante el comando #6 (+27 s) | 14:01:47 | no · EHOSTUNREACH | no · EHOSTUNREACH | no · ENOTFOUND | no · getaddrinfo ENOTFOUND example.com |
| durante el comando #7 (+32 s) | 14:01:53 | no · EHOSTUNREACH | no · EHOSTUNREACH | no · ENOTFOUND | no · getaddrinfo ENOTFOUND example.com |
| durante el comando #8 (+37 s) | 14:01:58 | no · EHOSTUNREACH | no · EHOSTUNREACH | no · ENOTFOUND | no · getaddrinfo ENOTFOUND example.com |
| durante el comando #9 (+42 s) | 14:02:03 | no · EHOSTUNREACH | no · EHOSTUNREACH | no · ENOTFOUND | no · getaddrinfo ENOTFOUND example.com |
| durante el comando #10 (+47 s) | 14:02:08 | no · EHOSTUNREACH | no · EHOSTUNREACH | no · ENOTFOUND | no · getaddrinfo ENOTFOUND example.com |
| durante el comando #11 (+52 s) | 14:02:13 | no · EHOSTUNREACH | no · EHOSTUNREACH | no · ENOTFOUND | no · getaddrinfo ENOTFOUND example.com |
| después del comando | 14:02:18 | no · EHOSTUNREACH | no · EHOSTUNREACH | no · ENOTFOUND | no · getaddrinfo ENOTFOUND example.com |

## Final de la salida del comando

```
Loading weights:   0%|          | 0/199 [00:00<?, ?it/s]
Loading weights:  28%|##7       | 55/199 [00:00<00:00, 549.58it/s]
Loading weights: 100%|##########| 199/199 [00:00<00:00, 1207.73it/s]
OK    pregunta con evidencia (embeddings locales) � 44449 ms � 3 afirmaciones citadas
OK    pregunta sin evidencia (abstenci�n) � 104 ms � abstenci�n
OK    cifra oficial del snapshot � 4 ms � Panam�, 2024: 0,7 (% anual). Dato anual del Banco Mundial; n
OK    redacci�n con Ollama local � 8065 ms � �En qu� puedo ayud
OK    adaptaci�n de formato � 40 ms � 0-5 s � Lo que se reporta
```

## Lo que falta

- amarillo · sin capa estática: pasar --estatica con la puerta que prohíbe la red en el código

## Hecho cuando

- [ ] Capa 1: la puerta estática pasa y está probada rompiéndola
- [x] Capa 2: el comando real funciona con la red cortada
- [x] Capa 3: ninguna toma antes, durante o después vio salida
- [x] La sonda se calibró viendo la red antes del corte
