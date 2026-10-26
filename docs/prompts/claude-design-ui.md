# Prompt para Claude Design: propuestas de interfaz

**Cómo usarlo:** copiar todo lo que está debajo de la línea en Claude Design y adjuntar `docs/samples/offer-request-response.sample.json`, que es una respuesta real de la API de Duffel (modo test) recortada a 6 ofertas representativas. Si la herramienta acepta archivos grandes, se puede adjuntar también `offer-request-response.full.json`, con las 56 ofertas.

---

## Contexto

Estoy construyendo una aplicación web de **búsqueda y reserva de vuelos**. El backend es Python/FastAPI y consume la API de **Duffel**. Necesito **2 o 3 propuestas de interfaz distintas** para el flujo completo. Cada propuesta tiene que estar diseñada a partir de los datos reales que devuelve la API, que te detallo abajo y en el JSON adjunto.

La interfaz va en **español**. El usuario es un viajero final, no un agente de viajes, que quiere encontrar un vuelo, compararlo y reservarlo.

## Flujo a diseñar

1. **Búsqueda:** formulario con origen, destino, fecha de ida, fecha de vuelta opcional (solo ida o ida y vuelta), pasajeros (adultos y menores con edad) y cabina (`economy`, `premium_economy`, `business`, `first`). Opcional: "solo vuelos directos" (`max_connections: 0`).
2. **Espera:** la búsqueda tarda varios segundos porque Duffel consulta a varias aerolíneas en paralelo. Necesito un estado de carga que se sienta ágil.
3. **Resultados:** lista de ofertas comparables, con ordenamiento (precio, duración, hora de salida) y filtros (aerolínea, cantidad de escalas, equipaje incluido, si es reembolsable o permite cambios, franja horaria).
4. **Detalle de la oferta:** itinerario tramo por tramo, conexiones, equipaje, condiciones de cambio y reembolso, comodidades de cabina y desglose del precio.
5. **Datos de pasajeros y reserva:** formulario por pasajero y confirmación del pago.
6. **Confirmación:** localizador (PNR), itinerario y tickets emitidos.

## Qué devuelve la búsqueda (por oferta)

La búsqueda real LHR → JFK, 1 adulto, economy devolvió **56 ofertas** de 5 aerolíneas: 4 directas, 50 con 1 escala y 2 con 2 escalas. Los precios fueron de **214 a 7.710 USD**. La misma ruta y horario aparece varias veces con distintas **tarifas** ("fare brands"): Economy Light, Comfort, Comfort Plus, Flex, etc. La interfaz tiene que manejar bien esa repetición; por ejemplo, agrupando por vuelo y mostrando las tarifas como opciones.

Estructura relevante para la UI:

