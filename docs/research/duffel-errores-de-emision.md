# Duffel: inventario de errores al emitir una reserva

> Investigación del 2026-10-28. Fuentes: la documentación oficial de Duffel ([manejo de respuestas](https://duffel.com/docs/api/overview/response-handling), [creación de órdenes y reservas](https://duffel.com/docs/api/overview/response-handling/order-and-booking-creation), [órdenes](https://duffel.com/docs/api/orders), [cancelaciones](https://duffel.com/docs/api/order-cancellations), [webhooks](https://duffel.com/docs/api/webhooks)) y lo observado en modo test.
> Sirve de memoria para el estado «Error de emisión» ([02-reserva-vuelos.md §8.2](../architecture/02-reserva-vuelos.md)) y para el [plan de failover](../architecture/XX-failover-proveedores.md).
> **Lo que la documentación no dice** está marcado como «sin verificar»: no se infiere.

## 1. Cómo emite Duffel

| Tema | Qué dice la documentación | Efecto en nuestro diseño |
|---|---|---|
| Respuesta de `POST /air/orders` | `201` con la orden completa. `200` o `202` solo cuando se paga con **tarjeta** (`card`): la orden se confirma después | Pagamos con **`balance`**, así que hoy esperamos `201` o un error. Si algún día se paga con tarjeta hay que manejar `200`/`202` (§4) |
| Con `202` | «No reintentes: podría duplicar la orden». El recurso puede tardar **un par de horas** en aparecer. Se avisa por webhook: `order.created` (éxito) u `order.creation_failed` (fallo, más un correo de soporte) | Hay que decirle al viajero «estamos confirmando», no «falló». Requiere recibir webhooks (no implementado) |
| Tiempos | Las aerolíneas pueden tardar **hasta 120 s**. Duffel recomienda un timeout **de al menos 130 s** | Teníamos 60 s para todo. **Corregido:** 130 s solo para crear la orden (`order_timeout_s`) |
| Tickets | La orden trae `documents` («documentos emitidos»; ej. `electronic_ticket`). La página **no dice cuándo se completan** ni si pueden llegar después de crearse la orden. `synced_at` dice cuándo se sincronizó con la aerolínea, y «la aerolínea es siempre la fuente de verdad» | **Sin verificar:** hoy confirmamos al crearse la orden y mostramos los tickets que vengan. Si vienen vacíos decimos «se emiten al pagar» |
| Anular lo emitido | Si `cancel` está en `available_actions`: se pide una cotización y se confirma. Dentro de la **ventana de anulación** (`void_window_ends_at`, normalmente unas 24 h) el reembolso es total. Fuera de ella, según las condiciones de la tarifa. El reembolso vuelve al **saldo de Duffel**. Si no se puede cancelar por API, lo gestiona el equipo de Duffel desde el panel | Es la compensación para «emitido pero no cobrado». Requiere una persona o un agente con esa herramienta (sin verificar en modo test) |
| Idempotencia | Duffel **ignora** el header `Idempotency-Key` (verificado). Rechaza una segunda orden de la misma búsqueda con `offer_request_already_booked` | Reconciliamos con `find_order` por `metadata.booking_id` antes de crear |
| Reintentos | `202` y `500`: no reintentar. `503`: no se creó nada, se puede reintentar. `504`: reintentar luego. `429`: esperar `ratelimit-reset`. `offer_expired`: nueva búsqueda | Ver el inventario |

## 2. Inventario

**Resolución:** *auto* = lo resuelve el código; *agente* = hace falta una persona o un agente de IA con herramientas; *desarrollo* = es un error nuestro. **Estado** = cómo termina hoy la reserva.

### 2.1 Antes de emitir (no se creó ninguna orden)

| Error | HTTP | Hoy | Estado | Quién | Falta |
|---|---|---|---|---|---|
| Oferta inexistente o vencida (`not_found`; en modo test una vencida responde así) | 404 | `OfferUnavailableError` | `failed(offer_unavailable)` | auto | — |
| `offer_expired` | 422 | `OfferExpiredError` | `failed(offer_expired)` | auto | — |
| `offer_no_longer_available` | 422 | `OfferExpiredError` | `failed(offer_expired)` | auto | El código es aproximado: la oferta existe pero ya no se vende. Candidata al failover |
| **`price_changed`** (la aerolínea cambió el precio al emitir) | 422 | **Cae en «rechazo»** (`OrderRejectedError`) | `failed(provider_rejected)` | auto | **Mal mapeado.** Debe volver a consultar la oferta y pedirle al viajero que apruebe el precio nuevo (reutiliza `awaiting_price_approval`) |
| `order_not_created` («no reintentes») | 422 | `OrderRejectedError` | `failed(provider_rejected)` | auto | Fallo definitivo: candidato al failover |
| Datos del pasajero inválidos (`validation_error`: nombre, teléfono, fecha de nacimiento, documentos) | 422 | `OrderRejectedError` | `failed(provider_rejected)` | auto | El mensaje al viajero («revisá los datos») es correcto |
| Pasaporte o documento exigido que no se pidió | 422 | Se valida antes si la oferta lo marca; si no lo marca, llega el rechazo | `failed(passenger_rejected / provider_rejected)` | auto | Ver el pendiente «Documentos de identidad» |
| **`insufficient_balance`** (el saldo de la plataforma en Duffel no alcanza) | 422 | **Cae en «rechazo»** | `failed(provider_rejected)` | **agente** | **Mal mapeado.** No es culpa del viajero: hay que alertar a operaciones para recargar el saldo y, mientras tanto, no culpar a los datos del pasajero |
| `payment_declined` de la aerolínea (airline_error) | 422 | `OrderRejectedError` | `failed(provider_rejected)` | agente | Con pago por saldo no es la tarjeta del viajero: revisar con Duffel |
| `payment_amount_does_not_match_order_amount` / `payment_currency_does_not_match_order_currency` | 422 | `OrderRejectedError` | `failed(provider_rejected)` | desarrollo | Pagamos `cost.total` de la oferta recién consultada: si ocurre, hay un error nuestro. Debe alertar |
| `offer_request_already_booked` | 422 | Se reconcilia con `find_order`: si la orden es nuestra se adopta | `confirmed` o `failed(offer_unavailable)` | auto | — |
| `503` (servicio no disponible: «seguro que no se creó nada») | 503 | `ProviderError`, se reintenta | tras 10 intentos `failed(provider_unavailable)` | auto | Fallo definitivo: candidato al failover |
| `429` (`rate_limit_exceeded`) | 429 | `ProviderError`, se reintenta a los 30 s | ídem | auto | Respetar el header `ratelimit-reset` |

### 2.2 Al emitir: resultado incierto

| Error | HTTP | Hoy | Estado | Quién | Falta |
|---|---|---|---|---|---|
| **`airline_internal`** / `airline_unknown` (la aerolínea falló o no respondió) | 502 | Se reintenta hasta 10 veces; en el último intento se reconcilia | `failed(provider_unavailable)` si no hay orden; `issuance_error(order_unverified)` si no se puede consultar | agente | Observado en modo test: se repitió más de 4 minutos con la misma oferta. Duffel dice «contactá a soporte». Candidato al failover **solo si se confirma que no hay orden** |
| **`api_error`** (500) y mal gateway (502) de Duffel | 500 / 502 | Se reintenta | ídem | agente | **Duffel dice «no reintentes».** El riesgo de duplicar lo cubre `find_order` y `offer_request_already_booked`, pero lo correcto es no repetir el `POST`: reconciliar y, si sigue incierto, derivar a un agente con el `request_id` |
| `504` (timeout de la pasarela) | 504 | Se reintenta | ídem | agente | Reintentar luego; si persiste, soporte |
| Timeout de nuestro lado | — | `ProviderTimeoutError`, se reintenta | ídem | auto | **Corregido:** 130 s al crear la orden. Antes cortábamos a los 60 s con la orden quizá en camino |
| `200` / `202` con pago por tarjeta | 200 / 202 | **No aplica** (pagamos por saldo) | — | — | Si se paga con tarjeta: no reintentar, avisar «estamos confirmando» y esperar los webhooks `order.created` / `order.creation_failed` |

### 2.3 Después de emitir (la orden existe)

| Situación | Hoy | Estado | Quién | Falta |
|---|---|---|---|---|
| **El cobro no se puede capturar** (retención vencida, saldo cambiado) | Se guarda la orden y la autorización, no se libera el dinero | **`issuance_error(capture_failed)`** | agente | Cobrar por otro medio o **cancelar la orden en Duffel dentro de la ventana de anulación**; después liberar la retención |
| No se pudo consultar si existe la orden en el último intento | Se conserva la autorización | **`issuance_error(order_unverified)`** | agente | Revisar en el panel de Duffel por `metadata.booking_id` |
| El worker muere después de crear la orden | El reintento la encuentra con `find_order`, captura y confirma | `confirmed` | auto | — |
| Falla guardar en la base después de emitir | Ídem | `confirmed` | auto | — |
| La orden se crea pero sus tickets no llegan | **Sin verificar** | `confirmed` | agente | Verificar en la documentación si pueden llegar después; si es así, esperar `documents` antes de confirmar |
| La aerolínea cambia o cancela después (`order.airline_initiated_change_detected`) | No hay webhooks | — | agente | Suscribirse al webhook y avisar al viajero |
| La reserva se queda sin dueño (el último intento ve un lease vivo y descarta el mensaje) | Queda en `processing` | `processing` | agente | Un barrido que reencole las reservas `processing` sin lease vivo |

### 2.4 Tarjeta (paso de verificación)

| Situación | Hoy | Estado | Quién |
|---|---|---|---|
| La compra pequeña de verificación se rechaza | No se continúa | `failed(payment_declined)` | auto |
| La compra pequeña se cobra pero **no se pudo revertir** | Se registra un log `error` con el id de la compra y se sigue con la reserva | `confirmed` (u otro) | **agente**: reembolsar a mano |
| El cobro real (retención) se rechaza | No se emite nada | `failed(payment_declined)` | auto |

## 3. Mal mapeados que conviene arreglar (sin prioridad)

Tres respuestas de Duffel terminan hoy como «la aerolínea rechazó los datos del pasajero», que es un mensaje falso para el viajero:

1. `price_changed` debería abrir la aprobación del precio nuevo.
2. `insufficient_balance` es un problema de operaciones, no del pasajero.
3. `500`/`502` de Duffel: no reintentar el `POST`; reconciliar y derivar.

## 4. Qué datos necesita quien atiende un caso

Hoy los logs traen el `booking_id` y el `offer_id`. A una persona o un agente de IA le faltan:

- el **`x-request-id`** de Duffel de la llamada que falló (hoy solo se imprime en el log del cliente; conviene guardarlo en la reserva);
- el **id de la orden** de Duffel (se guarda solo cuando se conoce) y el `metadata.booking_id` para buscarla en el panel;
- el id de la autorización y el de la compra de verificación, con su estado;
- el historial de intentos (cuándo, contra quién, qué respondió).

## 5. Pendientes que salen de esta investigación

| Tema | Detalle |
|---|---|
| Tickets que llegan tarde | Verificar con Duffel (soporte o pruebas) si los `documents` pueden completarse después de crearse la orden |
| Cancelación en modo test | Verificar que `order-cancellations` funcione en el sandbox |
| Mapeos | `price_changed`, `insufficient_balance` y la política de «no reintentar» para `500`/`502` |
| Webhooks de Duffel | `order.created`, `order.creation_failed` y `order.airline_initiated_change_detected`; obligatorios si se paga con tarjeta |
| Guardar `x-request-id` | En la reserva, para quien atienda el caso |
