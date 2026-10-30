# Prompt para Claude Design: usuarios, inicio de sesión y dispositivos

**Cómo usarlo:** copiar todo lo que está debajo de la línea en Claude Design y adjuntar `docs/frontend/Vuelos · Propuesta A.html`, que tiene el sistema de diseño vigente y los demás tableros. Contexto técnico: [03-usuarios-y-acceso.md](../architecture/03-usuarios-y-acceso.md).

---

## Contexto

Es una aplicación web de **búsqueda y reserva de vuelos** en español. Ya existe la **Propuesta A** (adjunta) con todos sus tableros: búsqueda, espera, resultados, detalle, Tu viaje, pasajeros y pago, y confirmación. Esa propuesta ya está implementada.

La plataforma apunta a **viajes corporativos**. Cada empresa tiene **su propia instalación** (su dirección, por ejemplo `acme.vuelos.com`), con sus usuarios y su configuración. También hay **particulares**, que reservan sin empresa desde la instalación principal.

Necesito los tableros de **inicio de sesión, alta de cuenta, contraseña y dispositivos conectados**, en **desktop (1280 px) y mobile (390 px)**. Hay que respetar los tokens, la tipografía (IBM Plex Sans / Mono) y los componentes de la Propuesta A para que se sienta el mismo producto.

## Reglas

- **Buscar no pide sesión; reservar sí.** El login aparece cuando el viajero pasa de «Tu viaje» a «Pasajeros y pago», o cuando abre una reserva. Al terminar, vuelve a donde estaba con su vuelo elegido.
- **Los métodos varían por instalación.** La pantalla de login solo muestra los que la instalación tiene habilitados:

| Instalación | Métodos |
|---|---|
| Principal (particulares) | «Continuar con Google» y email + contraseña |
| Empresa con contraseña | Uno o más botones de SSO con el nombre que configure la empresa (ej. «Entrar con Acme SSO») y email + contraseña |
| Empresa solo SSO | Solo los botones de SSO, sin campos de email ni contraseña |

- En una instalación de empresa se muestra el **nombre de la empresa** (no hay logo ni colores por empresa todavía).
- **Email y contraseña en dos pasos:** primero el email; después la contraseña. Entre los dos pasos se ve el email elegido con «Cambiar».
- Textos en español neutro rioplatense, como el resto de la Propuesta A («Ingresá», «Revisá»).
- No diseñar roles, permisos, panel de administración, MFA ni SAML: no existen todavía.

## Tableros

### 1. Inicio de sesión

Tres variantes: principal, empresa con contraseña y empresa solo SSO. Estados: normal, cargando (después de tocar un botón de SSO, mientras se redirige) y error.

**Hay un solo mensaje de error de inicio de sesión, siempre el mismo: «No pudimos iniciar sesión».** No se dice si el email no existe, si la contraseña está mal, si la cuenta está bloqueada ni si falló el proveedor: es una decisión de seguridad para no darle pistas a quien prueba cuentas. El diseño puede acompañarlo con ayuda genérica («Revisá tus datos o recuperá tu contraseña») pero nunca con el motivo.

Incluir el texto que explica por qué se pide la sesión cuando viene desde el checkout: «Ingresá para reservar tu vuelo. Tu viaje queda guardado».

### 2. Paso de contraseña

Con el email ya elegido. «¿Olvidaste tu contraseña?». Variante para una cuenta **que existe pero no tiene contraseña** (se creó con Google o la creó su empresa): explicar que todavía no tiene contraseña y ofrecer «Continuar con Google» (o el SSO de la empresa) y «Enviarme el correo para crear una contraseña».

### 3. No encontramos tu cuenta

Aparece después de Google o del SSO, o al escribir un email que no existe. Siempre muestra el email con el que se intentó.

| Variante | Acciones |
|---|---|
| Particular, desde Google | «Crear cuenta» (se crea con los datos de Google, sin formulario) y «Usar otra cuenta» (vuelve a elegir cuenta de Google) |
| Particular, email escrito | «Crear cuenta» (va al registro con el email ya cargado) y «Probar con otro email» |
| Empresa | No se puede crear: «Tu empresa todavía no te dio acceso. Pedíselo a quien administra los viajes en tu empresa». Acción: «Usar otra cuenta» |

El tono tiene que dejar claro que puede ser un error de tipeo o la cuenta equivocada, sin culpar al usuario.

