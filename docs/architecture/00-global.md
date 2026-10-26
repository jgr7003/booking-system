# Arquitectura global

> Reglas que aplican a todo el proyecto. Los detalles de cada etapa están en los documentos `NN-*.md` de esta carpeta.
> Última actualización: 2026-10-26

## 1. Objetivo

Plataforma de **viajes empresariales** (vuelos y, más adelante, hoteles), de una o varias personas, con frontend y backend propios. Los viajes se guardan para consultar después el historial, como particular o como empresa. La versión actual es la "vainilla": un viaje de una persona con un vuelo.

La plataforma:

1. **No depende de un proveedor concreto.** Cada vertical define su contrato y cada proveedor se conecta con el **patrón Adapter**.
2. **Expone datos normalizados** mediante DTOs propios. El frontend nunca ve el formato del proveedor.
3. **Vende con ganancia.** Internamente se lleva el **precio de compra** (`cost`) y el **precio de venta** (`price`). Hacia afuera solo sale el de venta.
4. **No duplica operaciones con efectos.** Toda operación que cobra o reserva es idempotente (ver §7).

## 2. Vista general

```mermaid
flowchart LR
    U((Viajero)) --> FE

    subgraph repo[booking-system]
        FE[frontend/<br/>React + Vite]

        subgraph BE[backend/ · FastAPI]
            API[app/main.py<br/>routers por módulo]
            CORE[app/core<br/>config · HTTP · errores · pricing · cache · db]
            FL[app/flights]
            HO[app/hotels · futuro]
            WK[workers<br/>outbox relay · reservas<br/><i>etapa 2</i>]
        end

        PG[(PostgreSQL)]
        RD[(Redis)]
        MQ[[RabbitMQ<br/><i>etapa 2</i>]]
    end

    FE -- "HTTP JSON /api/v1/..." --> API
    API -. "SSE /events (etapa 2)" .-> FE
    API --> FL & HO
    FL & HO --> CORE
    CORE --> PG & RD
    WK --> PG & MQ
    API -.-> MQ
    FL -- HTTPS --> DAPI[(Duffel API)]
    HO -- HTTPS --> HAPI[(Proveedor de hoteles<br/><i>a definir</i>)]
```

| Componente | Rol | Desde |
|---|---|---|
| `frontend/` | SPA. Consume solo la API propia | Etapa 1 |
| `backend/` (API) | FastAPI. Módulos por vertical | Etapa 1 |
| PostgreSQL | Fuente de verdad: catálogos (aeropuertos), reservas, outbox/inbox | Etapa 1 (aeropuertos) |
| Redis | Caché (cache-aside) de lecturas frecuentes | Etapa 1 (aeropuertos) |
| RabbitMQ | Transporte de eventos entre API y workers | Etapa 2 |
| Workers | Procesos aparte: outbox relay y procesamiento de reservas | Etapa 2 |

Todo corre en Docker. Un `docker-compose.yml` en la raíz levanta todos los servicios y `make up` es el punto de entrada.

## 3. Estructura del repositorio

```
booking-system/
├── Makefile                 # punto de entrada: make up / down / test / logs ...
├── docker-compose.yml       # todos los servicios
├── AGENTS.md / CLAUDE.md    # memoria y convenciones para agentes de código
├── docs/
│   ├── architecture/        # este documento + uno por etapa
│   ├── frontend/            # propuestas de diseño (Claude Design)
│   ├── prompts/
│   ├── research/            # investigaciones que sirven de memoria (p. ej. equipaje)
│   ├── samples/             # respuestas reales de proveedores
│   └── duffel-busqueda-y-reserva.md
├── backend/
│   └── app/
│       ├── main.py
│       ├── core/            # transversal: config, http, errors, money, pricing, db, cache, health
│       ├── flights/         # módulo de vuelos
│       └── hotels/          # futuro, misma estructura
└── frontend/
    └── src/
        ├── api/             # cliente generado del OpenAPI + hooks
        ├── features/        # una carpeta por vertical/flujo (flights, trip...)
        ├── components/ui/
        ├── lib/
        └── routes/
```

### 3.1 Estructura de un módulo del backend

Todos los módulos (`flights`, `hotels`…) repiten esta forma:

