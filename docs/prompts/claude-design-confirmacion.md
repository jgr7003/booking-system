# Prompt para Claude Design: rediseño de la pantalla de confirmación

**Cómo usarlo:** copiar todo lo que está debajo de la línea en Claude Design y adjuntar:

1. `docs/frontend/Vuelos · Propuesta A.html`: el sistema de diseño vigente y los demás tableros.
2. `docs/samples/booking-confirmed-roundtrip.sample.json`: respuesta real de `GET /api/v1/flights/bookings/{id}` de una ida y vuelta Bogotá ⇄ Cali confirmada en Duffel (modo test).
3. Una captura de la pantalla actual (la de esta conversación o una nueva desde `/bookings/{id}`).

---

## Contexto

Es una aplicación web de **búsqueda y reserva de vuelos** en español, para un viajero final. Ya existe la **Propuesta A** (adjunta) con todos sus tableros: búsqueda, espera, resultados, detalle, Tu viaje, pasajeros y pago, confirmación y estados. Esa propuesta ya está implementada.

Necesito **mejorar solo la pantalla de Confirmación** (tablero "A · Confirmación" y su versión mobile, "7 · Confirmación" del tablero "A · Mobile"). El resto del sistema no cambia. Hay que respetar sus tokens, tipografía y componentes, para que la pantalla nueva se sienta parte del mismo producto.

## Qué está mal hoy (ver la captura adjunta)

1. **La ida y la vuelta no se distinguen.** El itinerario es una tabla con un renglón por segmento, sin etiquetas «Ida» y «Vuelta» y **sin fecha por tramo**. En la muestra, la vuelta es el 15 nov y no aparece en ninguna parte: el título solo muestra la fecha de ida («Bogota → Cali · mar 10 nov 2026»).
2. **El título no comunica el viaje completo.** No dice si es solo ida o ida y vuelta, ni las fechas de cada tramo.
3. **Jerarquía pobre.** El estado («Reserva confirmada y pagada») es una línea chica. El código de reserva compite con el título, y la columna izquierda deja mucho espacio vacío debajo.
4. **No hay próximos pasos.** El viajero no sabe qué hacer ahora: qué equipaje incluye su tarifa, qué condiciones de cambio y reembolso tiene, qué necesita para el aeropuerto.
5. **«Gestionar» parece roto.** Los tres botones deshabilitados se ven lavados. Hay que comunicar mejor que esas acciones llegan próximamente, sin que parezca un error.
6. **Barra superior:** «Mis reservas · próximamente» se corta en anchos intermedios.
7. **Mobile:** la tabla del itinerario no sirve en 390 px. Hace falta una vista por tramo.

## Datos disponibles (no inventar otros)

La pantalla se arma **solo** con esta respuesta. Lo que no está acá no existe en la API: no hay email del pasajero, ni asientos, ni enlaces de check-in, ni PDF del ticket.

| Dato | Campo | Notas |
|---|---|---|
| Estado | `status` | Acá siempre `confirmed`. Ver "Estados" para los demás |
| Código de reserva (PNR) | `booking_reference` | 6 caracteres, ej. `GNA3VA` |
| Pasajero | `passenger.title`, `given_name`, `family_name` | **En mayúsculas y sin tildes**, como lo recibe la aerolínea (`PEPE PEREZ`, `MUNOZ`) |
| Total cobrado | `price` (`amount` texto, `currency`) | Precio de venta. Se muestra en su moneda, sin convertir: «59,82 USD» |
| Vendedor | `order.owner.name`, `order.owner.logo_url` (SVG), `order.owner.conditions_of_carriage_url` | |
| Tramos | `order.slices[]` | 1 = solo ida; 2 = ida y vuelta |
| Por tramo | `origin`, `destination` (código, `name`, `city`, `terminal`), `duration_minutes`, `stops`, `fare_brand` (ej. «Basic»), `connections[]` (aeropuerto y minutos de conexión) | `city` puede venir vacía y los nombres vienen en inglés («Bogota») |
| Por segmento | `departing_at` / `arriving_at`, `marketing_carrier` + `flight_number`, `operating_carrier`, `aircraft`, `duration_minutes` | Horarios **en hora local del aeropuerto**, como texto, sin zona horaria. Puede llegar al día siguiente (+1). `terminal` y `aircraft` pueden ser `null` («terminal s/d») |
| Equipaje por segmento | `segments[].passengers[].baggage.checked` / `carry_on` | `null` = la aerolínea no informa («Sin dato»); `0` = no incluido. Nunca suponer |
| Cabina | `segments[].passengers[].cabin_name` / `cabin_class` | ej. «Economy» |
| Comodidades | `segments[].passengers[].amenities` (wifi, power, seat_pitch) | Suelen venir vacías |
| Condiciones | `order.conditions.change` / `refund`: `allowed` (bool o `null`) y `penalty` (monto o `null`) | `penalty` puede estar en otra moneda que el total |
| Tickets | `order.tickets[]`: `passenger_id`, `number` | En modo test el número es «1». Puede venir vacío: «Se emiten al pagar» |
| Pago | `order.paid_at` (instante UTC), `order.awaiting_payment` | |
| Acciones | `order.available_actions`: `cancel`, `change`, `update` | **Solo se muestran las que vienen.** Hoy no se pueden ejecutar (próximamente) |