### 4. Registro con contraseña (particulares)

Nombre, email (precargado si viene del paso anterior), teléfono **opcional** (con código de país, ej. +54 9 11 1234-5678), contraseña con sus requisitos visibles mientras escribe (mínimo 10 caracteres) y aceptación de términos. El mismo teléfono opcional aparece en «Crear cuenta» cuando se crea desde Google o el SSO (tablero 3). No hay selector de idioma: la plataforma está en español; el idioma se guardará para el futuro. Después: **«Revisá tu correo»**, con el email, «Reenviar el correo» (con espera entre reenvíos) y «Cambiar email».

### 5. Crear o recuperar la contraseña (desde el correo)

Una pantalla con dos textos:

- **Crear:** «Creá tu contraseña» (cuenta creada con Google o por su empresa). Aclarar que podrá seguir entrando también con Google o con su SSO.
- **Recuperar:** «Elegí una contraseña nueva». Aclarar que **se cerrará la sesión en todos sus dispositivos**.

Estados: enlace vencido o ya usado (con «Enviarme otro»), y éxito.

También «¿Olvidaste tu contraseña?»: pide el email y siempre responde «Si el email tiene una cuenta, te mandamos un enlace».

### 6. Aviso después de crear la cuenta con Google

Un aviso no bloqueante (banner o toast) en la pantalla a la que vuelve: «Te mandamos un correo para que crees una contraseña. Mientras tanto, seguí entrando con Google».

### 7. Menú de usuario en la barra superior

Hoy la barra tiene «Mis reservas · próximamente». Sumar:

- Sin sesión: «Ingresar».
- Con sesión: iniciales o avatar, nombre y email, empresa si tiene, «Dispositivos conectados» y «Cerrar sesión». «Mis reservas» sigue como próximamente.
- Mobile: cómo entra en el menú de 390 px sin cortarse (el tablero actual ya tiene problemas con «Mis reservas · próximamente» en anchos intermedios).

### 8. Dispositivos conectados

Una fila por dispositivo con sesión abierta:

| Dato | Ejemplo |
|---|---|
| Nombre | «Chrome en Windows», «Safari en iPhone», «App en Pixel 8» |
| Tipo | Ícono de computadora, celular o app |
| Inició sesión | «12 oct 2026» |
| Último uso | «Hace 5 min», «Ahora» |
| Última IP | `181.52.xx.xx` (sin ubicación por ahora) |
| Actual | Marca «Este dispositivo»; no tiene «Cerrar sesión» propio, se cierra desde el menú |

Acciones: «Cerrar sesión» por fila (con confirmación) y «Cerrar sesión en los demás dispositivos». Estados: un solo dispositivo (solo el actual), varios, cargando y error.

### 9. Sesión cerrada por seguridad

Si el sistema detecta que la sesión se usó desde otro dispositivo, o si el usuario la cerró desde otro lado, la próxima acción lleva al login con un aviso: «Cerramos tu sesión por seguridad. Volvé a ingresar». No debe asustar ni dar detalles técnicos. Distinguir de la sesión vencida por inactividad: «Tu sesión venció. Volvé a ingresar».

### 10. Pasajeros y pago con sesión

Solo el cambio sobre el tablero existente: el formulario del pasajero viene **precargado** con nombre y email del usuario, editable, con una indicación de que el viajero puede ser otra persona.

### 11. Correos

Mismo estilo que el correo de confirmación de reserva:

- Verificá tu email (registro).
- Creá tu contraseña (cuenta creada con Google o por su empresa; en ese caso, con el nombre de la empresa).
- Recuperá tu contraseña.
- Bloqueamos el ingreso con tu contraseña: «¿Fuiste vos?». Hubo varios intentos con una contraseña equivocada y el ingreso con contraseña quedó bloqueado por un tiempo (por ejemplo 30 minutos). Botón «Cambiar mi contraseña», que lo desbloquea; aclarar que también puede esperar, y que si no fue la persona conviene cambiarla.

Cada uno con su botón, el vencimiento del enlace y «Si no fuiste vos, ignorá este correo».

## Qué no hacer

- No mostrar notas técnicas en la interfaz (tokens, claves, DPoP, OIDC).
- No inventar métodos de login fuera de la tabla de arriba (Apple, Microsoft, enlace mágico).
- No pedir más datos de los listados en el registro.