```
app/<módulo>/
├── core/config.py           # settings del módulo (credenciales del proveedor, timeouts)
├── domain/
│   ├── constants.py         # constantes de negocio
│   ├── validators.py        # reglas de validación y tipos validados
│   ├── dtos.py              # DTOs: lo que circula entre capas
│   ├── errors.py            # errores de dominio
│   └── models.py            # modelos de base de datos (SQLAlchemy); solo persistencia
├── providers/
│   ├── base.py              # puerto (Protocol)
│   └── <proveedor>/         # adapter: client.py (HTTP), mapper.py (puro), provider.py
├── repositories/            # acceso a PostgreSQL (+ caché Redis cuando aplica)
├── services/                # casos de uso
├── api/                     # routes.py, schemas.py (públicos), dependencies.py, errors.py
└── tests/                   # unit/, integration/, fixtures/, support.py, conftest.py
```

## 4. Reglas de dependencias entre capas

```mermaid
flowchart LR
    api --> services --> domain
    services --> ports{{providers/base}}
    services --> repositories --> domain
    adapter[providers/&lt;proveedor&gt;] -.implementa.-> ports
    adapter --> domain
```

- `domain` no importa nada del módulo. Puede usar `app.core` (por ejemplo `Money` o `AppError`).
- `services` conoce el **puerto** y los repositorios, **nunca** un adapter concreto.
- El formato de un proveedor solo existe dentro de su carpeta `providers/<proveedor>/`.
- `api/dependencies.py` es el único lugar donde se elige qué adapter, repositorio o política se usa.
- Un módulo no importa otro módulo. Lo compartido sube a `app/core`.

## 5. Patrones

| Patrón | Dónde | Etapa |
|---|---|---|
| **Módulos por vertical** | `app/flights`, `app/hotels` | 1 |
| **Adapter** (Ports & Adapters) | `<módulo>/providers/` | 1 |
| **DTO** (interno con costo, público sin costo) | `domain/dtos.py`, `api/schemas.py` | 1 |
| **Mapper** puro | `providers/<proveedor>/mapper.py` | 1 |
| **Strategy** de precios | `app/core/pricing/` | 1 |
| **Inyección de dependencias** | `api/dependencies.py` (`Depends`) | 1 |
| **Repository** | `<módulo>/repositories/` | 1 |
| **Cache-aside** | Repositorios de lectura (Redis) | 1 |
| **Idempotency Key** | Endpoints que reservan o cobran | 2 |
| **Transactional Outbox** / **Inbox** | Reservas: estado + evento en la misma transacción | 2 |
| **Server-Sent Events** | Notificación de la reserva al frontend | 2 |

## 6. Precios

- Los providers devuelven siempre el **costo**. La ganancia la aplica el servicio con una `PricingPolicy` de `app/core/pricing/`.
- Política vigente: **cargo fijo + % aleatorio determinístico**. Las constantes `FIXED_FEE`, `MIN_PERCENT` y `MAX_PERCENT` están en `fixed_fee_random_percent.py`. La semilla es `HMAC(PRICING_SECRET, "provider:offer_id")` y el resultado se redondea a 2 decimales.
- La misma oferta siempre tiene la misma ganancia, en la búsqueda, al refrescarla y al reservar.
- Los impuestos se muestran reales y la ganancia va dentro de la tarifa base.
- **Los schemas públicos no tienen campos de costo ni de ganancia.**

## 7. Idempotencia y efectos

- **Lecturas** (búsqueda, aeropuertos): se pueden repetir sin efectos.
- **Agregar a "Tu viaje":** es un *upsert* por una clave natural del ítem (`provider:itinerary_key`). Volver atrás y elegir la misma oferta, hacer doble clic o volver a buscar el mismo vuelo **nunca duplica** un ítem. En la etapa 1 el control está en el store del frontend; desde la etapa 2, en PostgreSQL con `UNIQUE (trip_id, item_key)`.
- **Escrituras con efectos** (reservar, cobrar): exigen un header `Idempotency-Key`. La clave se guarda en **PostgreSQL con restricción `UNIQUE`**, que es la fuente de verdad. Si llega dos veces, se devuelve el resultado de la primera y no se procesa de nuevo.
- **Las claves no se guardan en RabbitMQ.** Una cola no permite consultar "¿ya vi esta clave?". RabbitMQ solo transporta eventos.
- **Cambio de estado + evento**: van siempre en la **misma transacción** mediante Outbox. Nunca se publica un evento de algo que no se guardó, ni se guarda algo cuyo evento se pierde.
- **Consumidores de eventos**: son idempotentes mediante Inbox, porque RabbitMQ entrega cada mensaje *al menos una vez*.

