# Arquitectura

| Documento | Contenido | Estado |
|---|---|---|
| [00-global.md](00-global.md) | Vista general, reglas que aplican a todo el proyecto, stack, patrones y registro de decisiones | Vigente |
| [01-busqueda-vuelos.md](01-busqueda-vuelos.md) | Etapa 1: búsqueda de vuelos, agrupación de tarifas, aeropuertos, frontend hasta "Tu viaje" | **Implementada** |
| [02-reserva-vuelos.md](02-reserva-vuelos.md) | Etapa 2: reserva asíncrona (idempotencia, Outbox/Inbox, RabbitMQ, SSE), módulos `travellers`, `payments` y `notifications`, correo de confirmación. **Incluye diagramas de todo el flujo y la guía para probar y depurar (§15)** | **Implementada** |
| [03-usuarios-y-acceso.md](03-usuarios-y-acceso.md) | Etapa 3: usuarios, empresas (tenants por hostname, `settings` JSON) y particulares; login con OIDC + PKCE (Google y AS de empresa) y contraseña; «no encontramos tu cuenta»; tokens propios ES256 con refresh rotado, sesiones por dispositivo atadas con DPoP. SAML queda para después. Plan en `../superpowers/plans/` | **Implementada** |
| [XX-failover-proveedores.md](XX-failover-proveedores.md) | Plan general: si un proveedor falla al emitir con un error definitivo, buscar el vuelo en otros, validar la tarifa y, si cambia, pedir aprobación. Incluye el canal para casos que resuelven agentes humanos o de IA. **Sin etapa asignada (`XX`)** | **Idea** |
| [XX-viajeros-y-viajes.md](XX-viajeros-y-viajes.md) | Cuenta ≠ viajero: snapshot de cada viajero por viaje; particulares con perfil del titular (implementado) y sin recordar a terceros; empresas con asistentes, usuarios e invitados (idea). **Sin etapa asignada (`XX`)** | **Idea** (perfil del titular implementado) |

**Por dónde empezar:** [00-global.md §2](00-global.md#2-vista-general) para ver los procesos y módulos, y después [02-reserva-vuelos.md](02-reserva-vuelos.md) para entender una reserva de punta a punta. Los documentos de Duffel están en [../duffel-busqueda-y-reserva.md](../providers/duffel-busqueda-y-reserva.md).

**Cómo se usan:**
- El documento global define las **reglas**. Los de etapa definen **qué se construye y cómo** en cada etapa.
- Si una etapa necesita romper una regla global, primero se cambia el global y se registra la decisión.
- Cada etapa nueva tiene su archivo `NN-nombre.md`. El de hoteles será `NN-busqueda-hoteles.md`.
