# AGENTS.md

Memoria compartida del proyecto para agentes de código (Claude Code, Codex, Cursor, etc.). `CLAUDE.md` importa este archivo.

## Proyecto

Sistema de búsqueda y reserva de vuelos construido **para aprender patrones y tendencias actuales de desarrollo**. Los patrones se van incorporando por etapas según un cronograma del autor: **no introducir patrones o capas que no se hayan pedido**; proponerlos y esperar confirmación.

- **Objetivo final:** viajes empresariales, de una o varias personas. Los viajes se guardan para consultar después el historial, como particular o como empresa.
- **Versión actual ("vainilla"):** un viaje de **una sola persona** con un vuelo (ida o ida y vuelta), que ya se puede reservar (etapa 2). "Agregar otro vuelo", hoteles y varios pasajeros quedan para más adelante; no adelantarlos sin pedido.
- Proveedor de vuelos: **Duffel** (API v2, modo test). Ver `docs/providers/duffel-busqueda-y-reserva.md`.
- Arquitectura y decisiones: **`docs/architecture/`**. Primero `00-global.md` (reglas generales), luego el documento de la etapa en curso. Leerlos antes de tocar código y actualizarlos cuando cambie una decisión. Las decisiones nuevas se registran en `00-global.md` §13.

## Stack

- Backend: Python 3.14 + FastAPI + Pydantic v2 + pydantic-settings, `httpx2` como cliente HTTP async. Tests con pytest.
- Datos: PostgreSQL (SQLAlchemy 2 async + Alembic) y Redis como caché.
- Frontend: React 19 + TypeScript + Vite, TanStack Query/Router, Zustand, Tailwind v4 + Radix (componentes propios al estilo de shadcn/ui, en `src/components/ui`). El detalle está en `docs/architecture/00-global.md` §10.
- Mensajería: RabbitMQ (`aio-pika`) con Transactional Outbox/Inbox; workers `outbox-relay` y `booking-worker` (misma imagen que la API).
- Todo corre en Docker. No hay Python instalado en el host; los comandos de Python se ejecutan dentro del contenedor.

## Estructura

```
Makefile, docker-compose.yml   comandos y servicios (api, outbox-relay, booking-worker, booking-notifier, frontend, postgres, redis, rabbitmq, mailpit)
docs/           documentación: architecture/ (global + etapas), research/ (memoria de investigaciones), API de Duffel, prompts, samples
backend/        API FastAPI (Dockerfile, requirements*.txt, alembic.ini, migrations/)
  app/core/     transversal: config, cliente HTTP, errores, pricing, health, messaging (outbox, inbox, relay, SSE)
  app/flights/  módulo de vuelos: core, domain, providers (Adapter), services, api, tests
  app/travellers/ viajeros: datos personales y pasaporte, compartidos por todas las verticales
  app/payments/ cobro al viajero (PaymentGateway, simulado por ahora)
  app/notifications/ correos (EmailSender: smtp → Mailpit en desarrollo, console)
  app/workers/  puntos de entrada de los procesos (raíz de composición, como app/main.py)
  app/hotels/   (futuro) misma estructura que flights
frontend/       app web React (Vite): src/api, src/features, src/components/ui, src/lib
```

Cada módulo de `app/` es autocontenido e incluye sus propios tests.

### Monolito modular

El backend es un **monolito modular**: un solo código y una sola imagen, que se despliega como API y como workers, dividido en módulos con límites estrictos. Cada módulo podría extraerse a un servicio sin reescribir a los demás. Reglas:

