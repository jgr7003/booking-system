# Etapa XX: Viajeros, viajes y asistentes

> Estado: **idea, sin etapa asignada** (de ahí el `XX`). Se va completando a medida que el autor aterriza la idea; solo está implementado lo que dice §4.
> Reglas generales: [00-global.md](00-global.md). Parte de: [03-usuarios-y-acceso.md](03-usuarios-y-acceso.md) (usuario ≠ viajero, §2).
> Fecha: 2026-10-30

## 1. La idea

Quien reserva y quien viaja no siempre son la misma persona. La plataforma tiene que distinguir:

- **la cuenta** (`identity`): quien entra y paga o gestiona;
- **el viajero** (`travellers`): la persona que vuela, con sus datos como figuran en el documento;
- **el viaje**: lo que se reserva (hoy un vuelo; más adelante varios vuelos, hotel y varias personas).

La regla que atraviesa todo: **el viaje guarda una foto (snapshot) de cada viajero tal como viajó.** Si después cambian sus datos (un apellido, el pasaporte), la reserva sigue mostrando con qué datos se emitió.

## 2. Particulares (plataforma principal)

Funciona como en las aerolíneas (LATAM, Avianca):

- Al comprar, la plataforma **sugiere los datos del titular** «como están actualmente»: nombre, email y teléfono de la cuenta, más tratamiento, fecha de nacimiento y género de su última reserva para sí mismo.
- Si el titular compra **para otra persona**, carga los datos de esa persona y la reserva sale a su nombre. Esos datos **quedan solo en esa reserva** (su snapshot): no se guardan como viajero frecuente ni se sugieren después. Si esa persona vuelve a viajar, se cargan de nuevo.

## 3. Empresas (a futuro)

- Habrá **asistentes** que crean viajes para otras personas.
- Los viajeros de un viaje de empresa pueden ser:
  - **usuarios de la empresa** (tienen cuenta en su instalación);
  - **invitados**: personas sin usuario en la empresa (posiblemente ni siquiera pertenecen a ella), que se suman a un viaje.
- Cada viajero se persiste **a nivel de viaje**, como snapshot, sea usuario o invitado.
- Abierto, para cuando se aterrice: si los usuarios de la empresa también tienen un perfil que se sugiere (como el titular particular); si un invitado puede pasar a ser usuario; qué permisos tiene un asistente (depende de la autorización, pendiente de la etapa 3, §19); si los datos de un invitado se pueden reutilizar dentro de la empresa.

## 4. Lo implementado (2026-10-30)

| Pieza | Qué hace |
|---|---|
| Snapshot por reserva | Ya existía desde la etapa 2: cada reserva crea su `travellers.travellers` con los datos con que se emitió |
| Perfil del titular | `travellers.profiles` (un registro por `user_id`, sin FK): tratamiento, fecha de nacimiento y género. Interfaz pública: `get_profile`, `save_profile`, `TravellerProfile` |
| Cuándo se guarda | Al crear la reserva con `passenger.is_account_holder = true`, en la misma transacción (upsert: queda lo de la última reserva para sí mismo). Con `false` no se guarda nada fuera de la reserva |
| Cómo se lee | `GET /me` → `traveller_profile` (identity lee la interfaz pública de travellers; `travellers` sigue sin conocer a `identity`) |
| Frontend | El checkout precarga tratamiento, fecha de nacimiento y género además de nombre, email y teléfono, y manda `is_account_holder` mientras el pasajero sea el titular. «Viaja otra persona» vacía todo y manda `false` |

No se guardan (por ahora): el pasaporte del titular ni los datos de terceros.

**Borradores del checkout** (`sessionStorage`): son de un usuario (`owner`). Si en esa pestaña entra otro, se descartan; al cerrar sesión se borran. Junto al borrador queda si el pasajero es el titular, así una recarga no lo olvida.
