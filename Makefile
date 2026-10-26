COMPOSE = docker compose
API = $(COMPOSE) exec api
FE = $(COMPOSE) exec frontend

.PHONY: up down build restart logs ps test test-backend test-frontend lint shell \
	migrate migration seed-airports psql redis-cli api-types fe-add

up: ## Levanta todos los servicios (reconstruye las imágenes si cambiaron)
	$(COMPOSE) up -d --build

down: ## Baja todos los servicios (los datos de PostgreSQL se conservan en su volumen)
	$(COMPOSE) down

build: ## Reconstruye las imágenes
	$(COMPOSE) build

restart: ## Recrea los contenedores (por ejemplo, después de cambiar un .env)
	$(COMPOSE) up -d --force-recreate

logs: ## Logs en vivo de todos los servicios
	$(COMPOSE) logs -f

ps: ## Estado de los contenedores
	$(COMPOSE) ps

test: test-backend test-frontend ## Corre todos los tests

test-backend: ## Tests del backend (pytest)
	$(API) pytest

test-frontend: ## Tests del frontend (vitest)
	$(FE) pnpm test

lint: ## Chequeo de tipos y lint del frontend
	$(FE) pnpm typecheck
	$(FE) pnpm lint

shell: ## Shell en el contenedor del backend
	$(API) bash

migrate: ## Aplica las migraciones pendientes
	$(API) alembic upgrade head

migration: ## Crea una migración nueva: make migration m="descripcion"
	$(API) alembic revision --autogenerate -m "$(m)"

seed-airports: ## Carga o actualiza aeropuertos y ciudades (idempotente)
	$(API) python -m app.flights.commands.seed_airports

api-types: ## Regenera los tipos del frontend desde el OpenAPI del backend
	$(FE) pnpm gen:api

fe-add: ## Agrega una dependencia al frontend: make fe-add p="paquete@version" [dev=1]
	$(FE) pnpm add $(if $(dev),-D,) $(p)

psql: ## Consola de PostgreSQL
	$(COMPOSE) exec postgres psql -U booking -d booking

redis-cli: ## Consola de Redis
	$(COMPOSE) exec redis redis-cli