## Reglas que no cambian

- **Requisito regulatorio:** en la confirmación tienen que verse el **código de reserva**, el **itinerario completo** y la **aerolínea que opera cada segmento** («operado por …»).
- Horarios en hora local, leídos como texto; fechas en formato «mar 10 nov 2026».
- Montos en su moneda, con el número primero: «59,82 USD».
- `null` → «Sin dato»; `0` en equipaje → «No incluida»; penalidad `0` → «Gratis».
- Nunca se muestran el costo para la plataforma ni su ganancia.
- Las acciones de «Gestionar» salen de `available_actions`. Si no viene ninguna, la sección no se muestra.
- «Mis reservas» todavía no existe (no hay cuentas de usuario).
- Textos en español rioplatense neutro, como el resto de la propuesta («Revisá», «Copiar»).

## Estados a diseñar

1. **Confirmada y pagada, ida y vuelta** (la muestra adjunta): el caso principal.
2. **Confirmada, solo ida con una escala:** conexión entre segmentos, con su aeropuerto y duración; resaltada si dura menos de 60 min.
3. **Datos faltantes:** terminal y avión `null`, equipaje `null`, ciudad vacía.
4. **Confirmando con la aerolínea:** el viajero llega por el link antes de que termine el proceso. La página se actualiza sola.
5. **No se pudo reservar:** con su motivo (tarifa no disponible, tarjeta rechazada, la aerolínea rechazó los datos). Indicar que no se cobró nada y ofrecer volver a «Tu viaje».

## Ideas que espero ver (no son obligatorias)

- Un encabezado que resuma el viaje completo: origen ⇄ destino, fechas de ida y vuelta, pasajero, estado y código de reserva con «Copiar» bien visible.
- El itinerario agrupado por tramo («Ida · mar 10 nov», «Vuelta · dom 15 nov»), reutilizando la línea de tiempo de los tableros de resultados y detalle.
- Un bloque «Qué incluye tu tarifa»: equipaje de mano y despachado, cambio y reembolso con su costo, con los mismos íconos y colores (✓/✗/«Sin dato») que la matriz de tarifas.
- «Antes de volar»: llevar el documento con el nombre tal como figura en el ticket y presentarse con tiempo. **Solo texto informativo genérico**, sin datos que la API no da.
- Acciones de «Gestionar» como opciones informativas («Disponible próximamente»), no como botones rotos.
- En mobile, el código de reserva arriba y bien grande, tarjetas por tramo, y el total y las acciones al final.

## Entregables

- **Desktop 1280 px** y **mobile 390 px** para el estado 1, y los estados 2 a 5 en la resolución que mejor los explique.
- El mismo formato de tablero que la Propuesta A, con los estilos de cada elemento legibles en el template. Se implementa replicando medidas, colores, tipografía y textos.
- Las notas para desarrolladores van **separadas** del dibujo, no dentro de la interfaz.
- Si una decisión contradice una regla de esta lista, anotarlo explícitamente.
