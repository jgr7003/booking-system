# Arquitectura

| Documento | Contenido | Estado |
|---|---|---|
| [00-global.md](00-global.md) | Vista general, reglas que aplican a todo el proyecto, stack, patrones y registro de decisiones | Vigente |
| [01-busqueda-vuelos.md](01-busqueda-vuelos.md) | Etapa 1: búsqueda de vuelos, agrupación de tarifas, aeropuertos, frontend hasta "Tu viaje" | **Implementada** (PR en revisión) |
| [02-reserva-vuelos.md](02-reserva-vuelos.md) | Etapa 2: reserva asíncrona con idempotencia, Transactional Outbox, RabbitMQ y SSE | Planificada |

**Cómo se usan:**
- El documento global define las **reglas**. Los de etapa definen **qué se construye y cómo** en cada etapa.
- Si una etapa necesita romper una regla global, primero se cambia el global y se registra la decisión.
- Cada etapa nueva tiene su archivo `NN-nombre.md`. El de hoteles será `NN-busqueda-hoteles.md`.