- **Módulo = capacidad de negocio:** una vertical (`flights`, `hotels`) o algo compartido entre verticales (`travellers`). `app/core` es solo técnico (config, HTTP, DB, mensajería, dinero, pricing) y no tiene reglas de negocio de ningún módulo.
- **Interfaz pública:** cada módulo expone lo que ofrece en `app/<módulo>/public.py`, con funciones o servicios y sus DTOs. Otro módulo importa **solo** ese archivo, nunca `domain/`, `repositories/`, `models.py`, `providers/` ni `services/` ajenos.
- **Dependencias sin ciclos:** `flights` → `travellers` está permitido; `travellers` no conoce a ninguna vertical.
- **Cada módulo es dueño de sus datos:** solo él lee y escribe sus tablas. No hay claves foráneas ni joins entre tablas de módulos distintos; se referencian por id.
- **Comunicación:**
  - sincrónica, llamando a la interfaz pública en el mismo proceso. Una operación que abarca módulos puede compartir la transacción: el módulo que orquesta abre la sesión y se la pasa a la interfaz pública del otro;
  - asincrónica, con eventos por el Outbox (`app/core/messaging`).
- **Lo que cruza un límite son DTOs** de la interfaz pública, nunca modelos de SQLAlchemy.
- **Tests:** cada módulo prueba lo suyo. Un módulo que consume otro lo usa por su interfaz pública o con un fake de ella.

## Comandos

Ejecutar desde la raíz:

| Comando | Qué hace |
|---|---|
| `make up` | Levanta todo: frontend en http://localhost:5173, API en http://localhost:8000 (Swagger en `/docs`), PostgreSQL, Redis, RabbitMQ (consola en http://localhost:15672, `booking`/`booking`), Mailpit (correos en http://localhost:8025) y los workers. Aplica las migraciones al arrancar |
| `make down` | Lo baja (los datos de PostgreSQL quedan en su volumen) |
| `make test` | Tests de backend (pytest) y de frontend (vitest). También están `make test-backend` y `make test-frontend` |
| `make lint` | Límites entre módulos (`import-linter`) y chequeo de tipos y Biome del frontend. También `make lint-backend` y `make lint-frontend` |
| `make seed-airports` | Carga o actualiza los aeropuertos (idempotente). Hace falta una vez, con la base vacía |
| `make migrate` / `make migration m="..."` | Aplica migraciones / crea una nueva a partir de los modelos |
| `make api-types` | Regenera `frontend/src/api/schema.d.ts` desde el OpenAPI. Correrlo cada vez que cambia un schema del backend |
| `make fe-add p="paquete@x.y.z" [dev=1]` | Agrega una dependencia al frontend **desde el contenedor**. No usar pnpm en el host: el lockfile queda con permisos que el contenedor no puede leer |
| `make logs` / `make logs-workers` / `make ps` / `make restart` | Logs, estado y recreación de contenedores (`restart` hace falta si cambia un `.env`) |
| `make shell` / `make psql` / `make redis-cli` | Consolas. `make rabbitmq` y `make mailpit` muestran la URL de sus consolas |

El código (`backend/app`, `frontend/src`) está montado como volumen, con recarga automática. Solo hace falta `make up` si cambian dependencias o un `Dockerfile`.

## Herramientas para agentes

### Grafo de conocimiento (graphify)

