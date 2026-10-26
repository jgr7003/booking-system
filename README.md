# booking-system
An example for a booking system using modern patterns

Búsqueda de vuelos sobre la API de [Duffel](https://duffel.com) (modo test), con backend FastAPI y frontend React.

El objetivo es una plataforma de viajes empresariales, de una o varias personas, con historial de viajes. La versión actual cubre un viaje de una persona: buscar un vuelo (solo ida o ida y vuelta), comparar tarifas y dejarlo en "Tu viaje".

## Requisitos

- Docker y Docker Compose
- `make`

## Levantar el proyecto

```bash
cp backend/.env.example backend/.env   # completar DUFFEL_API_TOKEN (duffel_test_...) y PRICING_SECRET
make up                                # frontend, API, PostgreSQL y Redis; aplica las migraciones
make seed-airports                     # la primera vez: carga los aeropuertos del autocompletado
```

| Servicio | URL |
|---|---|
| App | http://localhost:5173 |
| API | http://localhost:8000 · Swagger en http://localhost:8000/docs |
| Búsqueda de vuelos | `POST /api/v1/flights/search` |
| Autocompletado de aeropuertos | `GET /api/v1/flights/places?q=new%20y` |

El código de `backend/app/` y `frontend/src/` se monta como volumen y se recarga solo.

## Comandos

| Comando | Qué hace |
|---|---|
| `make up` / `make down` | Levanta / baja todos los servicios |
| `make test` | Tests de backend y frontend |
| `make lint` | Tipos y Biome del frontend |
| `make seed-airports` | Carga o actualiza aeropuertos (idempotente) |
| `make migrate` | Aplica migraciones |
| `make api-types` | Regenera los tipos del frontend desde el OpenAPI |
| `make logs` | Logs en vivo |

La lista completa está en el `Makefile`.

## Estructura

```
booking-system/
├── Makefile, docker-compose.yml
├── AGENTS.md / CLAUDE.md   # convenciones y memoria del proyecto para agentes de código
├── docs/                   # arquitectura (global + etapas), investigación, diseño, API de Duffel
├── backend/                # FastAPI · módulos por vertical (app/flights, futuro app/hotels)
└── frontend/               # React + Vite
```

La arquitectura está en [`docs/architecture/`](docs/architecture/README.md): un documento global y uno por etapa.
