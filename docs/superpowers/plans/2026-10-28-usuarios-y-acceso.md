# Plan: usuarios, empresas e inicio de sesión (etapa 3)

> Arquitectura aprobada: [03-usuarios-y-acceso.md](../../architecture/03-usuarios-y-acceso.md) (decisiones en §16 y en [00-global.md §13](../../architecture/00-global.md#13-registro-de-decisiones), 49-58).
> Diseño de las pantallas: [prompt para Claude Design](../../prompts/claude-design-usuarios.md). El tablero resultante es requisito de la fase 7.
> Fecha: 2026-10-28

## Reglas del plan

- Cada fase termina con `make test` y `make lint` en verde y con `graphify update .`.
- Sin commits salvo pedido del autor: al cierre de cada fase se propone uno.
- **Los tests nunca llaman a un IdP real** (ni Keycloak ni Google). Usan un IdP falso con `httpx2.MockTransport` y claves generadas en el test. Keycloak es solo para la prueba manual.
- Las dependencias se fijan con `==`. En el frontend se agregan con `make fe-add` y respetando la antigüedad mínima de pnpm.
- **Secretos:** la clave privada de firma, `IDENTITY_SECRETS_KEY` y los `client_secret` viven en `backend/.env` o cifrados en la base, nunca en el repo, en fixtures ni en logs. `backend/.env.example` lleva las variables con valores vacíos o de ejemplo. Las contraseñas de los usuarios de Keycloak del realm exportado son de desarrollo y sí van al repo.
- Toda ruta, schema o mapper nuevo sigue las convenciones de `AGENTS.md`: `routes/`, `schemas/`, `mappers/`, docstrings Google, `Field(description=...)`.
- Después de cambiar schemas del backend, `make api-types`.

## Fase 0 · Verificaciones previas

1. Versiones a fijar, comprobando que tengan la antigüedad mínima: `joserfc`, `pwdlib[argon2]`, `cryptography` (puede estar ya como dependencia transitiva: fijarla igual) y la imagen de Keycloak.
2. Confirmar en la documentación de `joserfc`: cálculo del *thumbprint* JWK (RFC 7638) para `cnf.jkt` y validación de un JWT firmado con una clave pública incluida en su header (`jwk`), que es lo que trae la prueba DPoP.
3. Confirmar en la documentación de Keycloak la configuración vigente de hostname v2: `KC_HOSTNAME` + `KC_HOSTNAME_BACKCHANNEL_DYNAMIC`, y que el token endpoint y el JWKS respondan por `http://keycloak:8080` con `iss = http://localhost:8080/realms/<realm>`.
4. PostgreSQL 18 (compose): `UNIQUE NULLS NOT DISTINCT` disponible. Decidir entre la extensión `citext` o `lower(email)` con índice único funcional (preferir lo segundo si `citext` complica Alembic).
5. Anotar lo verificado en `03-usuarios-y-acceso.md` si cambia algo del diseño.

**Listo cuando:** versiones elegidas y las tres verificaciones anotadas.

## Fase 1 · Base: `organizations`, `identity` y resolución por host

1. Módulo `app/organizations/`: modelos `organizations` y `domains` (schema `organizations`), `OrganizationSettings` (Pydantic, `password_login_enabled: bool = True`, `extra="forbid"`), repositorio, `public.py` con `resolve_by_host(host)` y `get(id)` → `OrganizationRef` (DTO con `settings` validados).
2. Esqueleto de `app/identity/` con la estructura de §4 del documento. Modelo `users` (schema `identity`) con `UNIQUE NULLS NOT DISTINCT (organization_id, email)`, `password_credentials` y `user_identities`.
3. Migración: `CREATE SCHEMA organizations, identity` y sus tablas.
4. Middleware de instalación en `app/main.py`: host desde `X-Forwarded-Host` solo si el cliente está en `FORWARDED_ALLOW_IPS`, si no `Host`; host desconocido → `404` con el formato de error de siempre; la empresa queda en `request.state`. Ajustar `vite.config.ts` para reenviar el host original.
5. `import-linter`: contratos de `organizations` e `identity` (solo `public.py`), y `organizations` no importa `identity`. Agregarlos a la capa de módulos compartidos.
6. Comandos en `app/organizations/commands/` y `app/identity/commands/` con targets: `make org-create slug= name= host=` y `make org-user-add org= email= name=` (el correo de contraseña se suma en la fase 3).
7. Tests: `settings` por defecto y clave desconocida rechazada; resolución por host (principal, empresa, desconocido, `X-Forwarded-Host` de un proxy no confiable ignorado); `NULLS NOT DISTINCT` entre particulares; mismo email en dos instalaciones; límites.

**Listo cuando:** `make org-create slug=acme host=acme.localhost` crea la empresa, `curl -H "Host: acme.localhost" /api/v1/...` la resuelve y un host desconocido responde `404`. Los tests de las etapas 1 y 2 siguen pasando.

## Fase 2 · Tokens propios, DPoP y sesiones por dispositivo

1. Configuración: `AUTH_SIGNING_KEYS` (JSON con `kid` y clave privada PEM; varias para rotar, una activa), `AUTH_ISSUER` por instalación (derivado del host), duraciones de C20. `make auth-keygen` genera una clave `ES256` y la imprime para pegar en `backend/.env` (no la escribe en el repo).
2. `app/identity/tokens/`:
   - `signing.py`: emitir el access token (claims de §10.1) y validarlo (firma por `kid`, `iss`, `aud`, `exp`, `org` igual a la instalación del request).
   - `dpop.py`: validar la prueba (`typ = dpop+jwt`, `alg = ES256`, `jwk` público en el header, `htm`, `htu` sin query, `iat` ±60 s, `ath`, `jti` no visto). Caché de `jti` en Redis con TTL; sin Redis, `warning` y se sigue.
3. Modelos `sessions` y `refresh_tokens` con su migración e índice parcial de sesiones activas.
4. `SessionService`: abrir sesión (dispositivo = `jkt`, `device_name`, user agent, IP), emitir par de tokens, refresh con rotación (`SELECT … FOR UPDATE` del refresh; usado → revocar sesión `refresh_reuse`; otra clave → `key_mismatch`), revocar una, las demás o todas (`password_changed`), y caché de sesión activa en Redis (`identity:v1:session:<sid>`) que se borra al revocar.
5. Dependencias en `identity/public.py`: `current_principal` y `optional_principal`. Orden de chequeo: esquema `DPoP` (con `Bearer` → revoca), token válido, prueba válida, `cnf.jkt` igual a la clave de la prueba (si no → revoca), sesión activa. Errores de §11.2.
6. Rutas: `GET /auth/jwks.json`, `POST /auth/token/refresh`, `POST /auth/logout`, `GET /me`, `GET /me/sessions`, `DELETE /me/sessions/{id}`, `DELETE /me/sessions?scope=others`.
7. Helper de tests en `app/identity/tests/support.py`: generar una clave de dispositivo, abrir una sesión directamente con el servicio y firmar pruebas DPoP para cualquier request. Lo usan también los tests de `flights` (fase 5), solo vía un fixture expuesto en `public.py` o en un paquete de soporte de tests acordado con los contratos de `import-linter`.
8. Tests de §17 «Tokens», «DPoP», «Refresh» y «Sesiones», incluida la revocación con y sin Redis y dos refresh concurrentes del mismo token (uno gana, el otro revoca).

**Listo cuando:** con una sesión abierta por el helper, `GET /me` responde con DPoP, el mismo token como `Bearer` devuelve `401` y deja la sesión revocada, y la lista de dispositivos refleja altas y cierres.

## Fase 3 · Email y contraseña

1. `PasswordHasher` (puerto) con `pwdlib` Argon2id y rehash al entrar.
2. Modelo `email_tokens` (`verify_email`, `set_password`, `reset_password`) con su migración; tokens de 256 bits guardados como SHA-256.
3. Plantillas en `app/identity/notifications/` (Jinja2, autoescape, como el correo de reserva): verificá tu email, creá tu contraseña (con nombre de empresa si aplica), recuperá tu contraseña. Envío por `notifications/public.py`. Enlaces a la instalación correcta (`http://<host>/cuenta/...`).
4. Rutas: `lookup`, `signup` (solo particulares), `email/verify` (abre sesión), `login`, `set` (asignar o recuperar; recuperar revoca todas las sesiones), `forgot` (siempre `202`).
5. Límite de intentos en Redis por email y por IP en `lookup`, `login` y `forgot`; sin Redis, sin límite y `warning`.
6. `password_login_enabled = false` → `404` en todas estas rutas para esa instalación.
7. `make org-user-add` manda el correo `set_password` si la empresa permite contraseña.
8. Tests de §17 «Contraseña» y la parte de usuarios de empresa con y sin correo. Correo real verificado contra Mailpit por su API, como en la etapa 2.

**Listo cuando:** un particular se registra, verifica desde Mailpit, entra con contraseña y recupera la contraseña cerrando sus otros dispositivos.

## Fase 4 · OIDC + PKCE con Keycloak (particulares)

1. Servicio `keycloak` en `docker-compose.yml` (imagen fijada, `start-dev --import-realm`, `KC_HOSTNAME`, `KC_HOSTNAME_BACKCHANNEL_DYNAMIC=true`, puerto `8080`, *healthcheck*). Realm `particulares` exportado en `backend/docker/keycloak/realms/`: cliente `booking-platform` confidencial con PKCE `S256` obligatorio y `redirect_uri` `http://localhost:5173/auth/callback`; usuarios `ana@`, `nuevo@` y `sinverificar@example.test`. `make keycloak` muestra la URL.
2. Modelo `identity_providers` (secreto cifrado con Fernet y `IDENTITY_SECRETS_KEY`) y `login_attempts`, con su migración. `make idp-add org= slug= name= issuer= client_id= client_secret= [backchannel_base_url=] [trust_email=]`.
3. `providers/oidc/`: discovery y JWKS cacheados en Redis (`identity:v1:oidc:<issuer>`), reescritura al `backchannel_base_url` para las llamadas servidor a servidor, URL de autorización con PKCE `S256`, `state`, `nonce` y `extra_authorize_params`, canje del código, validación del id_token (firma, `iss` público, `aud`, `exp`, `nonce`, `email_verified` o `trust_email`) y un reintento del JWKS ante `kid` desconocido.
4. `LoginService`: buscar por identidad, después por email verificado (vincula), si no `account_not_found` con la identidad guardada en el intento (`awaiting_signup`). Cuenta sin verificar con el mismo email: se descarta al crear la nueva (§7, toma de cuenta anticipada).
5. Rutas: `GET /auth/methods`, `POST /auth/oidc/{provider}/authorize`, `POST /auth/oidc/{provider}/callback`, `POST` y `DELETE /auth/signup/pending/{attempt_id}`. El intento se ata al `jkt` de la prueba DPoP; `return_to` solo rutas propias.
6. «Crear cuenta» de un particular por SSO: usuario mínimo + identidad + sesión + correo `set_password`.
7. `make seed-dev-idps` (idempotente): registra el IdP `keycloak` de la plataforma. En la fase 6 suma Acme.
8. Tests de §17 «OIDC» y «Sin cuenta» con el IdP falso. Prueba manual con Keycloak llamando a la API con un script de scratchpad que genera la clave DPoP, mientras no haya frontend.

**Listo cuando:** con Keycloak, `ana@` entra, `nuevo@` recibe `account_not_found` y al crear la cuenta llega el correo a Mailpit, y `sinverificar@` se rechaza.

## Fase 5 · Reservas con dueño

1. **Limpieza de los datos de prueba** de la base de desarrollo, a mano y antes de migrar: reservas, viajeros, autorizaciones de pago y filas de outbox/inbox de las etapas 1 y 2. No va en la migración: una migración no borra datos en silencio.
2. Migración: `user_id uuid NOT NULL` y `organization_id uuid NULL` (`NULL` = particular) en `flights.bookings`, con índice `(organization_id, user_id)`. Sin valores por defecto: si quedara alguna reserva, la migración falla en lugar de dejar reservas huérfanas.
3. `POST /flights/bookings` y `price-decision` con `current_principal`; la reserva guarda `user_id` y `organization_id` **del principal**, nunca del body.
4. **Aislamiento obligatorio en el repositorio.** Toda lectura de reservas hecha por un usuario recibe un `BookingOwnerScope(organization_id, user_id)` sin valores por defecto, y el filtro se arma siempre con los dos:
   - `organization_id IS NOT DISTINCT FROM :org`: un usuario de una empresa nunca ve reservas de otra, ni un particular las de una empresa (ni al revés);
   - `user_id = :user`: un particular solo ve las suyas y, mientras no haya autorización, un usuario de empresa también.
   Cuando llegue la autorización (por ejemplo, un administrador que ve las de su empresa), solo se relaja el filtro de `user_id`; el de empresa no se quita nunca. Los métodos sin scope existen solo para los workers, con un nombre explícito (`get_for_processing`), y un test verifica que ninguna ruta de la API los usa.
5. `GET /flights/bookings/{id}`, `price-decision` y el SSE: fuera del scope → `404`. El SSE valida el token al conectar y cierra el stream al vencer el access token.
6. Contrato de `import-linter`: `flights` importa solo `identity.public`.
7. Ajustar los tests de reservas existentes para usar el helper de sesión de la fase 2. Tests nuevos: sin sesión → `401`; otro particular → `404`; usuario de Acme sobre una reserva de otra empresa o de un particular → `404` en `GET`, `price-decision` y SSE, aunque el `user_id` coincidiera; particular sobre una reserva de empresa → `404`; la reserva guarda la empresa del principal aunque el body intente otra; stream cerrado al vencer el token.
8. `make api-types`.

**Listo cuando:** ninguna reserva es visible fuera de su empresa (o fuera de su dueño, para particulares), no existe ninguna reserva sin `user_id`, y los tests de la etapa 2 siguen pasando adaptados.

**Propuesta a confirmar (no se implementa sin pedido):** sumar *Row-Level Security* de PostgreSQL en `flights.bookings` como segunda barrera, con la empresa y el usuario del request en variables de sesión de la conexión. Protegería incluso ante una consulta escrita sin el scope.

## Fase 6 · Empresas

1. Realm `acme` en Keycloak: cliente `booking-acme` (PKCE `S256`, `redirect_uri` `http://acme.localhost:5173/auth/callback`), usuarios `viajero@acme.test` e `intruso@acme.test`.
2. `make seed-dev-idps` suma la empresa Acme (`acme.localhost`), su IdP y el usuario `viajero@acme.test` (con el correo `set_password`).
3. `account_not_found` en una empresa → `can_create = false`; `POST /auth/signup/pending` → `403`.
4. `GET /auth/methods` por instalación: Acme muestra su IdP y la contraseña según `settings`; la principal no muestra IdPs de empresas.
5. Tests: IdP de otra instalación no utilizable; vínculo por email del usuario creado por la empresa; `intruso@` sin alta; Acme con `password_login_enabled = false`.

**Listo cuando:** en `acme.localhost`, `viajero@` entra por Acme SSO, `intruso@` ve «tu empresa todavía no te dio acceso», y con la contraseña deshabilitada sus rutas responden `404`.

## Fase 7 · Frontend

**Requisito:** el tablero de Claude Design hecho con [el prompt](../../prompts/claude-design-usuarios.md), guardado en `docs/frontend/` y leído completo antes de empezar (regla «el diseño manda»).

1. `src/lib/auth/` (sin interfaz):
   - clave del dispositivo: `crypto.subtle.generateKey` ES256 **no exportable**, guardada en IndexedDB;
   - firma de pruebas DPoP (`htm`, `htu`, `iat`, `jti`, `ath`);
   - almacenamiento del refresh token en IndexedDB y del access token en memoria;
   - lectura de los claims del access token para la interfaz.
2. `src/api/client.ts`: middleware de `openapi-fetch` que agrega `Authorization: DPoP` y `DPoP`, hace refresh ante `401 token_expired` serializado con Web Locks, y ante `session_revoked` limpia el almacenamiento y manda a `/login?return_to=…&reason=…`.
3. SSE de reservas con `fetch` en lugar de `EventSource` (`src/api/bookings.ts`), con los headers de autenticación y reconexión al cerrar el stream.
4. `src/features/auth/` (con `public.ts`): login con métodos por instalación, paso de contraseña, sin contraseña asignada, «no encontramos tu cuenta» (particular y empresa), registro, «revisá tu correo», crear o recuperar la contraseña, `/auth/callback`, avisos de sesión cerrada por seguridad o vencida.
5. `src/features/account/`: dispositivos conectados.
6. Barra superior: menú de usuario. Rutas protegidas (checkout y reserva) con `return_to`. Checkout: precarga de nombre y email del usuario.
7. Fixtures de MSW generados con el backend; tests de la lógica (`src/lib/auth/`, refresh serializado, `return_to`) y de cada flujo, con `onUnhandledFrame: "error"`.
8. Verificación con Playwright contra el tablero, desktop y mobile, con Keycloak real: particular existente, nuevo, empresa, dispositivos, robo del token simulado.

**Listo cuando:** el recorrido completo funciona en el navegador contra Keycloak y las capturas coinciden con el tablero.

## Fase 8 · Cierre

1. Reescribir `docs/architecture/03-usuarios-y-acceso.md` con lo implementado y los hallazgos. En `00-global.md`: §2 (Keycloak y los módulos nuevos), §3, §4.1 (diagrama de módulos), §5 (patrones: BFF de login sin cookies, PKCE, DPoP, rotación de refresh tokens, multi-tenant por host) y decisiones nuevas en §13.
2. `AGENTS.md`: estructura (`organizations`, `identity`), servicios de compose, comandos nuevos (`auth-keygen`, `org-create`, `org-user-add`, `idp-add`, `seed-dev-idps`, `keycloak`) y la bitácora.
3. `backend/.env.example` con todas las variables nuevas.
4. Grafo (obligatorio antes del PR): `graphify update .` y `/graphify . --update`.
5. Proponer el commit o el PR al autor.