El repo tiene un grafo de código y documentación en `graphify-out/` (ignorado por git, se regenera). [graphify](https://github.com/Graphify-Labs/graphify) está instalado en el host con `uv tool install --python 3.13 graphifyy`. Es la única herramienta de Python del host y no tiene relación con el Python del proyecto, que sigue en Docker.

- **Primero el grafo.** Ante cualquier pregunta sobre el código, correr `graphify query "<pregunta>"` antes del primer grep, búsqueda o lectura de archivos fuente. Para relaciones, `graphify path "<A>" "<B>"`; para un concepto puntual, `graphify explain "<concepto>"`. Leer archivos solo en las líneas que el grafo ya ubicó. Incluir esta regla en el prompt de todo subagente que explore código.
- `graphify-out/GRAPH_REPORT.md` resume la arquitectura (nodos centrales y comunidades). Se lee solo para una revisión amplia o cuando `query`, `path` y `explain` no alcanzan.
- **Mantenerlo al día.** Después de modificar código, correr `graphify update .`, que es solo AST, sin costo de LLM. Si cambian documentos de `docs/`, regenerarlo con `/graphify . --update`.
- Lo que no entra al grafo está en `.graphifyignore`: tablero de diseño, samples, fixtures, `schema.d.ts` generado y configuración de agentes.
- Un hook `PreToolUse` en `.claude/settings.json` le recuerda a Claude Code consultar el grafo antes de buscar o leer.

### Skills de superpowers

El plugin [superpowers](https://github.com/obra/superpowers) está habilitado a nivel proyecto en `.claude/settings.json`. Incluye flujos de brainstorming, planes, TDD, depuración sistemática, revisión de código y verificación. Se usan, pero **las reglas de este archivo mandan sobre las de las skills**:

- **Commits:** las skills piden commits frecuentes, pero acá no se hace ninguno sin que el autor lo pida. Los pasos "Commit" de un plan se saltean o se le proponen al autor.
- **Ramas y worktrees:** `using-git-worktrees` y `finishing-a-development-branch` (merge, PR, borrar la rama) solo se usan si el autor lo pide.
- **Alcance:** un plan no puede introducir patrones o capas que no estén en el cronograma (ver "Proyecto").
- **Documentos:** los specs y planes van en `docs/superpowers/` y se escriben en español, como el resto de `docs/`. Las decisiones de arquitectura se siguen registrando en `docs/architecture/`.

## Convenciones

- **Idioma:** código, identificadores y docstrings en inglés; documentación en `docs/` y comunicación con el autor en español.
- **Docstrings: formato Google.** Todo módulo, clase, método y función de `app/` lleva docstring. Reglas:
  - **Públicos:** resumen de una línea más las secciones `Args:`, `Returns:`, `Yields:`, `Raises:` y `Attributes:` que correspondan.
  - **Privados** (`_nombre`): alcanza con una línea, salvo que la lógica no sea obvia.
  - **Campos de modelos Pydantic** (DTOs, schemas, settings): el resumen va en la clase y cada campo lleva `Field(description=...)`, con **una línea en blanco entre campos**. Así las descripciones se publican en Swagger. No usar `#` ni docstrings de atributo para estos campos.
  - **Constantes de módulo y atributos de clases comunes:** `# comentario` en la línea de arriba, con una línea en blanco entre cada uno.
  - **Endpoints de FastAPI:** el docstring se escribe en prosa para quien consume la API, sin secciones de Google, porque FastAPI lo publica como descripción en Swagger.
  - **Tests:** el nombre de la función describe el caso. Solo llevan docstring los helpers, los fixtures y los casos que necesiten contexto.
- **Dependencias:** con versión fijada (`==`). Runtime en `requirements.txt`, desarrollo en `requirements-dev.txt`.
- **Herramientas del sistema:** si se necesitan, se agregan al `Dockerfile` (hay un bloque `apt-get` comentado).
- **Capas:** el formato de Duffel solo existe dentro de `app/flights/providers/duffel/`. Fuera de ahí se usan los DTOs de `app/flights/domain/dtos/`.
- **Archivos del dominio** (`<módulo>/domain/`). Cada tipo es un archivo mientras el módulo es chico (`travellers`, `payments`) y **pasa a ser un paquete con un archivo por tema** cuando junta temas distintos (`flights`: `dtos/search.py`, `dtos/itinerary.py`, `dtos/offers.py`, `dtos/places.py`, `dtos/results.py`, `dtos/bookings.py`, `dtos/orders.py`…). El `__init__.py` del paquete solo tiene el docstring: se importa siempre desde el archivo del tema, nunca re-exportando.
  - `constants`: constantes de negocio.
  - `validators`: reglas de validación y tipos validados, como `AirportCode`.
  - `dtos`: los DTOs.
  - `errors`: los errores.
  - `models`: **reservado para modelos de base de datos**; no poner DTOs ahí.
- **Capa `api/`** (`<módulo>/api/`), con una responsabilidad por carpeta:
  - `routes/`: solo endpoints, un archivo por tema; `routes/__init__.py` arma el router del módulo.
  - `schemas/`: solo la **forma** de las respuestas públicas (Pydantic), sin lógica ni imports de `services`.
  - `mappers/`: convierte dominio → schema (`to_booking_response`, `to_search_response`). Es el único lugar que decide qué sale hacia el cliente.
  - `dependencies.py`: dependencias de FastAPI: el armado (qué adapter, repositorio o política se usa) y las que leen o validan el request antes del endpoint (`idempotency_key`, `existing_booking`).
  - `errors.py`: error de dominio → código HTTP.
- **Precios:** internamente se llevan precio de compra (`cost`) y precio de venta (`price`). El costo y la ganancia **nunca** salen por la API pública: los schemas de `api/schemas/` no tienen esos campos.

### Frontend

- **El diseño manda.** La interfaz **replica** los tableros de `docs/frontend/` (propuesta A de Claude Design): medidas, colores, tipografía, textos y estructura de cada pantalla, en desktop y mobile. Los tableros no son una inspiración sino la especificación.
  - Antes de tocar una pantalla, leer su template completo, incluidos los estilos que calcula su script. Se extraen con los scripts de desempaquetado descritos en `docs/architecture/01-busqueda-vuelos.md` §9.
  - Las notas para desarrolladores que aparecen en los tableros (por ejemplo "La búsqueda arma `slices[...]`") no van en la interfaz.
  - Si una regla escrita del diseño contradice el dibujo, se sigue la regla y se deja anotado. Ejemplo: "el contador pasa a ámbar a los 5 min".
  - Verificar con capturas en navegador real (Playwright) comparando contra el tablero.
- **Estructura:**
  - `src/api/`: cliente tipado (`openapi-fetch`) y hooks de TanStack Query.
  - `src/features/<flujo>/`: componentes y lógica de cada flujo. La lógica pura va en archivos aparte (por ejemplo `logic.ts`), con tests.
  - `src/components/ui/`: componentes base. `src/components/flight/`: piezas de vuelo que usan varias pantallas (`SliceTimeline`, `AirlineBadge`).
  - `src/lib/`: formato, utilidades y hooks sin interfaz (`useNow`, `useExpiry`). `src/lib/flights/`: reglas de vuelos que comparten varias features (tarifas, itinerario, criterios de búsqueda).
- **Límites entre features**, como el monolito modular del backend (Biome, `noRestrictedImports` en `frontend/biome.json`, lo verifica `make lint`):
  - una feature importa otra **solo por su `public.ts`** (`@/features/trip/public`), nunca sus archivos internos ni con rutas `../`;
  - `api/`, `components/` y `lib/` nunca importan una feature, y `lib/` no importa componentes;
  - lo que necesitan dos features no se expone en `public.ts`: va a `components/` o `lib/`. `public.ts` es para las dependencias del flujo (por ejemplo, «Tu viaje»).
- **Tipos de la API:** salen siempre del OpenAPI generado (`src/api/schema.d.ts`, con `make api-types`). No se escriben a mano.
- **Estado:**
  - criterios, filtros y orden van en la URL (TanStack Router + Zod);
  - los datos del servidor, en TanStack Query;
  - "Tu viaje", en Zustand con `sessionStorage`.
  - Con Zustand, nunca derivar arrays u objetos nuevos dentro del selector: provoca renders infinitos. Usar `useShallow` + `useMemo`.
- **Datos:**
  - el frontend no calcula precios ni reglas de negocio;
  - `null` → «Sin dato»; `0` → «No incluida»; `"0.00"` → «Gratis»;
  - horarios en hora local del aeropuerto, leídos como texto, sin convertir con `Date`;
  - montos en su moneda, sin convertir.
- **Textos y código:** textos de interfaz en español; código, comentarios y JSDoc en inglés.
- **Accesibilidad:** Biome con el preset recomendado, incluidas sus reglas de a11y. El lint tiene que pasar sin `biome-ignore`, salvo que se justifique en el comentario.

## Reglas

- **Secretos:** el token de Duffel vive en `backend/.env`, que está ignorado por git. Nunca imprimirlo, commitearlo ni copiarlo en docs o fixtures.
- **Tests sin red:** toda comunicación con proveedores va mockeada. Se usan los fixtures de `<módulo>/tests/fixtures/` (respuestas reales capturadas), `httpx2.MockTransport` o providers falsos. Ningún test llama a Duffel.
  - **Backend:** el `conftest.py` raíz bloquea el HTTP saliente y apunta a la base y al Redis de test (`booking_test`, Redis db 15), nunca a los de desarrollo.
  - **Frontend:** MSW con `onUnhandledFrame: "error"`. Los fixtures de `src/test/fixtures/` se generan pasando la respuesta real de Duffel por el servicio y los schemas del backend.
- **Vencimiento de ofertas:** las ofertas de Duffel vencen a los ~30 minutos. Para probar una reserva manual hay que hacer una búsqueda nueva.
- **Commits:** no hacer commits sin que el autor lo pida.

## Bitácora

| Fecha | Qué se hizo |
|---|---|
| 2026-10-23 | Documentación de la API de Duffel (búsqueda y reserva). |
| 2026-10-23 | Estructura base FastAPI + Docker (`python:3.14-slim`), endpoint `/health`. |
| 2026-10-23 | Token de test validado con una búsqueda real LHR→JFK (56 ofertas); respuesta guardada en `docs/samples/`. |
| 2026-10-23 | Prompt para Claude Design (`docs/prompts/claude-design-ui.md`). |
| 2026-10-23 | Backend movido a `backend/`; `Makefile` en la raíz; `docs/architecture.md` (Adapter + DTO) **pendiente de validación** antes de implementar la búsqueda. |
| 2026-10-23 | Arquitectura v2: módulos por vertical (`app/flights`, futuro `app/hotels`), frontend en el repo, tests por módulo con proveedores mockeados, filtro por aerolínea (Duffel no lo soporta nativamente: se filtra en el adapter), coordenadas en `Place`, precio de compra/venta con ganancia aleatoria. **Pendiente:** elegir la opción de ganancia (§8 y §12 de `docs/architecture.md`). |
| 2026-10-26 | **Búsqueda de vuelos implementada**: `POST /api/v1/flights/search` (adapter Duffel, DTOs, filtro por aerolínea por `owner`, ganancia opción C con constantes en `app/core/pricing/fixed_fee_random_percent.py` y HMAC con `PRICING_SECRET`). 62 tests, todos con el proveedor mockeado. Fixtures de error 422/401 capturados de Duffel real. Pendiente: paginar respuestas grandes (una ida y vuelta devolvió 1364 ofertas, ~9 MB). |
| 2026-10-26 | Docstrings en formato Google en todo `backend/app`; descripciones de los DTOs publicadas en OpenAPI con `use_attribute_docstrings`. Convención anotada en este archivo. |
| 2026-10-26 | Dominio de flights dividido en `constants.py`, `validators.py`, `dtos.py` y `models.py` (reservado para DB). Campos Pydantic documentados con `Field(description=...)` y una línea en blanco entre campos; constantes con `# comentario` arriba. |
| 2026-10-26 | Documentación de arquitectura reorganizada en `docs/architecture/` (global + etapas). Etapa 1 ampliada: equipaje `0`≠`None`, agrupación de tarifas por clave de itinerario (verificada: 56 ofertas → 16 vuelos, igual que `comparison_key`), aeropuertos en PostgreSQL (`airportsdata`, MIT) con caché Redis, frontend React hasta "Tu viaje". Etapa 2 planificada: Idempotency-Key en PostgreSQL, Transactional Outbox/Inbox, RabbitMQ, SSE. |
| 2026-10-26 | Investigación de equipaje (`docs/research/equipaje-low-cost-vs-tradicionales.md`): ausencia de ítem = sin información (Duffel lo documenta); no se infiere "solo artículo personal". Idempotencia de "Tu viaje" documentada: upsert por `item_key = provider:itinerary_key` (etapa 1 en el store, etapa 2 en PostgreSQL). |
| 2026-10-26 | **Etapa 1 implementada.** Backend: equipaje `None`, agrupación por clave de itinerario (`flights[].fares[]`), aeropuertos en PostgreSQL (`airportsdata` + OurAirports) con caché Redis y `GET /places`, compose en la raíz con postgres y redis. Frontend (React 19, TS 7, Vite 8, TanStack, Zustand, Tailwind 4): búsqueda con autocompletado, espera, resultados con filtros y matriz de tarifas, detalle y "Tu viaje" idempotente. 93 tests de backend y 38 de frontend; recorrido verificado en navegador (desktop y mobile). Pendientes en `01-busqueda-vuelos.md` §10. |
| 2026-10-26 | Resultados grandes: gzip en la API, `supplier_timeout` 45 s (con 10 s faltaban Avianca y LATAM), tarifas en modal, sin búsquedas duplicadas por `StrictMode`. Ida y vuelta en dos pasos (cada ida una vez, después sus vueltas), igual para toda ida y vuelta, sin cambiar la API. 93 tests de backend y 45 de frontend. |
| 2026-10-26 | Objetivo de la plataforma anotado (viajes empresariales, historial por particular o empresa; versión actual: una persona, un vuelo). "Agregar otro vuelo" deshabilitado y su formulario eliminado. Las vueltas respetan el orden elegido. |
| 2026-10-26 | **Cierre de la etapa 1.** Documentación actualizada con el estado final (`01-busqueda-vuelos.md`, decisiones 28-31 en `00-global.md`) y PR con todo lo hecho. Hallazgo: el sandbox de Duffel no cubre todas las rutas (BAQ-EOH solo trae Duffel Airways; BAQ-MDE, 621 vuelos). |
| 2026-10-27 | Herramientas para agentes: grafo de conocimiento con graphify (instalado en el host con `uv`; hook `PreToolUse` y skill en `.claude/`) y plugin superpowers habilitado a nivel proyecto. Reglas de convivencia con este archivo en "Herramientas para agentes". |
| 2026-10-27 | **Etapa 2: reserva de vuelos.** Monolito modular como regla (interfaz `public.py`, schema por módulo, `import-linter` en los tests); módulos `travellers` y `payments` (gateway simulado). Reserva asíncrona: Idempotency-Key en PostgreSQL, Outbox/Inbox, RabbitMQ con reintentos y DLQ, worker con lease y reconciliación por `metadata.booking_id`, SSE nativo de FastAPI. Bifurcación por precio: `awaiting_price_approval` hasta que el viajero acepta. Pantallas 5 y 6 en desktop y mobile. Hallazgos de Duffel test: ignora `Idempotency-Key`; una oferta vencida responde `not_found`. 194 tests de backend y 87 de frontend; reserva real verificada en navegador. Detalle en `02-reserva-vuelos.md`. |
| 2026-10-27 | Confirmación v2 (Propuesta A v2: confirmada, confirmando, no se pudo reservar) y correo de confirmación asíncrono por `booking.confirmed`: módulo `notifications` con adapters por ambiente (`EMAIL_BACKEND`), Mailpit en compose y proceso `booking-notifier`. Plantillas Jinja2 con autoescape (un test detectó que `.html.j2` no se escapaba). 212 tests de backend y 100 de frontend; correo real verificado en Mailpit. |
| 2026-10-28 | Arreglo del lease del worker: ante una falla transitoria del proveedor suelta la reserva para que el reintento la tome enseguida (antes se gastaban 7 de 10 intentos esperando un lease propio). Aviso «Está tardando más de lo habitual» a partir de 1 minuto en las pantallas 5 y 6. Análisis de qué pasa si fallan los 10 reintentos y qué no está cubierto en `02-reserva-vuelos.md` §8.1. 214 tests de backend y 103 de frontend. |
| 2026-10-28 | **Estado «Error de emisión» (`issuance_error`)**: captura rechazada después de emitir o emisión sin verificar conservan la retención y la orden y quedan para una persona o un agente de IA; la API no muestra localizador ni orden fuera de `confirmed`; el checkout no cierra el intento. **Verificación de la tarjeta** con una compra pequeña y su reversión (`verify_card`). Timeout de 130 s al crear la orden. Inventario de errores de emisión verificado en la documentación de Duffel (`docs/research/duffel-errores-de-emision.md`) y plan de failover entre proveedores (`docs/architecture/XX-failover-proveedores.md`, sin etapa asignada). |
