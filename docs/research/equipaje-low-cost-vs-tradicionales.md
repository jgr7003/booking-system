# Equipaje: low cost frente a aerolíneas tradicionales

> Documento de investigación (memoria del proyecto). Investigado el 2026-10-26.
> **Pregunta:** cuando Duffel no informa el equipaje de mano (`carry_on`) de una tarifa, ¿significa que solo incluye un artículo personal, como en las low cost?
> **Respuesta corta: no se puede inferir.** `null` significa "la aerolínea no informó". Se muestra como «Sin dato», con una aclaración, sin suponer nada.

## 1. Qué dice Duffel

De la API reference (Offers / Offer Requests), sobre `slices[].segments[].passengers[].baggages[]`:

| Campo | Definición textual |
|---|---|
| `baggages` | *"The baggage allowances for the passenger on this segment included in the offer. Some airlines may allow additional baggage to be booked as a service - see the offer's `available_services`."* |
| `type` | Solo dos valores: **`checked`** (despachada) y **`carry_on`** (de mano). **No existe un tipo para el artículo personal** (mochila o bolso bajo el asiento). |
| `quantity` | *"The number of items of baggage of the specified `type` allowed on the segment. **Where no allowance information is available for a particular `type`, no entry will be present.**"* |

Conclusiones:

1. **Que falte el ítem significa "sin información"**, no "no incluido". Lo dice Duffel.
2. **`quantity: 0` significa "no incluido"**. Es un dato explícito de la aerolínea.
3. **El artículo personal no se puede saber desde Duffel**, porque no es un tipo de equipaje en su API.
4. El equipaje extra se compra como *service* (`available_services`, que no vienen por defecto). Algunas aerolíneas lo emiten como un documento aparte (EMD), además del ticket.

## 2. Qué muestra nuestra búsqueda real (LHR → JFK, 23/10/2026)

| Aerolínea · tarifa | Despachada | De mano | Cambio | Reembolso |
|---|---|---|---|---|
| British Airways · Basic | 1 | 1 | No | No |
| Iberia · Basic | 1 | 1 | Sí | Sí |
| American · Basic Economy | 1 | 1 | Sí | No |
| Duffel Airways · Basic | 1 | 1 | No | No |
| Lufthansa · Economy Light | **0** | 1 | Sí | No |
| Lufthansa · Economy Comfort | 1 | 1 | Sí | No |
| Lufthansa · Economy Comfort Plus | 1 | 1 | Sí | Sí |
| Lufthansa · **Economy Impact** | 1 | **sin ítem** | Sí | Sí |
| Lufthansa · Economy Flex | 1 | 1 | Sí | Sí |

**Lo que dice esta tabla:**
- El único caso sin `carry_on` (*Economy Impact*) **no es una tarifa básica**: incluye valija despachada y permite cambio y reembolso. Interpretarlo como "solo artículo personal" sería un error.
- *Economy Light* sí trae `checked: 0`, que es un "no incluido" explícito. Ese caso se puede mostrar con seguridad.
- No hay low cost en la muestra. El sandbox de Duffel solo tiene algunas aerolíneas tradicionales y Duffel Airways.

## 3. Industria: low cost frente a tradicionales (2026)

| Tipo | Ejemplos | Incluido en la tarifa más barata |
|---|---|---|
| Low cost europeas | Ryanair, Wizz Air | Solo artículo personal (40×30×20 cm). Equipaje de mano y despachado, pagos |
| Low cost europea "generosa" | easyJet | Bolso bajo el asiento más grande (45×36×20 cm). De mano grande y despachado, pagos |
| Low cost EE.UU. | Spirit | Solo artículo personal |
| Tradicionales, tarifa estándar | British Airways, Iberia, Delta, American | Artículo personal + equipaje de mano. La despachada depende de la tarifa y la ruta |
| Tradicionales, **tarifa básica nueva** | **Lufthansa Economy Basic** (desde el 18/05/2026, corto y medio radio) | **Solo artículo personal** (40×30×15 cm, la franquicia gratuita más chica de Europa); sin cambios ni reembolso |
| Tradicionales, tarifa "light" | Lufthansa Economy Light | Equipaje de mano sí, despachada no |
| United Basic Economy | Doméstico EE.UU. | Solo artículo personal. En transatlánticos varía según la ruta (las fuentes no coinciden) |

