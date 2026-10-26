# AGENTS.md

Memoria compartida del proyecto para agentes de código (Claude Code, Codex, Cursor, etc.). `CLAUDE.md` importa este archivo.

## Proyecto

Sistema de búsqueda y reserva de vuelos construido **para aprender patrones y tendencias actuales de desarrollo**. Los patrones se van incorporando por etapas según un cronograma del autor: **no introducir patrones o capas que no se hayan pedido**; proponerlos y esperar confirmación.

- **Objetivo final:** viajes empresariales, de una o varias personas. Los viajes se guardan para consultar después el historial, como particular o como empresa.
- **Versión actual ("vainilla"):** un viaje de **una sola persona** con un vuelo (ida o ida y vuelta). "Agregar otro vuelo", hoteles y varios pasajeros quedan para más adelante; no adelantarlos sin pedido.
- Proveedor de vuelos: **Duffel** (API v2, modo test). Ver `docs/duffel-busqueda-y-reserva.md`.
- Arquitectura y decisiones: **`docs/architecture/`**. Primero `00-global.md` (reglas generales), luego el documento de la etapa en curso. Leerlos antes de tocar código y actualizarlos cuando cambie una decisión. Las decisiones nuevas se registran en `00-global.md` §13.

## Stack

- Backend: Python 3.14 + FastAPI + Pydantic v2 + pydantic-settings, `httpx2` como cliente HTTP async. Tests con pytest.
- Datos: PostgreSQL (SQLAlchemy 2 async + Alembic) y Redis como caché.
- Frontend: React 19 + TypeScript + Vite, TanStack Query/Router, Zustand, Tailwind v4 + Radix (componentes propios al estilo de shadcn/ui, en `src/components/ui`). El detalle está en `docs/architecture/00-global.md` §10.
- Mensajería (etapa 2, planificada): RabbitMQ + workers.
- Todo corre en Docker. No hay Python instalado en el host; los comandos de Python se ejecutan dentro del contenedor.

## Estructura

```
Makefile, docker-compose.yml   comandos y servicios (api, frontend, postgres, redis)
docs/           documentación: architecture/ (global + etapas), research/ (memoria de investigaciones), API de Duffel, prompts, samples
backend/        API FastAPI (Dockerfile, requirements*.txt, alembic.ini, migrations/)
  app/core/     transversal: config, cliente HTTP, errores, pricing, health
  app/flights/  módulo de vuelos: core, domain, providers (Adapter), services, api, tests
  app/hotels/   (futuro) misma estructura que flights
frontend/       app web React (Vite): src/api, src/features, src/components/ui, src/lib
```

Cada módulo de `app/` es autocontenido e incluye sus propios tests.

## Comandos

Ejecutar desde la raíz:

| Comando | Qué hace |
|---|---|
| `make up` | Levanta todo: frontend en http://localhost:5173, API en http://localhost:8000 (Swagger en `/docs`), PostgreSQL y Redis. Aplica las migraciones al arrancar |
| `make down` | Lo baja (los datos de PostgreSQL quedan en su volumen) |
| `make test` | Tests de backend (pytest) y de frontend (vitest). También están `make test-backend` y `make test-frontend` |
| `make lint` | Chequeo de tipos y Biome del frontend |
| `make seed-airports` | Carga o actualiza los aeropuertos (idempotente). Hace falta una vez, con la base vacía |
| `make migrate` / `make migration m="..."` | Aplica migraciones / crea una nueva a partir de los modelos |
| `make api-types` | Regenera `frontend/src/api/schema.d.ts` desde el OpenAPI. Correrlo cada vez que cambia un schema del backend |
| `make fe-add p="paquete@x.y.z" [dev=1]` | Agrega una dependencia al frontend **desde el contenedor**. No usar pnpm en el host: el lockfile queda con permisos que el contenedor no puede leer |
| `make logs` / `make ps` / `make restart` | Logs, estado y recreación de contenedores (`restart` hace falta si cambia un `.env`) |
| `make shell` / `make psql` / `make redis-cli` | Consolas |

El código (`backend/app`, `frontend/src`) está montado como volumen, con recarga automática. Solo hace falta `make up` si cambian dependencias o un `Dockerfile`.

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
- **Capas:** el formato de Duffel solo existe dentro de `app/flights/providers/duffel/`. Fuera de ahí se usan los DTOs de `app/flights/domain/dtos.py`.
- **Archivos del dominio** (`<módulo>/domain/`):
  - `constants.py`: constantes de negocio.
  - `validators.py`: reglas de validación y tipos validados, como `AirportCode`.
  - `dtos.py`: los DTOs.
  - `errors.py`: los errores.
  - `models.py`: **reservado para modelos de base de datos**; no poner DTOs ahí.
- **Precios:** internamente se llevan precio de compra (`cost`) y precio de venta (`price`). El costo y la ganancia **nunca** salen por la API pública: los schemas de `api/schemas.py` no tienen esos campos.

### Frontend

- **El diseño manda.** La interfaz **replica** los tableros de `docs/frontend/` (propuesta A de Claude Design): medidas, colores, tipografía, textos y estructura de cada pantalla, en desktop y mobile. Los tableros no son una inspiración sino la especificación.
  - Antes de tocar una pantalla, leer su template completo, incluidos los estilos que calcula su script. Se extraen con los scripts de desempaquetado descritos en `docs/architecture/01-busqueda-vuelos.md` §9.
  - Las notas para desarrolladores que aparecen en los tableros (por ejemplo "La búsqueda arma `slices[...]`") no van en la interfaz.
  - Si una regla escrita del diseño contradice el dibujo, se sigue la regla y se deja anotado. Ejemplo: "el contador pasa a ámbar a los 5 min".
  - Verificar con capturas en navegador real (Playwright) comparando contra el tablero.
- **Estructura:**
  - `src/api/`: cliente tipado (`openapi-fetch`) y hooks de TanStack Query.
  - `src/features/<flujo>/`: componentes y lógica de cada flujo. La lógica pura va en archivos aparte (por ejemplo `logic.ts`), con tests.
  - `src/components/ui/`: componentes base.
  - `src/lib/`: formato y utilidades.
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
