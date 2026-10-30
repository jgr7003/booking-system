COMPOSE = docker compose
API = $(COMPOSE) exec api
FE = $(COMPOSE) exec frontend
# A literal comma, for `$(subst)` (make can't take one inline).
comma := ,

.PHONY: up down build restart logs logs-workers ps test test-backend test-frontend lint lint-backend lint-frontend shell \
	migrate migration seed-airports org-create org-user-add auth-keygen idp-add seed-dev-idps seed-dev keycloak psql redis-cli rabbitmq mailpit api-types fe-add

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

logs-workers: ## Logs en vivo del outbox relay y del worker de reservas
	$(COMPOSE) logs -f outbox-relay booking-worker

test: test-backend test-frontend ## Corre todos los tests

test-backend: ## Tests del backend (pytest)
	$(API) pytest

test-frontend: ## Tests del frontend (vitest)
	$(FE) pnpm test

lint: lint-backend lint-frontend ## Lint de backend y frontend

lint-backend: ## Límites entre módulos del monolito modular (import-linter)
	$(API) lint-imports

lint-frontend: ## Chequeo de tipos y lint del frontend
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

org-create: ## Crea una empresa: make org-create slug=acme name="Acme" host=acme.localhost [nopassword=1] [nets=200.1.2.0/24,...]
	$(API) python -m app.organizations.commands.create_organization --slug "$(slug)" --name "$(name)" --host "$(host)" $(if $(nopassword),--no-password-login,) $(foreach n,$(subst $(comma), ,$(nets)),--trusted-network "$(n)")

org-user-add: ## Da acceso a una persona en una empresa: make org-user-add org=acme email=ana@acme.test name="Ana" [phone=+549...] [lang=es]
	$(API) python -m app.identity.commands.add_organization_user --org "$(org)" --email "$(email)" --name "$(name)" $(if $(phone),--phone "$(phone)",) $(if $(lang),--language "$(lang)",)

auth-keygen: ## Imprime claves nuevas (AUTH_SIGNING_KEYS, IDENTITY_SECRETS_KEY) para pegar en backend/.env
	@$(API) python -m app.identity.commands.generate_signing_key

idp-add: ## Agrega o actualiza un proveedor OIDC: make idp-add [org=acme] slug=google name=Google issuer=... client_id=... client_secret=... [prompt=select_account]
	$(API) python -m app.identity.commands.add_identity_provider $(if $(org),--org "$(org)",) --slug "$(slug)" --name "$(name)" --issuer "$(issuer)" --client-id "$(client_id)" --client-secret "$(client_secret)" $(if $(prompt),--prompt "$(prompt)",)

seed-dev-idps: ## Registra el Keycloak de desarrollo como proveedor de identidad (idempotente)
	$(API) python -m app.identity.commands.seed_dev_identity_providers

seed-dev: seed-airports seed-dev-idps ## Datos de prueba de desarrollo: aeropuertos, Keycloak, la empresa Acme y su usuario (idempotente)

api-types: ## Regenera los tipos del frontend desde el OpenAPI del backend
	$(FE) pnpm gen:api

fe-add: ## Agrega una dependencia al frontend: make fe-add p="paquete@version" [dev=1]
	$(FE) pnpm add $(if $(dev),-D,) $(p)

psql: ## Consola de PostgreSQL
	$(COMPOSE) exec postgres psql -U booking -d booking

redis-cli: ## Consola de Redis
	$(COMPOSE) exec redis redis-cli

rabbitmq: ## Consola de gestión de RabbitMQ (booking / booking)
	@echo "http://localhost:15672"

keycloak: ## Consola de Keycloak, el proveedor de identidad de desarrollo (admin / admin)
	@echo "http://localhost:8080"

mailpit: ## Bandeja de Mailpit: los correos que manda la plataforma en desarrollo
	@echo "http://localhost:8025"