| Dato | Campo en la API | Notas para el diseño |
|---|---|---|
| Precio total | `total_amount` + `total_currency` | Viene como string ("402.74"). Es el precio total para **todos** los pasajeros. |
| Desglose | `base_amount`, `tax_amount` | Los impuestos pueden ser mucho mayores que la tarifa base (ej. 24.07 base + 378.67 impuestos). |
| Vendedor | `owner.name`, `owner.logo_symbol_url`, `owner.logo_lockup_url` | Logos en SVG servidos por Duffel. |
| Vencimiento | `expires_at` | **La oferta vence a los ~30 min.** La UI tiene que comunicarlo y resolver qué pasa si vence (volver a buscar). |
| Emisiones | `total_emissions_kg` | CO₂ estimado (ej. "379"). |
| Tarifa | `slices[].fare_brand_name` | "Basic", "Economy Light", "Economy Flex"… |
| Duración total | `slices[].duration` | ISO 8601 (`PT12H40M`), hay que mostrarlo como "12 h 40 min". |
| Tramos | `slices[].segments[]` | 1 segmento = directo; 2 o más = con escalas. |
| Horarios | `segments[].departing_at` / `arriving_at` | **Hora local de cada aeropuerto, sin zona horaria.** Se puede llegar "antes" de salir o al día siguiente (+1). |
| Aeropuertos | `origin` / `destination`: `iata_code`, `name`, `city_name`, `time_zone` | Más `origin_terminal` y `destination_terminal`, que pueden venir en `null`. |
| Vuelo | `marketing_carrier` + `marketing_carrier_flight_number` | Ej. "LX 0317". |
| Operador | `operating_carrier` | **Puede ser distinto del vendedor y del marketing carrier.** Ej.: la oferta la vende Lufthansa pero vuela SWISS. **Es obligatorio mostrar el nombre del operador de cada tramo** (regulación de EE.UU.). |
| Avión | `aircraft.name` | Puede venir en `null`. |
| Equipaje | `segments[].passengers[].baggages[]` | `{type: "checked" \| "carry_on", quantity}`. Hay tarifas con 0 valijas despachadas. |
| Cabina | `segments[].passengers[].cabin.amenities` | Wi-Fi (`available`, `cost: free/paid`), enchufe, asiento (`pitch` en pulgadas, `legroom: less/standard/more`). Varía por tramo y puede faltar. |
| Cambios / reembolso | `conditions.change_before_departure`, `conditions.refund_before_departure` | `{allowed, penalty_amount, penalty_currency}`. **La penalidad puede estar en otra moneda que el precio** (ej. precio en USD y penalidad en GBP) o venir `null`. |
| Extras de la tarifa | `slices[].conditions` | `advance_seat_selection`, `priority_boarding`, `priority_check_in`: `true`, `false` o `null` (desconocido). |
| Reserva sin pago | `payment_requirements.requires_instant_payment`, `payment_required_by` | Si es `false`, se puede "reservar ahora y pagar después" hasta `payment_required_by`. |
| Documento | `passenger_identity_documents_required` | Si es `true`, el formulario de pasajero tiene que pedir pasaporte. |

### Ejemplo real de una oferta (recortado)

```json
{
  "id": "off_034l6ScLRLhYObdEbC8k1g",
  "expires_at": "2026-10-23T21:26:50.000000Z",
  "total_amount": "402.74",
  "total_currency": "USD",
  "base_amount": "24.07",
  "tax_amount": "378.67",
  "total_emissions_kg": "379",
  "owner": {
    "name": "Lufthansa",
    "iata_code": "LH",
    "logo_symbol_url": "https://assets.duffel.com/img/airlines/for-light-background/full-color-logo/LH.svg"
  },
  "conditions": {
    "change_before_departure": { "allowed": true, "penalty_amount": "300", "penalty_currency": "GBP" },
    "refund_before_departure": { "allowed": false, "penalty_amount": null, "penalty_currency": null }
  },
  "payment_requirements": {
    "requires_instant_payment": false,
    "payment_required_by": "2026-10-27T01:56:00Z",
    "price_guarantee_expires_at": null
  },
  "passenger_identity_documents_required": false,
  "slices": [
    {
      "duration": "PT12H40M",
      "fare_brand_name": "Economy Light",
      "conditions": { "advance_seat_selection": false, "priority_boarding": false, "priority_check_in": false },
      "origin": { "iata_code": "LHR", "name": "Heathrow Airport", "city_name": "London" },
      "destination": { "iata_code": "JFK", "name": "John F. Kennedy International Airport", "city_name": "New York" },
      "segments": [
        {
          "departing_at": "2026-12-15T09:00:00",
          "arriving_at": "2026-12-15T11:55:00",
          "duration": "PT1H55M",
          "origin": { "iata_code": "LHR", "city_name": "London" },
          "origin_terminal": "2",
          "destination": { "iata_code": "ZRH", "city_name": "Zürich" },
          "destination_terminal": null,
          "marketing_carrier": { "name": "SWISS", "iata_code": "LX" },
          "marketing_carrier_flight_number": "0317",
          "operating_carrier": { "name": "SWISS", "iata_code": "LX" },
          "aircraft": { "name": "Airbus A321neo" },
          "passengers": [
            {
              "cabin_class_marketing_name": "ECONOMY",
              "baggages": [ { "type": "checked", "quantity": 0 }, { "type": "carry_on", "quantity": 1 } ],
              "cabin": {
                "amenities": {
                  "wifi": { "available": false, "cost": "n/a" },
                  "seat": { "type": "standard", "legroom": "less", "pitch": "29" },
                  "power": { "available": true }
                }
              }
            }
          ]
        },
        {
          "departing_at": "2026-12-15T13:10:00",
          "arriving_at": "2026-12-15T16:40:00",
          "duration": "PT9H30M",
          "origin": { "iata_code": "ZRH", "city_name": "Zürich" },
          "destination": { "iata_code": "JFK", "city_name": "New York" },
          "destination_terminal": "1",
          "marketing_carrier": { "name": "SWISS", "iata_code": "LX" },
          "marketing_carrier_flight_number": "0014",
          "operating_carrier": { "name": "SWISS", "iata_code": "LX" },
          "aircraft": { "name": "Airbus A330-300" },
          "passengers": [
            {
              "baggages": [ { "type": "checked", "quantity": 0 }, { "type": "carry_on", "quantity": 1 } ],
              "cabin": {
                "amenities": {
                  "wifi": { "available": true, "cost": "paid" },
                  "seat": { "type": "standard", "legroom": "standard", "pitch": "31" },
                  "power": { "available": true }
                }
              }
            }
          ]
        }
      ]
    }
  ]
}
```

