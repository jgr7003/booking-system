# Duffel API: búsqueda de vuelos y reserva

> Documentación básica para integrar la **búsqueda de vuelos** y la **solicitud de reserva** con [Duffel](https://duffel.com/docs) (API v2).
> Fuente: documentación oficial de Duffel, consultada el 2026-10-23.

---

## 1. Conceptos y configuración general

### 1.1 Modo test

- Los tokens de prueba se crean en el Dashboard de Duffel con el **Developer test mode** activado. Empiezan con `duffel_test_`.
- Un token de test solo puede acceder a recursos de test (`live_mode: false` en las respuestas).
- **Aerolínea de prueba:** *Duffel Airways* (IATA `ZZ`). Es el sandbox más confiable. Sus horarios y precios no son realistas. Soporta fare brands, servicios extra (equipaje), mapas de asientos, creación de órdenes, cancelación y cambios.
- Los sandboxes de otras aerolíneas pueden estar caídos o sin disponibilidad.
- **Pago en test:** con `type: "balance"` el saldo es **ilimitado** en modo test.

### 1.2 Base URL y headers comunes

```
Base URL: https://api.duffel.com
```

| Header            | Valor                         |
|-------------------|-------------------------------|
| `Authorization`   | `Bearer <ACCESS_TOKEN>`       |
| `Duffel-Version`  | `v2`                          |
| `Content-Type`    | `application/json`            |
| `Accept`          | `application/json`            |
| `Accept-Encoding` | `gzip`                        |

Todos los bodies de request y response van envueltos en un objeto `data`.

### 1.3 Glosario mínimo

| Término           | Significado                                                                                  | Prefijo de ID |
|-------------------|----------------------------------------------------------------------------------------------|---------------|
| **Offer Request** | La búsqueda: qué tramos, pasajeros y cabina se buscan.                                       | `orq_`        |
| **Offer**         | Un resultado de la búsqueda: itinerario + precio de una aerolínea. Tiene vencimiento.        | `off_`        |
| **Slice**         | Un tramo del viaje (origen → destino). Solo ida = 1 slice, ida y vuelta = 2 slices.          | `sli_`        |
| **Segment**       | Un vuelo concreto dentro de un slice (un slice con escala tiene 2 o más segments).           | `seg_`        |
| **Passenger**     | Pasajero. El ID lo genera Duffel en la búsqueda y **se reutiliza al reservar**.              | `pas_`        |
| **Order**         | La reserva creada con la aerolínea a partir de un offer.                                     | `ord_`        |

### 1.4 Flujo general

```
1. POST /air/offer_requests      → buscar vuelos (devuelve offers + passenger ids)
2. GET  /air/offers/{offer_id}   → (recomendado) refrescar el offer elegido para obtener precio actualizado
3. POST /air/orders              → crear la reserva con offer_id + datos de pasajeros + pago
```

---

## 2. Búsqueda de vuelos: Create an Offer Request

```
POST https://api.duffel.com/air/offer_requests
```

### 2.1 Query params (opcionales)

| Parámetro          | Tipo    | Default    | Descripción                                                                                                                         |
|--------------------|---------|------------|-------------------------------------------------------------------------------------------------------------------------------------|
| `return_offers`    | boolean | `true`     | Si es `false`, la respuesta no incluye offers. Se consultan después con *List Offers*, que permite paginar, ordenar y filtrar.       |
| `supplier_timeout` | integer | `20000`    | Tiempo máximo de espera por aerolínea, en ms (2000 a 60000). Conviene que sea menor al timeout del cliente HTTP para recibir resultados parciales. |
| `view`             | enum    | `"offers"` | `"offers"` devuelve una lista plana. `"itineraries"` agrupa los resultados por slices, itinerarios y brands.                         |

### 2.2 Body: qué necesita recibir

| Campo                  | Tipo           | Requerido | Descripción                                                                                       |
|------------------------|----------------|:---------:|---------------------------------------------------------------------------------------------------|
| `slices`               | array          | ✅        | Tramos a buscar. 1 = solo ida, 2 = ida y vuelta.                                                   |
| `passengers`           | array          | ✅        | Pasajeros que viajan.                                                                             |
| `cabin_class`          | enum \| null   | ❌        | `first`, `business`, `premium_economy` o `economy`.                                               |
| `max_connections`      | integer (0–2)  | ❌        | Máximo de conexiones por slice. `0` = solo directos. Default `1`.                                  |
| `private_fares`        | object         | ❌        | Tarifas privadas por IATA de aerolínea: `{ "UA": [{ "corporate_code", "tour_code", "tracking_reference" }] }`. |
| `airline_credit_ids`   | string[]       | ❌        | Créditos de aerolínea a evaluar.                                                                  |
| `include_split_ticket` | boolean        | ❌        | Busca combinaciones de tickets separados. Requiere `view=itineraries` y habilitación por soporte.  |

#### `slices[]`

| Campo            | Tipo                 | Requerido | Descripción                                                    |
|------------------|----------------------|:---------:|----------------------------------------------------------------|
| `origin`         | string (IATA 3)      | ✅        | Código IATA de ciudad o aeropuerto de origen (ej. `EZE`, `BUE`). |
| `destination`    | string (IATA 3)      | ✅        | Código IATA de ciudad o aeropuerto de destino.                  |
| `departure_date` | string (`YYYY-MM-DD`)| ✅        | Fecha de salida.                                                |
| `departure_time` | `{ from, to }`       | ❌        | Ventana horaria de salida, hora local `hh:mm`.                  |
| `arrival_time`   | `{ from, to }`       | ❌        | Ventana horaria de llegada, hora local `hh:mm`.                 |

#### `passengers[]`

Cada pasajero se define de **una** de estas tres formas:

| Variante          | Campo requerido | Valores                                                                 |
|-------------------|-----------------|-------------------------------------------------------------------------|
| Por tipo          | `type`          | `adult`, `child`, `infant_without_seat`. Usar `adult` para mayores de 18. |
| Por edad          | `age`           | Entero entre 0 y 130. **Recomendado para menores de 18.** Es la edad en la fecha del último slice. |
| Por tarifa        | `fare_type`     | `student`, `teacher`, `contract_bulk`, etc. (tarifas privadas leisure). Puede combinarse con `age`. |

> ⚠️ No se puede enviar `type` y `age` juntos.

Campos opcionales en cualquier variante: `given_name`, `family_name` (solo obligatorios si se envían `loyalty_programme_accounts`), `loyalty_programme_accounts[] { airline_iata_code, account_number }` y `user_id`.

### 2.3 Ejemplo de request

Solo ida EZE → MAD, 2 adultos y 1 menor, en economy:

```bash
curl -X POST --compressed "https://api.duffel.com/air/offer_requests?supplier_timeout=10000" \
  -H "Accept-Encoding: gzip" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -H "Duffel-Version: v2" \
  -H "Authorization: Bearer $DUFFEL_TOKEN" \
  -d '{
  "data": {
    "slices": [
      { "origin": "EZE", "destination": "MAD", "departure_date": "2026-12-15" }
    ],
    "passengers": [
      { "type": "adult" },
      { "type": "adult" },
      { "age": 10 }
    ],
    "cabin_class": "economy",
    "max_connections": 1
  }
}'
```

### 2.4 Response: qué retorna

`201 Created` con el Offer Request en `data`:

| Campo          | Tipo           | Descripción                                                                                 |
|----------------|----------------|---------------------------------------------------------------------------------------------|
| `id`           | string         | ID del offer request (`orq_...`).                                                           |
| `live_mode`    | boolean        | `false` en test.                                                                            |
| `created_at`   | datetime       | Fecha de creación.                                                                          |
| `cabin_class`  | string \| null | Cabina solicitada.                                                                          |
| `slices`       | array          | Slices solicitados, con `origin` y `destination` expandidos como objetos Place.             |
| `passengers`   | array          | **Pasajeros con su `id` (`pas_...`)**. Estos IDs se usan luego para reservar.               |
| `offers`       | array          | Ofertas encontradas. Vacío si `return_offers=false`.                                        |
| `client_key`   | string         | Clave para el componente *Duffel Ancillaries* (frontend).                                   |

#### Campos principales de cada `offers[]`

| Campo                                         | Tipo     | Descripción                                                                                          |
|-----------------------------------------------|----------|------------------------------------------------------------------------------------------------------|
| `id`                                          | string   | ID del offer (`off_...`). **Es lo que se envía para reservar.**                                      |
| `total_amount` / `total_currency`             | string   | Precio total y moneda. Se usan en el pago de la orden.                                               |
| `base_amount` / `base_currency`               | string   | Tarifa base sin impuestos.                                                                           |
| `tax_amount` / `tax_currency`                 | string   | Impuestos.                                                                                           |
| `expires_at`                                  | datetime | **Vencimiento del offer.** Después de esta fecha no se puede reservar.                               |
| `owner`                                       | object   | Aerolínea que vende la tarifa: `name`, `iata_code`, `logo_symbol_url`, `conditions_of_carriage_url`. |
| `slices[]`                                    | array    | Cada slice con `origin`, `destination`, `duration` (ISO 8601, ej. `PT02H26M`), `fare_brand_name` y `segments[]`. |
| `slices[].segments[]`                         | array    | `departing_at`, `arriving_at`, `duration`, `origin_terminal`, `destination_terminal`, `aircraft`, `marketing_carrier` y `marketing_carrier_flight_number`, `operating_carrier` y `operating_carrier_flight_number`, `stops[]`, `passengers[]`. |
| `slices[].segments[].passengers[]`            | array    | Por pasajero: `cabin_class`, `cabin_class_marketing_name`, `fare_basis_code`, `baggages[] { type, quantity }`. |
| `passengers[]`                                | array    | Pasajeros del offer, con el `id` y el `type` que asignó la aerolínea.                                |
| `payment_requirements`                        | object   | `requires_instant_payment` (si es `true`, no se puede hacer *hold*), `payment_required_by` y `price_guarantee_expires_at`. |
| `conditions`                                  | object   | `refund_before_departure` y `change_before_departure`, cada uno con `allowed`, `penalty_amount` y `penalty_currency`. |
| `passenger_identity_documents_required`       | boolean  | Si es `true`, hay que enviar pasaporte al reservar.                                                  |
| `supported_passenger_identity_document_types` | string[] | Tipos de documento aceptados (ej. `passport`).                                                       |
| `total_emissions_kg`                          | string   | Emisiones estimadas de CO₂.                                                                          |

#### Ejemplo de response (resumido)

```json
{
  "data": {
    "id": "orq_00009hjdomFOCJyxHG7k7k",
    "live_mode": false,
    "cabin_class": "economy",
    "passengers": [
      { "id": "pas_00009hj8USM7Ncg31cBCLL", "type": "adult" }
    ],
    "offers": [
      {
        "id": "off_00009htYpSCXrwaB9DnUm0",
        "total_amount": "45.00",
        "total_currency": "GBP",
        "expires_at": "2020-01-17T10:42:14.545Z",
        "owner": { "name": "Duffel Airways", "iata_code": "ZZ" },
        "payment_requirements": {
          "requires_instant_payment": false,
          "payment_required_by": "2020-01-17T10:42:14Z",
          "price_guarantee_expires_at": "2020-01-17T10:42:14Z"
        },
        "passenger_identity_documents_required": false,
        "slices": [
          {
            "duration": "PT02H26M",
            "fare_brand_name": "Basic",
            "segments": [
              {
                "departing_at": "2020-06-13T16:38:02",
                "arriving_at": "2020-06-13T19:04:02",
                "marketing_carrier": { "iata_code": "ZZ", "name": "Duffel Airways" },
                "marketing_carrier_flight_number": "1234",
                "passengers": [
                  {
                    "passenger_id": "pas_00009hj8USM7Ncg31cBCLL",
                    "cabin_class": "economy",
                    "baggages": [{ "type": "checked", "quantity": 1 }]
                  }
                ]
              }
            ]
          }
        ]
      }
    ]
  }
}
```

---

## 3. Paso intermedio recomendado: refrescar el offer elegido

```
GET https://api.duffel.com/air/offers/{offer_id}
```

Los offers se desactualizan rápido. Antes de reservar, Duffel recomienda volver a consultar el offer elegido para obtener `total_amount` y `total_currency` actualizados. Estos son los valores que deben enviarse en el pago de la orden.

---

## 4. Solicitud de reserva: Create an Order

```
POST https://api.duffel.com/air/orders
```

### 4.1 Reglas importantes

- Solo se puede reservar **un offer por offer request**, y `selected_offers` debe tener **exactamente un** elemento.
- Máximo **9 pasajeros** por orden.
- Hay dos tipos de orden:
  - `instant`: se paga al crear la orden. El body debe incluir `payments`.
  - `hold`: se reserva sin pagar y se paga después con *Create a payment*. **No se envían `payments` ni `services`.** Solo se permite si el offer tiene `payment_requirements.requires_instant_payment = false`.
- El `payments[].amount` debe ser igual al `total_amount` del offer más el de los servicios agregados. La `currency` debe ser igual al `total_currency` del offer.
- Los infantes (edad 0 o 1) deben asociarse a un adulto mediante `infant_passenger_id`, con un adulto distinto por cada infante.
- Al mostrar la confirmación al cliente hay que incluir `booking_reference`, el itinerario completo y el nombre del **operating carrier** de cada segmento (requisito regulatorio de EE.UU.).

### 4.2 Body: qué necesita recibir

| Campo             | Tipo     | Requerido                 | Descripción                                                                                  |
|-------------------|----------|:-------------------------:|----------------------------------------------------------------------------------------------|
| `selected_offers` | string[] | ✅                        | Array con **un** offer ID (`off_...`).                                                       |
| `passengers`      | array    | ✅                        | Datos completos de cada pasajero (ver abajo).                                                |
| `payments`        | array    | ✅ en `instant` / ❌ en `hold` | Pago de la orden.                                                                        |
| `type`            | enum     | ❌                        | `instant` o `hold`.                                                                          |
| `services`        | array    | ❌                        | Servicios extra (equipaje, asientos): `[{ "id": "ase_...", "quantity": 1 }]`.                 |
| `metadata`        | object   | ❌                        | Hasta 50 pares clave/valor (string) propios. Útil para guardar un ID interno de reserva.     |
| `users`           | string[] | ❌                        | IDs de usuarios (`icu_...`) que pueden gestionar la orden.                                   |

#### `passengers[]`

| Campo                         | Tipo                   | Requerido | Descripción                                                                               |
|-------------------------------|------------------------|:---------:|-------------------------------------------------------------------------------------------|
| `id`                          | string                 | ✅        | **ID `pas_...` devuelto en el offer request.**                                            |
| `given_name`                  | string                 | ✅        | Nombre. Solo letras ASCII, Latin-1 o Latin Extended-A, espacio, `-` y `'`. Nombre más apellido suman como máximo 40 caracteres. |
| `family_name`                 | string                 | ✅        | Apellido. Mismas reglas que `given_name`.                                                 |
| `title`                       | enum                   | ✅        | `mr`, `ms`, `mrs`, `miss`, `dr` (algunas aerolíneas no aceptan `dr`).                     |
| `gender`                      | enum                   | ✅        | `m` o `f`.                                                                                |
| `born_on`                     | string (`YYYY-MM-DD`)  | ✅        | Fecha de nacimiento.                                                                      |
| `email`                       | string                 | ✅        | Email del pasajero.                                                                       |
| `phone_number`                | string (E.164)         | ✅        | Teléfono en formato internacional, ej. `+5491112345678`.                                  |
| `identity_documents`          | array                  | ⚠️        | Obligatorio (pasaporte) si el offer tiene `passenger_identity_documents_required = true`. |
| `infant_passenger_id`         | string                 | ❌        | En el adulto responsable: ID del infante que viaja con él.                                |
| `user_id`                     | string                 | ❌        | Asocia el pasajero a un usuario cliente.                                                  |

#### `passengers[].identity_documents[]`

| Campo                  | Tipo            | Requerido | Descripción                                                                          |
|------------------------|-----------------|:---------:|--------------------------------------------------------------------------------------|
| `type`                 | enum            | ✅        | `passport`, `tax_id`, `known_traveler_number` o `passenger_redress_number`.          |
| `unique_identifier`    | string          | ✅        | Número del documento.                                                                |
| `issuing_country_code` | string (ISO 3166-1 alpha-2) | ✅ | País emisor (ej. `AR`). Aplica a pasaporte, known traveler y redress.         |
| `expires_on`           | string (`YYYY-MM-DD`) | ✅  | Vencimiento. Solo se envía en pasaportes.                                            |

#### `payments[]`

| Campo                       | Tipo           | Requerido | Descripción                                                                         |
|-----------------------------|----------------|:---------:|-------------------------------------------------------------------------------------|
| `type`                      | enum           | ✅        | `balance` (saldo de la cuenta Duffel, **ilimitado en test**), `card` o `arc_bsp_cash` (agentes IATA). |
| `amount`                    | string         | ✅        | Debe coincidir con el `total_amount` del offer más los servicios.                   |
| `currency`                  | string (ISO 4217) | ✅     | Debe coincidir con el `total_currency` del offer.                                   |
| `three_d_secure_session_id` | string         | ❌        | ID de la sesión 3DS (`3ds_...`). Solo para pagos con tarjeta.                       |

### 4.3 Ejemplo de request (instant, pago con balance)

```bash
curl -X POST --compressed "https://api.duffel.com/air/orders" \
  -H "Accept-Encoding: gzip" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -H "Duffel-Version: v2" \
  -H "Authorization: Bearer $DUFFEL_TOKEN" \
  -d '{
  "data": {
    "type": "instant",
    "selected_offers": ["off_00009htYpSCXrwaB9DnUm0"],
    "payments": [
      { "type": "balance", "currency": "GBP", "amount": "45.00" }
    ],
    "passengers": [
      {
        "id": "pas_00009hj8USM7Ncg31cBCLL",
        "title": "mrs",
        "given_name": "Amelia",
        "family_name": "Earhart",
        "gender": "f",
        "born_on": "1987-07-24",
        "email": "amelia@example.com",
        "phone_number": "+442080160509",
        "identity_documents": [
          {
            "type": "passport",
            "unique_identifier": "19KL56147",
            "issuing_country_code": "GB",
            "expires_on": "2030-04-25"
          }
        ]
      }
    ],
    "metadata": { "internal_booking_id": "BK-0001" }
  }
}'
```

Para un **hold**, se envía `"type": "hold"` y se omiten `payments` y `services`.

### 4.4 Response: qué retorna

`201 Created` con la Order en `data`:

| Campo                             | Tipo             | Descripción                                                                                              |
|-----------------------------------|------------------|----------------------------------------------------------------------------------------------------------|
| `id`                              | string           | ID de la orden (`ord_...`).                                                                              |
| `booking_reference`               | string           | **PNR / localizador** de la aerolínea.                                                                   |
| `booking_references`              | array            | Todos los PNR, incluidos los de otras aerolíneas del itinerario.                                         |
| `type`                            | enum             | `instant` o `hold`.                                                                                      |
| `offer_id`                        | string           | Offer que se reservó.                                                                                    |
| `total_amount` / `total_currency` | string           | Total con impuestos.                                                                                     |
| `base_amount`, `tax_amount`       | string \| null   | Tarifa base e impuestos, cada uno con su moneda.                                                         |
| `tax_breakdown`                   | array            | Detalle de impuestos (puede venir vacío).                                                                |
| `passengers`                      | array            | Pasajeros con `id`, `type`, `title`, `given_name`, `family_name`, `born_on`, `gender`, `email`, `phone_number`, `infant_passenger_id`. |
| `slices`                          | array            | Itinerario reservado, con la misma estructura de slices y segments que el offer.                         |
| `services`                        | array            | Servicios contratados.                                                                                   |
| `documents`                       | array            | Documentos emitidos, ej. `{ "type": "electronic_ticket", "unique_identifier": "1252106312810", "passenger_ids": [...] }`. |
| `payment_status`                  | object           | `awaiting_payment` (true en un hold sin pagar), `paid_at`, `payment_required_by`, `price_guarantee_expires_at`. |
| `conditions`                      | object           | Condiciones de cambio y reembolso, con penalidades.                                                      |
| `owner`                           | object           | Aerolínea dueña de la orden.                                                                             |
| `available_actions`               | string[]         | Acciones posibles: `cancel`, `change`, `update`.                                                         |
| `void_window_ends_at`             | datetime \| null | Fin de la ventana de anulación sin costo (preview).                                                      |
| `cancellation` / `cancelled_at`   | object / datetime | Se completan si la orden se cancela.                                                                    |
| `metadata`                        | object           | Lo que se envió en el request.                                                                           |
| `live_mode`                       | boolean          | `false` en test.                                                                                         |
| `created_at` / `synced_at`        | datetime         | Fecha de creación y de la última sincronización con la aerolínea.                                        |

#### Ejemplo de response (resumido)

```json
{
  "data": {
    "id": "ord_00009hthhsUZ8W4LxQgkjo",
    "booking_reference": "RZPNX8",
    "type": "instant",
    "live_mode": false,
    "offer_id": "off_00009htYpSCXrwaB9DnUm0",
    "total_amount": "90.80",
    "total_currency": "GBP",
    "payment_status": {
      "awaiting_payment": false,
      "paid_at": "2020-04-11T15:48:11Z",
      "payment_required_by": null,
      "price_guarantee_expires_at": null
    },
    "passengers": [
      {
        "id": "pas_00009hj8USM7Ncg31cBCLL",
        "type": "adult",
        "title": "mrs",
        "given_name": "Amelia",
        "family_name": "Earhart",
        "born_on": "1987-07-24",
        "gender": "f",
        "email": "amelia@example.com",
        "phone_number": "+442080160509"
      }
    ],
    "documents": [
      {
        "type": "electronic_ticket",
        "unique_identifier": "1252106312810",
        "passenger_ids": ["pas_00009hj8USM7Ncg31cBCLL"]
      }
    ],
    "available_actions": ["cancel", "update"],
    "metadata": { "internal_booking_id": "BK-0001" },
    "created_at": "2020-04-11T15:48:11.642Z",
    "synced_at": "2020-04-11T15:48:11Z"
  }
}
```

### 4.5 Errores de validación específicos

| Campo      | Código                                | Causa                                                                                     |
|------------|---------------------------------------|-------------------------------------------------------------------------------------------|
| `payments` | `payments_not_allowed_for_order_type` | Se enviaron `payments` en una orden `hold`.                                               |
| `services` | `services_not_allowed_for_order_type` | Se enviaron `services` en una orden `hold`.                                               |
| `services` | `intended_services_conflict`          | Los servicios no coinciden con los `intended_services` con los que se cotizó el offer.    |
| `type`     | `not_valid_with_selected_offer`       | Se pidió `hold` y el offer exige pago inmediato, o `payment_required_by` ya pasó.         |

### 4.6 Comportamiento verificado en modo test (2026-10-27)

Probado con una oferta de Duffel Airways (LHR→JFK, 226,75 USD). Las respuestas están en `backend/app/flights/tests/fixtures/duffel/`.

| Caso | Respuesta de Duffel |
|---|---|
| `GET /air/offers/{id}` | `200`. `passengers[].id` trae el `pas_…` que exige la orden, así que el frontend no necesita conocerlo |
| `GET /air/offers/{id}` inexistente | `404 not_found` |
| `GET /air/orders?offer_id=…` | `200` con `data: []` antes de reservar y con la orden (incluido su `metadata`) después |
| Orden con un monto que no es el total | `422 payment_amount_does_not_match_order_amount` |
| Orden creada | `201`. `booking_reference` (ej. `M6BM7T`), `documents[]` con `electronic_ticket`, `payment_status.paid_at`, `available_actions: [cancel, change, update]`, `metadata` tal cual |
| Segunda orden sobre el mismo offer request (otra oferta o la misma) | `422 offer_request_already_booked` |
| Segunda orden con el **mismo header `Idempotency-Key`** | También `422 offer_request_already_booked`: **Duffel no implementa `Idempotency-Key`**, el header se ignora |
| `GET /air/offers/{id}` de una oferta ya reservada | `200`: la oferta se sigue pudiendo leer, no sirve para saber si se reservó |
| `GET /air/offers/{id}` de una oferta **vencida** (1 min después de `expires_at`) | `404 not_found`, igual que una inexistente |
| Orden sobre una oferta **vencida** | `422 not_found` en `selected_offers` («linked record(s) not found»), no `offer_no_longer_available` |

**Consecuencia para la reserva:** una oferta vencida no se distingue de una inexistente, así que las dos terminan como `offer_unavailable`. El código `offer_expired` queda para los casos que Duffel documenta (`offer_no_longer_available`). Además, el `422 offer_request_already_booked` es un guardián natural contra la orden doble. Si el worker lo recibe, no marca la reserva como fallida: reconcilia con `GET /air/orders?offer_id=…` y, si encuentra una orden con el mismo `metadata.booking_id`, la adopta.

---

### 4.7 Emisión: respuestas, tiempos y errores (documentación oficial, 2026-10-28)

- **Respuestas:** `201` con la orden completa. `200` o `202` solo si se paga con **tarjeta**: la orden se confirma después y el resultado llega por los webhooks `order.created` u `order.creation_failed`. Con `202` **no se reintenta**. Nosotros pagamos con `balance`.
- **Tiempos:** las aerolíneas pueden tardar hasta **120 s**; Duffel recomienda un timeout de **al menos 130 s** (configurado en `order_timeout_s`).
- **No reintentar:** `202`, `500` y mal gateway `502` de Duffel; `order_not_created`; `offer_expired`. **Se puede reintentar:** `503` (no se creó nada) y `504` más tarde; `429` tras `ratelimit-reset`.
- **Anular una orden emitida:** cotización y confirmación con `order-cancellations`, si `cancel` está en `available_actions`; dentro de `void_window_ends_at` (normalmente ~24 h) el reembolso es total y vuelve al saldo de Duffel.
- **Sin verificar:** si los `documents` (tickets) pueden completarse después de crearse la orden.

El inventario completo, con cómo se trata cada error y quién lo resuelve, está en [../research/duffel-errores-de-emision.md](../research/duffel-errores-de-emision.md).

---

## 5. Mapeo de datos entre búsqueda y reserva

| Dato que necesita la reserva          | De dónde sale                                                        |
|---------------------------------------|----------------------------------------------------------------------|
| `selected_offers[0]`                  | `offers[].id` del offer request o del GET del offer                   |
| `passengers[].id`                     | `passengers[].id` del offer request (u `offer.passengers[].id`)       |
| `payments[].amount`                   | `offer.total_amount` (más servicios), idealmente del GET del offer   |
| `payments[].currency`                 | `offer.total_currency`                                               |
| ¿Se permite `hold`?                   | `offer.payment_requirements.requires_instant_payment == false`       |
| ¿Hace falta pasaporte?                | `offer.passenger_identity_documents_required`                        |
| ¿Hasta cuándo se puede reservar?      | `offer.expires_at`                                                   |

---

## Referencias

- Test mode: https://duffel.com/docs/api/overview/test-mode
- Create an offer request: https://duffel.com/docs/api/v2/offer-requests/create-offer-request
- Create an order: https://duffel.com/docs/api/v2/orders/create-order
- Quick start: https://duffel.com/docs/guides/quick-start