**Conclusión de industria:** la diferencia ya no pasa por "low cost frente a tradicional", sino por la **familia de tarifa**. Las tradicionales también venden tarifas de "solo artículo personal" (Lufthansa Economy Basic, United Basic Economy). No sirve un atajo del tipo "si es low cost, entonces solo artículo personal".

**Regulación UE:** en enero de 2026 el Parlamento Europeo aprobó su posición para exigir, sin costo, un artículo personal y un equipaje de mano pequeño (hasta 100 cm sumando dimensiones y 7 kg). **Todavía no es ley:** falta el acuerdo con el Consejo. Hay que revisarlo, porque si se aprueba cambia lo que "incluye" cualquier tarifa en la UE.

## 4. Decisión para la plataforma

| Dato del proveedor | DTO | Frontend | Aclaración (tooltip) |
|---|---|---|---|
| `quantity ≥ 1` | `n` | «n incluida(s)» | — |
| `quantity = 0` | `0` | «No incluida» | «Se puede agregar con cargo al reservar» (cuando haya `available_services`) |
| Sin ítem | `None` | «Sin dato» | «La aerolínea no informa este equipaje para la tarifa. Revisá sus condiciones de transporte», con enlace a `conditions_of_carriage_url` |
| Artículo personal | — (no existe) | No se muestra como incluido | — |

**Reglas:**
1. **Nunca inferir equipaje** a partir del tipo de aerolínea, el nombre de la tarifa o el precio. Solo se muestra lo que informa el proveedor.
2. El `Carrier` del vendedor (`owner`) suma `conditions_of_carriage_url`, que Duffel ya envía y hoy descartamos. Es el enlace del tooltip de «Sin dato».
3. **Filtro "Con valija":** solo considera `checked ≥ 1`. Las tarifas con `None` **no** se cuentan como "con valija".

**Ideas para el futuro** (no se implementan ahora):
- Tabla `airlines` con `is_low_cost` y la política pública de artículo personal, para mostrar una **pista** («En esta aerolínea, la tarifa básica suele incluir solo un artículo personal»), claramente marcada como orientativa y no como dato de la tarifa.
- Consultar `available_services` del detalle de la oferta para saber si el equipaje se puede agregar y a qué precio.

## 5. Fuentes

- Duffel API reference: Offers y Offer Requests, campos `baggages`, `type` y `quantity`. Consultado en duffel.com/docs/api/v2 el 2026-10-26.
- [Duffel: Adding Extra Bags](https://duffel.com/docs/guides/adding-extra-bags): equipaje como `available_services` y EMD.
- [Euronews (30/04/2026): Lufthansa lanza la franquicia gratuita más chica de Europa](https://www.euronews.com/travel/2026/04/30/this-airline-just-launched-europes-smallest-free-cabin-allowance-and-its-not-a-budget-carr): Economy Basic, 40×30×15 cm; comparación con Ryanair, Wizz y easyJet; posición del Parlamento Europeo.
- [Which? (2026): equipaje de mano de Ryanair, easyJet, British Airways y Wizz Air](https://www.which.co.uk/reviews/airlines/article/most-generous-airline-hand-luggage-aF9jK9M1uoMk).
- [Carry-On Size Rules by Airline: 2026 Guide](https://horizn-studios.com/blogs/journal/carry-on-size-2026-guide): aerolíneas tradicionales de EE.UU. con equipaje de mano + artículo personal.
- [Thrifty Traveler: United Basic Economy](https://thriftytraveler.com/guides/airlines/united-basic-economy/) y [Going: guía de Basic Economy internacional](https://www.going.com/guides/the-ultimate-guide-to-basic-economy-on-international-flights-from-the-us). Las fuentes no coinciden para los transatlánticos de United.
- [Lufthansa Group: viajar en intercontinental solo con equipaje de mano](https://newsroom.lufthansagroup.com/en/travelling-on-an-intercontinental-journey-with-hand-luggage-only/): Economy Light.
- Muestra propia: `docs/samples/offer-request-response.full.json`.

> Las políticas de equipaje de las aerolíneas cambian seguido. Este documento describe la situación a octubre de 2026.
