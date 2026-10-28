# Revisión del frontend contra buenas prácticas de React

> Inventario del **2026-10-28**, hecho sin modificar código. Es una lista de trabajo: se marca lo que se corrige, se anota lo que se descarta y se decide qué entra **antes de cerrar la etapa 2**.
> Criterios: la lista de buenas prácticas de React que pasó el autor (estructura, estado, hooks, rendimiento, TypeScript, calidad, accesibilidad, errores, seguridad, estilos y herramientas).
> Reglas del proyecto para el frontend: [AGENTS.md](../../AGENTS.md) (sección «Frontend») y [00-global.md §10](../architecture/00-global.md#10-frontend).

## Cómo se usa

- **Estado:** `[ ]` pendiente · `[~]` en curso · `[x]` hecho · `[-]` descartado (con motivo en «Notas»).
- **Etapa 2:** qué se decide para el cierre. `Sí` = se corrige antes de cerrar · `No` = queda para después · `?` = sin decidir.
- **Esfuerzo:** `S` ≤ 1 hora · `M` unas pocas horas · `L` un día o más. Son estimaciones, no compromisos.
- Cada corrección va con sus tests y **no cambia el comportamiento visible**, salvo F-01 y F-02, que arreglan errores.
- Al terminar un ítem: marcar el estado, anotar la fecha y el resultado en «Registro» y, si cambia una regla, actualizar `AGENTS.md`.

## Resumen

| Prioridad | Ítems | Hechos |
|---|---|---|
| P1 · Errores y robustez | F-01 a F-06 | 0 de 6 |
| P2 · Estructura y mantenimiento | F-07 a F-15 | 5 de 9 |
| P3 · Herramientas y calidad | F-16 a F-23 | 0 de 8 |

**Valores de partida** (para comparar después de corregir):

| Medida | Hoy |
|---|---|
| Bundle | 1 archivo JS de **837 KB** (251 KB comprimido) y 63 KB de CSS. En la etapa 1 eran 588 KB |
| Tests de frontend | 107 en 12 archivos |
| Archivo más grande | `BookingPage.tsx`, 943 líneas y 16 componentes |
| `any` | 0 |
| `useEffect` | 7 |
| `biome-ignore` | 5, todos justificados |
| Importaciones entre carpetas de `features/` | 29 (20 entre features distintas) |

## P1 · Errores y robustez

| Estado | ID | Hallazgo | Dónde | Propuesta | Esf. | Etapa 2 |
|---|---|---|---|---|---|---|
| `[ ]` | **F-01** | **Sin Error Boundary ni pantallas de error y de «no encontrado» en el router.** Un error al renderizar deja la app en blanco | `router.tsx` | `defaultErrorComponent` y `defaultNotFoundComponent` del router, más un Error Boundary en el layout, con un botón para reintentar. Texto en español | S | ? |
| `[ ]` | **F-02** | **Errores de red que se ven como otra cosa.** (a) Si el `GET` de la reserva falla con algo distinto de 404, la pantalla 6 muestra «Estamos confirmando…» para siempre. (b) El checkout ignora el error de esa consulta. (c) El detalle de vuelo muestra «Este vuelo ya no está en los resultados» ante una caída de red | `BookingPage`, `CheckoutPage`, `FlightDetailPage` | Un estado de error con «Reintentar» en cada una, distinguiendo «no existe» de «no pudimos consultar». En la pantalla 6, mantener el último estado conocido si ya había datos | M | ? |
| `[ ]` | **F-03** | **El payload del SSE se lee sin validar:** `JSON.parse(...) as { status }` | `api/bookings.ts` | Esquema Zod mínimo del evento (`booking_id`, `status`, `version`). Si no cumple, se ignora y se confía en la consulta de respaldo | S | ? |
| `[ ]` | **F-04** | **Las tiendas de `sessionStorage` se rehidratan sin validar** (`version: 1` y sin `migrate`). Un dato viejo o corrupto puede romper la pantalla | `trip/store.ts`, `checkout/store.ts` | Validar con Zod al rehidratar y descartar lo inválido; `migrate` ante un cambio de versión | M | ? |
| `[ ]` | **F-05** | **Bundle de 837 KB en un solo archivo.** No hay `lazy` ni división por ruta. Los sospechosos son `libphonenumber-js`, Zod y React Hook Form, pero **no está medido** | `router.tsx`, `vite.config.ts` | (1) Medir con un visualizador qué pesa. (2) Cargar por ruta con `lazyRouteComponent` (checkout, confirmación, detalle). (3) Evaluar `libphonenumber-js/min` o un cálculo más liviano. Objetivo: que la ruta inicial baje de la etapa 1 (588 KB) | M | ? |
| `[ ]` | **F-06** | **Datos personales en `sessionStorage`:** el borrador del checkout guarda nombre, nacimiento, email, teléfono y pasaporte | `checkout/store.ts` | **Decisión de privacidad.** Hoy cumple el tablero («si vence mientras se completan los datos, lo cargado se conserva»). Opciones: dejarlo; guardar solo en memoria y perder el borrador al recargar; o excluir el pasaporte y la fecha de nacimiento | S | ? |

## P2 · Estructura y mantenimiento

| Estado | ID | Hallazgo | Dónde | Propuesta | Esf. | Etapa 2 |
|---|---|---|---|---|---|---|
| `[x]` | **F-07** | `BookingPage.tsx` tiene **943 líneas y 16 componentes** (confirmada, confirmando, fallida, error de emisión, tarjeta de tramo, línea de tiempo…) | `features/booking/` | Un archivo por componente: `Confirmed`, `SliceCard`, `Included`, `BeforeFlying`, `Manage`, `Confirming`, `Failed`, `IssuanceError`. `BookingPage` queda como el selector de estado | M | ? |
| `[x]` | **F-08** | `FlightDetailPage.tsx`: **607 líneas y 9 componentes** | `features/flights/detail/` | Partir en `Itinerary`, `FareTable`, `FareConditions`, `PriceAside`, `FlightHeading` | M | ? |
| `[x]` | **F-09** | `TripPage.tsx` (447 líneas). La **lógica de datos vive dentro de `TripItemCard`**: refresco de precio con `fetchQuery`, toasts y tienda | `features/trip/` | Hook `useRefreshTripItem`; separar `TripItemCard` y `TripSummary` en archivos | M | ? |
| `[ ]` | **F-10** | `CheckoutPage.tsx` mezcla formulario, intento, SSE, navegación por estado y diálogo de precio | `features/checkout/` | Hook `useCheckoutFlow` (intento, creación, estado de la reserva, navegación) y la página queda de composición | M | ? |
| `[x]` | **F-11** | **Features acopladas.** `trip`, `checkout` y `booking` importan componentes y lógica de `flights/results` (`FlightCard`, `SliceTimeline`, `ResultStates`, `fareName`, `bagCell`…) y los tipos de `search/params` | 29 importaciones entre carpetas (20 entre features distintas) | Capa compartida: `components/flight/` (tarjeta, línea de tiempo, insignias) y `lib/` o `shared/` para la lógica de tarifas y los tipos de búsqueda. Una feature no importa de otra | L | ? |
| `[x]` | **F-12** | **Duplicación:** `lowest()` dos veces (`booking/logic.ts`, `results/logic.ts`); `todayIso` y `todayOf` hacen lo mismo; **tres** contadores de vencimiento (`ExpiryBadge`, `HeaderExpiry`, el de `TripPage`); `Notice` del checkout y las franjas de estado de la pantalla 6 | varios | Una sola implementación de cada una, en la capa compartida de F-11 | M | ? |
| `[ ]` | **F-13** | **Un efecto que sincroniza la URL con estado local:** copia `search.hl` a `openKey` y `watchedKey` | `ResultsPage.tsx` (~línea 218) | Derivar de la URL en el render y dejar el efecto solo para el desplazamiento | S | ? |
| `[ ]` | **F-14** | **6 colores fijos en JSX**, aunque existen los tokens. Ej.: `text-[#93B4FF]` (ya existe `action-light`), `border-[#C27A00]`, `fill`/`stroke` de SVG con hex | `toast.tsx`, `BookingPage.tsx`, `FlightDetailPage.tsx`, `Steps.tsx` | Usar tokens de `@theme` y `currentColor` en los SVG; agregar el token que falte | S | ? |
| `[ ]` | **F-15** | `FlightCard` tiene props de configuración (`opensDialog`, `priceCaption`, `actionLabel`, `sliceLabels`) para dos usos distintos. Es el principio de «mil flags» | `results/FlightCard.tsx` | Composición: tarjeta base y `children` o *slots* para el pie y el precio. Hacerlo junto con F-11 | M | ? |

## P3 · Herramientas y calidad

| Estado | ID | Hallazgo | Propuesta | Esf. | Etapa 2 |
|---|---|---|---|---|---|
| `[ ]` | **F-16** | **Sin CI.** No hay `.github/` | GitHub Actions: `make lint` (límites entre módulos, tipos, Biome) y `make test` en cada PR, con Docker Compose | M | ? |
| `[ ]` | **F-17** | **Sin pre-commit.** No hay Husky ni lint-staged | Biome y chequeo de tipos sobre los archivos que cambian. Va después de F-16 y respeta la regla de que no se commitea sin que el autor lo pida | S | ? |
| `[ ]` | **F-18** | **Sin E2E en el repo.** El recorrido con Playwright se hizo siempre a mano | Suite mínima: buscar, guardar, reservar, tarjeta rechazada. Necesita Duffel de prueba o la API con el proveedor falso | L | ? |
| `[ ]` | **F-19** | **`FlightDetailPage` no tiene ningún test**, y los hooks (`useBookingEvents`, `useAddToTrip`, `useNow`) solo se prueban de refilón | Tests de la pantalla de detalle (tarifa elegida, vuelo no encontrado, error) y de los hooks | M | ? |
| `[ ]` | **F-20** | `SearchForm` usa estado local + Zod, no React Hook Form (decisión de la etapa 1) | Migrar solo si se aprovecha la validación por campo. Baja prioridad | M | No |
| `[ ]` | **F-21** | Sin Storybook para documentar `components/ui` | Evaluar cuando haya un equipo más grande | M | No |
| `[ ]` | **F-22** | **Las respuestas de la API no se validan en runtime**: los tipos salen de `openapi-typescript` y se confía en el backend | Validar solo en el borde más crítico (la reserva) con un esquema derivado del OpenAPI, o descartarlo si los contratos se prueban del lado del backend | M | ? |
| `[ ]` | **F-23** | **Aserciones de tipo (`as`)** donde un esquema o un estrechamiento dan el tipo: `values.title as PassengerTitle` y `gender as "m" \| "f"` tras validar, `values as CheckoutValues` en el borrador, `error as ApiError` | Derivar el tipo de la salida de Zod; `instanceof` en lugar de `as`. Muchos `as number[]` y `as string` existen por `noUncheckedIndexedAccess` y están bien | S | ? |

## Lo que ya cumple (no hay que tocar)

| Práctica | Evidencia |
|---|---|
| TypeScript estricto | `strict`, `noUncheckedIndexedAccess`, `noUnused*`; **cero `any`** |
| Estado del servidor ≠ estado de UI | TanStack Query para datos remotos; Zustand para «Tu viaje» y el checkout; filtros y orden en la URL con Zod |
| Organización por feature | `features/<flujo>` con `logic.ts` puro y probado |
| Lint y accesibilidad | Biome con el preset recomendado (incluye las reglas de a11y); pasa limpio. Los 5 `biome-ignore` están justificados |
| HTML semántico | Sin `div` ni `span` con `onClick`; Radix para los diálogos y popovers |
| Efectos | Solo 7; con limpieza donde corresponde |
| Memoización | Solo en `ResultsPage` y `RoundTripSteps`, justificada por una medición (ordenar bajó de 30 s a 1,2 s) |
| Keys | 2 por índice, ambas justificadas (columnas fijas, menores sin identidad) |
| Formularios | Checkout con React Hook Form + Zod |
| Tests | Vitest + Testing Library + MSW sobre comportamiento del usuario, con un test que garantiza que ninguna request sale sin mock |
| Seguridad | Sin `dangerouslySetInnerHTML`, sin secretos ni `VITE_*`, tarjeta nunca guardada, enlaces externos con `rel="noreferrer"` |
| Estilos | Tailwind con tokens en `@theme`; `style` inline solo para valores calculados |
| Herramientas | Vite, alias `@/`, tipos generados del OpenAPI |

## Descartado a propósito

| Tema | Motivo |
|---|---|
| Virtualizar listas | Medido con 276 vuelos: ordenar 0,45 s, filtrar 0,5 s. Además la ida y vuelta se muestra en dos pasos |
| Quitar la memoización manual ahora | Tiene una medición detrás. React Compiler podría reemplazarla más adelante |
| Optimizar imágenes | La interfaz no usa `<img>` (las aerolíneas se muestran con su código) |

## Otros puntos a tener en cuenta

- Los enlaces a las condiciones de transporte (`conditions_of_carriage_url`) vienen del proveedor y no se valida su esquema. Conviene aceptar solo `https:` cuando se haga F-22 o F-23.
- La pantalla «Error de emisión» no tiene tablero de diseño; su texto es provisional (ver [02-reserva-vuelos.md §8.2](../architecture/02-reserva-vuelos.md)).

## Orden sugerido

1. **F-01, F-02, F-03, F-04**: arreglan errores reales y son chicos.
2. **F-05** (medir primero) y **F-06** (decidir).
3. **F-07 a F-10**: partir archivos y extraer hooks, sin cambiar comportamiento.
4. **F-11, F-12, F-15, F-14, F-13**: capa compartida y limpieza.
5. **F-16, F-17, F-19**: CI, pre-commit y tests del detalle. **F-18** (E2E) y el resto, después.

## Cómo verificar cada cambio

```bash
make test           # backend y frontend
make lint           # límites entre módulos, tipos y Biome
# bundle (F-05), sin ensuciar el repo:
cd frontend && MSYS_NO_PATHCONV=1 docker compose exec -T frontend pnpm exec vite build --outDir /tmp/chk --emptyOutDir
```

Además, para los cambios visibles (F-01, F-02, F-07 a F-10): captura en navegador real en desktop y mobile, comparada contra los tableros, como pide `AGENTS.md`.

## Registro

| Fecha | Ítem | Qué se hizo | Resultado |
|---|---|---|---|
| 2026-10-28 | — | Inventario inicial | 23 ítems |
| 2026-10-28 | F-07, F-08, F-09 | Bloques movidos tal cual (verificado línea por línea; solo cambió una firma que Biome partió en varias líneas). **Confirmación** (`booking/`): `BookingPage` (elige el estado y «no encontrada»), `Confirmed`, `SliceCard`, `Included`, `BeforeFlying`, `Manage`, `Confirming`, `Failed`, `IssuanceError` y `styles.ts`. **Detalle** (`flights/detail/`): `FlightDetailPage`, `FlightHeading`, `Itinerary`, `FareTable`, `FareConditions`, `PriceAside`, `styles.ts` y `logic.ts` (comodidades, penalidades, beneficios, horas UTC). **Tu viaje** (`trip/`): `TripPage`, `TripItemCard`, `TripSummary`, `logic.ts` (`conditionsLine`, `totalsByCurrency`) y el hook `useRefreshTripItem`, con `useMutation` en lugar del estado manual | 122 tests de frontend (15 nuevos: las dos `logic.ts` y el refresco de precio, con éxito y error); tipos y Biome limpios. Probado en Chrome, desktop y mobile. El archivo más grande de los tres bajó de 943 a 253 líneas (`Confirmed.tsx`) |
| 2026-10-28 | F-11 | **Capa compartida:** `lib/flights/fares.ts` (equipaje, cambios, reembolso, nombre de tarifa), `lib/flights/itinerary.ts` (escalas, operadores, números de vuelo), `lib/flights/search.ts` (los criterios de búsqueda, antes `features/flights/search/params.ts`), `lib/cell.ts` (`Tone`, `Cell`), `components/flight/` (`SliceTimeline`, `AirlineBadge`). **Dependencias del flujo** por `public.ts`, como el `public.py` del backend: `features/trip/public.ts` (el viaje y `useAddToTrip`) y `features/booking/public.ts` (`SlowBookingNotice`). Se corrigieron dos imports al revés (`components/ui/tone` y `HeaderExpiry` importaban de una feature). **Reglas en Biome** (`noRestrictedImports`), probadas con un archivo que las viola | De 20 imports entre features a 10, todos por `public.ts`; `components/`, `lib/` y `api/` no importan ninguna feature. Tests de tarifas e itinerario movidos con su código |
| 2026-10-28 | F-12 | Una sola implementación de: `lowest` (en `lib/flights/fares`), la fecha de hoy (`todayIso` en `lib/dates`, antes `todayIso` y `todayOf`), las horas UTC de una oferta (`utcTime`, `utcDateTime` en `lib/format`; había dos `utcTime`), los colores por tono (`booking` usaba su propio `Tone` y `TONE_TEXT`; ahora `toneTextClass`, mismas clases), la **regla del vencimiento** (`expiryOf` / `useExpiry` en `lib/useExpiry`, usada por los 6 contadores; cada uno conserva su texto y su diseño), el aviso ámbar o rojo (`components/ui/notice.tsx`, usado por el checkout y «Está tardando más de lo habitual») y la franja de una reserva que terminó mal (`booking/ProblemHeader.tsx`, usada por «No se pudo reservar» y «Error de emisión»). La franja de «confirmada» queda aparte: el tablero le da otras medidas | 128 tests (6 nuevos: `expiryOf` y `todayIso`), `make lint` limpio. Probado en Chrome: confirmación, reserva fallida, detalle, Tu viaje y checkout |