El JSON adjunto incluye además estos casos:
- **British Airways:** directo, el más barato, ni cambios ni reembolso.
- **Iberia:** directo, permite cambios y reembolso.
- **Duffel Airways:** aerolínea de prueba.
- **Lufthansa Economy Flex:** 1 escala, flexible.
- **Lufthansa:** 2 escalas con tres operadores distintos (VL, LH, LX), a 6.146 USD.

## Qué necesita la reserva (formulario de pasajeros)

Por cada pasajero son obligatorios:
- tratamiento (`mr`, `ms`, `mrs`, `miss`, `dr`);
- nombre y apellido (solo letras latinas, espacio, `-` y `'`; máximo 40 caracteres entre los dos);
- género (`m`/`f`);
- fecha de nacimiento;
- email;
- teléfono en formato internacional (`+54911…`).

Si la oferta lo exige, también el pasaporte: número, país emisor y vencimiento. Los infantes (0 o 1 año) tienen que quedar asociados a un adulto responsable, con un adulto distinto por cada infante.

**La respuesta de la reserva devuelve:**
- `booking_reference`: el localizador, por ejemplo "RZPNX8";
- `documents[]`: los tickets electrónicos, con un número por pasajero;
- `payment_status`: `awaiting_payment`, `paid_at`, `payment_required_by`;
- `available_actions`: `cancel`, `change`, `update`;
- el itinerario completo.

## Estados y casos borde a contemplar

- Búsqueda en curso (varios segundos), sin resultados y error del proveedor.
- Oferta vencida: el usuario tarda más de 30 minutos en decidir o en completar los datos.
- El precio cambió entre la búsqueda y la reserva, porque se vuelve a consultar la oferta antes de reservar.
- Llegada al día siguiente (+1) y conexiones largas o cortas: mostrar el tiempo de conexión, que se calcula entre segmentos.
- Datos faltantes: terminal, avión o amenities en `null`.
- Muchas ofertas casi iguales que difieren solo en la tarifa.
- Reserva tipo "hold" (reservar sin pagar) frente a pago inmediato.

## Qué espero de cada propuesta

- **Concepto:** una o dos líneas sobre el enfoque. Por ejemplo, "comparación densa tipo tabla" frente a "tarjetas con foco en lo esencial".
- **Pantallas:** las 6 del flujo, en **desktop y mobile**.
- **Datos:** cómo se resuelve la jerarquía de información en la tarjeta de resultado (qué se ve de entrada y qué queda en el detalle).
- **Tarifas:** cómo se muestran las variantes de una misma ruta y horario.
- **Datos reales:** usar los datos del JSON adjunto, no datos inventados.

No hay design system previo; podés proponer uno simple (colores, tipografía, componentes base) como parte de cada propuesta.