El detalle está en `02-reserva-vuelos.md`.

## 8. Datos y caché

- **PostgreSQL** con **SQLAlchemy 2 async** y **Alembic** para las migraciones. Los modelos van en `<módulo>/domain/models.py`.
- **Redis** como caché *cache-aside*: el repositorio busca primero en Redis y, si no está, consulta la DB y guarda el resultado con TTL. Redis nunca es fuente de verdad: si se pierde, el sistema sigue funcionando, solo más lento.
- **Las claves de caché llevan versión** (`airports:v1:...`), así un cambio de formato no lee datos viejos.

## 9. Errores

- Formato uniforme: `{"error": {"code", "message", "details"?}}`.
- Cada módulo mapea sus errores de dominio a HTTP en `api/errors.py`.
- Nunca se reenvían al cliente errores crudos del proveedor, tokens ni stack traces.

## 10. Frontend

| Capa | Elección |
|---|---|
| Base | React 19 + TypeScript + Vite (SPA) |
| Contrato con el backend | `openapi-typescript` + `openapi-fetch`: tipos generados del OpenAPI de FastAPI |
| Datos del servidor | TanStack Query |
| Rutas y estado en la URL | TanStack Router (search params tipados) |
| Estado del cliente | Zustand (`persist` en `sessionStorage`) |
| Formularios | React Hook Form + Zod |
| Estilos y componentes | Tailwind CSS v4 + Radix (`radix-ui`), con componentes propios al estilo de shadcn/ui en `src/components/ui` |
| Tipografía | IBM Plex Sans / IBM Plex Mono (`@fontsource`) |
| Formato | `Intl.NumberFormat`, `Intl.DateTimeFormat`, date-fns |
| Tests | Vitest + Testing Library + MSW (Playwright más adelante) |
| Calidad | Biome (linter + formatter) |
| Runtime | Node 24 LTS + pnpm, en Docker. Vite hace proxy `/api` → backend (sin CORS) |

Reglas del frontend:

- **El frontend no calcula precios ni reglas de negocio.** Muestra lo que devuelve la API.
- **Valores desconocidos:**
  - `null` se muestra como «Sin dato».
  - `0` (cantidad) se muestra como «No incluida».
  - `"0.00"` (penalidad) se muestra como «Gratis».
- **Nunca se infiere** lo que el proveedor no informa. Por ejemplo, el equipaje no se deduce del tipo de aerolínea; ver `docs/research/equipaje-low-cost-vs-tradicionales.md`.
- **Horarios de vuelo:** se muestran en la hora local del aeropuerto, sin convertir.
- **Montos:** se muestran en su moneda original, sin convertir.

## 11. Tests

- **Toda comunicación con proveedores externos** (Duffel, pasarelas de pago…) **está mockeada.** Se usan respuestas reales capturadas en `tests/fixtures/`. La red de seguridad del `conftest.py` raíz rechaza cualquier request no mockeada.
- **Infraestructura propia** (PostgreSQL, Redis, RabbitMQ): los tests de integración usan instancias reales en Docker, con bases y vhosts de test, aisladas de las de desarrollo. Los unitarios usan fakes en memoria.
- **Frontend:** MSW con los mismos fixtures reales.

## 12. Convenciones

Las convenciones de código (idioma, docstrings Google, `Field(description=...)`, archivos del dominio) están en `AGENTS.md`, en la raíz.

## 13. Registro de decisiones

