# Plan: reserva de vuelos (etapa 2)

> Spec: [2026-10-27-reserva-vuelos-design.md](../specs/2026-10-27-reserva-vuelos-design.md)
> Fecha: 2026-10-27

## Reglas del plan

- Cada fase termina con `make test` y `make lint` en verde y con `graphify update .`.
- Sin commits salvo pedido del autor: al cierre de cada fase se propone uno.
- Los tests nunca llaman a Duffel. Las únicas llamadas reales son las de la fase 0, que el autor autorizó, para capturar fixtures.
- Las dependencias se fijan con `==`. En el frontend se agregan con `make fe-add` y respetando la antigüedad mínima de pnpm.

## Fase 0 · Fixtures y verificación de Duffel

1. Script en el scratchpad (no en el repo), corrido dentro del contenedor `api`. Hace una búsqueda LHR→JFK de 1 adulto y, sobre esa búsqueda:
   - `GET /air/offers/{id}`;
   - `POST /air/orders` (instant, balance, `metadata.booking_id`);
   - `GET /air/orders?offer_id=…`;
   - una orden con un monto incorrecto (error de pago);
   - una orden sobre una oferta ya reservada u otro caso de oferta no disponible;
   - `GET` de una oferta inexistente.
2. Guardar las respuestas en `backend/app/flights/tests/fixtures/duffel/` sin el token ni headers sensibles. Los datos del pasajero son ficticios.
3. Revisar en la documentación de Duffel si existe un header `Idempotency-Key` para `POST /air/orders` y si `GET /air/orders` filtra por `metadata`. Anotarlo en `docs/duffel-busqueda-y-reserva.md`.

**Listo cuando:** están los fixtures y queda anotado lo que se verificó.

## Fase 1 · Monolito modular: schemas y límites

1. `import-linter` en `requirements-dev.txt` y `.importlinter` con los contratos del spec §2.2. Test `app/tests/test_module_boundaries.py` que lo corre.
2. Schema `flights` en los modelos de `airports` y `cities`; `migrations/env.py` con `include_schemas=True`. Migración: `CREATE SCHEMA flights, travellers, payments, messaging` y `ALTER TABLE … SET SCHEMA flights`.
3. Verificar que `make seed-airports`, `/places` y sus tests siguen funcionando.
4. `make lint` también corre el lint del backend.

**Listo cuando:** los tests de la etapa 1 pasan sin cambios de comportamiento y el test de límites falla si se agrega a propósito un import prohibido.

## Fase 2 · Infraestructura de mensajería

1. `rabbitmq` en compose (vhost `test`, *healthcheck*), `aio-pika` y settings (`RABBITMQ_URL`, `TEST_RABBITMQ_URL`).
2. `app/core/messaging/`: modelos `outbox` e `inbox`, `add_event`, publicador con confirms, relay (`__main__`) y la base de los consumidores (inbox, reintento con TTL, DLQ).
3. Servicio `outbox-relay` en compose.
4. Tests de integración contra PostgreSQL y RabbitMQ de test: misma transacción, `SKIP LOCKED` con dos relays, *at-least-once*, inbox.

**Listo cuando:** un evento insertado en una transacción confirmada llega a RabbitMQ y uno de una transacción con *rollback* no llega.

## Fase 3 · `travellers` y `payments`

1. `app/travellers/`: `domain` (DTOs, validadores, modelos), `repositories`, `services`, `public.py`. Migración.
2. `app/payments/`: puerto `PaymentGateway`, `FakePaymentGateway` con `payment_authorizations`, `public.py`. Migración.
3. Tests unitarios y de integración (spec §11).

**Listo cuando:** `flights` puede crear un viajero y autorizar un pago usando solo los `public.py`, y el test de límites lo confirma.

## Fase 4 · Dominio y adapter de reservas en `flights`

1. DTOs: pasajero de vuelos (`title` + `TravellerDetails`), `BookingStatus`, `Order`, `FailureCode`. Validadores de la aerolínea: alfabeto, 40 caracteres, transliteración y edad.
2. Puerto `FlightProvider`: `get_offer`, `find_order`, `create_order`. En Duffel: cliente (`GET`/`POST`), mapper puro de la orden y errores mapeados (vencida, no disponible, rechazo, timeout).
3. Modelo `flights.bookings` y su migración.
4. Tests del mapper y del adapter con los fixtures de la fase 0.

## Fase 5 · API de reservas

1. Servicio `BookingService`: crear (Idempotency-Key, hash, viajero + reserva + outbox en una transacción), consultar y decidir el precio.
2. Rutas `POST /`, `GET /{id}` y `POST /{id}/price-decision`, schemas públicos sin costo ni ganancia, errores en `api/errors.py`.
3. Difusor SSE en el `lifespan` (cola exclusiva por instancia) y `GET /{id}/events`.
4. `make api-types`.
5. Tests de idempotencia (incluida la concurrencia), decisión de precio y SSE.

## Fase 6 · Worker de reservas

1. `app/flights/workers/booking_worker.py` (`python -m`), con los pasos del spec §5.4 y los reintentos de §5.5.
2. Servicio `booking-worker` en compose.
3. Tests del worker con el provider mockeado y el gateway fake (todos los casos del spec §11).
4. Prueba manual de punta a punta contra Duffel test: búsqueda → `POST` → SSE → `confirmed`.

## Fase 7 · Frontend

1. Dependencias: `react-hook-form`, `@hookform/resolvers`, `libphonenumber-js`.
2. `src/api/bookings.ts`: hooks de `POST`, `GET` y decisión de precio, y `useBookingEvents` (EventSource + invalidación de la query).
3. `src/features/checkout/`: pantalla 5, `logic.ts` (transliteración, edad, armado del body) con tests, borrador en `sessionStorage` y diálogo de precio.
4. `src/features/booking/`: pantalla 6.
5. "Tu viaje": habilitar «Continuar a pasajeros». Buscador: 1 adulto fijo.
6. Fixtures de MSW generados con el servicio del backend. Tests del flujo.
7. Verificación con Playwright contra los tableros 5, 6 y "Estados", en desktop y mobile.

## Fase 8 · Cierre

1. Reescribir `docs/architecture/02-reserva-vuelos.md` con lo implementado y los hallazgos. Agregar a `00-global.md` §13 las decisiones de la etapa y actualizar la bitácora de `AGENTS.md`.
2. `/graphify . --update` (cambiaron documentos).
3. Proponer el commit o el PR al autor.