| # | Fecha | Decisión |
|---|---|---|
| 1 | 2026-10-23 | Backend en Python + FastAPI, en Docker con `python:3.14-slim`. |
| 2 | 2026-10-23 | Monorepo: `backend/` y `frontend/` en la raíz. |
| 3 | 2026-10-23 | Módulos por vertical, cada uno con domain, providers, services, api y tests. |
| 4 | 2026-10-23 | Adapter para los proveedores de cada vertical; Duffel es el primero de vuelos. |
| 5 | 2026-10-23 | DTOs propios: uno interno (con costo y ganancia) y otro público (solo precio de venta). |
| 6 | 2026-10-23 | `httpx2` como cliente HTTP async compartido. |
| 7 | 2026-10-23 | `Protocol` en lugar de ABC para los puertos. |
| 8 | 2026-10-23 | Filtro por aerolínea en el contrato de la plataforma; el adapter de Duffel filtra la respuesta. |
| 9 | 2026-10-23 | Coordenadas de aeropuertos incluidas en `Place`. |
| 10 | 2026-10-23 | Tests por módulo; proveedores siempre mockeados con respuestas reales. |
| 11 | 2026-10-26 | Ganancia: `FIXED_FEE` + % aleatorio en [`MIN_PERCENT`, `MAX_PERCENT`], como constantes. |
| 12 | 2026-10-26 | Aleatorio estable por HMAC(`PRICING_SECRET`, `provider:offer_id`), sin persistencia. |
| 13 | 2026-10-26 | Precio de venta redondeado a 2 decimales. |
| 14 | 2026-10-26 | Filtro por aerolínea: coincide solo por `owner`. |
| 15 | 2026-10-26 | Dominio dividido en `constants`, `validators`, `dtos`, `errors` y `models` (este último solo para DB). |
| 16 | 2026-10-26 | Documentación de arquitectura en `docs/architecture/`: un documento global + uno por etapa. |
| 17 | 2026-10-26 | Frontend: React 19 + Vite + TypeScript, TanStack Query/Router, Zustand, Tailwind v4 + shadcn/ui, tipos generados del OpenAPI. Diseño base: propuesta A de Claude Design. |
| 18 | 2026-10-26 | PostgreSQL (SQLAlchemy 2 async + Alembic) como fuente de verdad; Redis como caché cache-aside. |
| 19 | 2026-10-26 | Equipaje: `0` significa "no incluido"; `None` significa "el proveedor no informa". No se infiere "solo artículo personal" (Duffel documenta que la ausencia es falta de información; ver `docs/research/`). |
| 20 | 2026-10-26 | Agrupación de tarifas por clave de itinerario propia (independiente del proveedor). |
| 21 | 2026-10-26 | Reservas asíncronas: Idempotency-Key en PostgreSQL, Transactional Outbox + Inbox, RabbitMQ como transporte y SSE hacia el frontend (etapa 2). |
| 22 | 2026-10-26 | Tests: proveedores externos mockeados; PostgreSQL, Redis y RabbitMQ reales en Docker para los tests de integración. |
| 23 | 2026-10-26 | "Tu viaje" idempotente: *upsert* por `item_key = provider:itinerary_key`. Misma oferta → sin cambios; otra tarifa o una oferta renovada del mismo vuelo → reemplaza. |
| 24 | 2026-10-26 | Aeropuertos: `airportsdata` (MIT) como fuente principal, más OurAirports (dominio público) para relevancia (`importance`) y nombres alternativos. |
| 25 | 2026-10-26 | Dependencias del frontend: se respeta la antigüedad mínima de publicación de pnpm, sin excepciones; ante un paquete muy nuevo se usa la versión anterior. |
| 26 | 2026-10-26 | TypeScript 7 para el proyecto; los tipos de la API se generan con `openapi-typescript` + TypeScript 5.9 vía `pnpm dlx`. |
| 27 | 2026-10-26 | Los títulos muestran el lugar buscado (NYC → "New York"), no el aeropuerto donde aterriza cada vuelo. |
| 28 | 2026-10-26 | `supplier_timeout` de Duffel en 45 s (HTTP 60 s): con 10 s, Duffel descartaba sin avisar a las aerolíneas lentas. |
| 29 | 2026-10-26 | Respuestas de la API con gzip (`GZipMiddleware`). |
| 30 | 2026-10-26 | Ida y vuelta: se busca como ida y vuelta (tarifa combinada) y se muestra en dos pasos (ida, después sus vueltas), igual para cualquier tamaño. Sin cambios en el contrato de la API. |
| 31 | 2026-10-26 | Alcance actual: un viaje de una persona con un vuelo. Lo que excede ese alcance en el diseño queda deshabilitado ("próximamente"). |
