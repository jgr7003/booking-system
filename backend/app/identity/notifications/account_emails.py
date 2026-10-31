"""Account emails (design board "Cuenta 11 · Correos de cuenta", Propuesta A v3).

- Welcome: when an account is created with Google or SSO, when an organization gives access, or
  when the email of a new account is verified.
- With a single-use link: verify the email, create the password, recover it, and the notice that
  the password sign in was blocked (no board: it follows the recovery email).

The expiry texts come from the real lifetimes of the links, not the board's examples.
"""

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from app.identity.domain.constants.passwords import SET_PASSWORD_PATH, VERIFY_EMAIL_PATH
from app.identity.domain.dtos.passwords import AccountEmail
from app.notifications.public import EmailMessage

_templates = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "templates"),
    # HTML templates escape every value (names come from users); plain text ones don't.
    autoescape=select_autoescape(enabled_extensions=("html.j2",), default_for_string=False),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)


@dataclass(frozen=True)
class _LinkCopy:
    """Texts of an account email with a link."""

    # Subject line.
    subject: str

    # Title inside the email.
    heading: str

    # Sentence before the email address, after «Hola, Pepe.».
    lead_before: str

    # Sentence after the email address.
    lead_after: str

    # Text of the button.
    button: str

    # What to know about the link: when it expires, what it does.
    link_note: str

    # Bold start of the closing line.
    safety_strong: str

    # Rest of the closing line.
    safety: str

    # Path of the web app the link opens.
    path: str


def _link_copy(
    kind: AccountEmail,
    *,
    expires: str,
    organization_name: str | None,
    provider_name: str | None,
    lock_minutes: int | None,
) -> _LinkCopy:
    """Texts of an email with a link, by kind."""
    if kind is AccountEmail.VERIFY_EMAIL:
        return _LinkCopy(
            subject="Verifica tu email para usar Vuelos",
            heading="Verifica tu email",
            lead_before="Para terminar de crear tu cuenta, confirma que ",
            lead_after=" es tuyo.",
            button="Verificar mi email",
            link_note=f"El enlace vence {expires} y se puede usar una sola vez.",
            safety_strong="Si no fuiste tú, ignora este correo.",
            safety="Sin verificar, la cuenta no se activa.",
            path=VERIFY_EMAIL_PATH,
        )
    if kind is AccountEmail.SET_PASSWORD:
        if provider_name:
            works_with = f" ya funciona con {provider_name}."
        elif organization_name:
            works_with = f" ya está lista: {organization_name} te dio acceso."
        else:
            works_with = " ya está lista."
        return _LinkCopy(
            subject="Si quieres, crea una contraseña para Vuelos",
            heading="Crea tu contraseña",
            lead_before="Tu cuenta de Vuelos para ",
            lead_after=(
                f"{works_with} Si quieres, crea una contraseña para entrar también con tu email. "
                "No es obligatorio."
            ),
            button="Crear mi contraseña",
            link_note=f"El enlace vence {expires}. Si vence, pide otro desde «¿Olvidaste tu contraseña?».",
            safety_strong="Si no fuiste tú, ignora este correo.",
            safety="Nadie va a poder usar tu cuenta sin este enlace.",
            path=SET_PASSWORD_PATH,
        )
    if kind is AccountEmail.ACCOUNT_LOCKED:
        return _LinkCopy(
            subject="Bloqueamos el ingreso con tu contraseña",
            heading="¿Fuiste tú?",
            lead_before="Hubo varios intentos de entrar a ",
            lead_after=(
                " con una contraseña equivocada. Para proteger tu cuenta, bloqueamos el ingreso con "
                f"contraseña durante {lock_minutes} minutos. Si fuiste tú, espera o cambia tu contraseña "
                "ahora: eso la desbloquea."
            ),
            button="Cambiar mi contraseña",
            link_note=(
                f"El enlace vence {expires} y se puede usar una sola vez. Al cambiarla, se cierra la sesión "
                "en todos tus dispositivos."
            ),
            safety_strong="Si no fuiste tú, cambia tu contraseña.",
            safety="Alguien está probando entrar a tu cuenta.",
            path=SET_PASSWORD_PATH,
        )
    return _LinkCopy(
        subject="Recupera tu contraseña de Vuelos",
        heading="Recupera tu contraseña",
        lead_before="Pediste elegir una contraseña nueva para ",
        lead_after=".",
        button="Elegir una contraseña nueva",
        link_note=(
            f"El enlace vence {expires} y se puede usar una sola vez. Al cambiarla, se cierra la sesión "
            "en todos tus dispositivos."
        ),
        safety_strong="Si no fuiste tú, ignora este correo.",
        safety="Tu contraseña actual sigue funcionando.",
        path=SET_PASSWORD_PATH,
    )


def installation_url(app_url: str, host: str) -> str:
    """Base URL of an installation: the web app's scheme and port with the installation's host.

    Args:
        app_url: Public URL of the main installation, e.g. `http://localhost:5173`.
        host: Host of the installation, e.g. `acme.localhost`.

    Returns:
        E.g. `http://acme.localhost:5173`.
    """
    parts = urlsplit(app_url)
    port = f":{parts.port}" if parts.port else ""
    return f"{parts.scheme}://{host}{port}"


def _expires(ttl: timedelta) -> str:
    """When a link expires, in words."""
    if ttl >= timedelta(days=2):
        return f"en {ttl.days} días"
    if ttl >= timedelta(hours=2):
        return f"en {int(ttl.total_seconds() // 3600)} horas"
    if ttl >= timedelta(hours=1):
        return "en 1 hora"
    return f"en {int(ttl.total_seconds() // 60)} minutos"


def _first_name(display_name: str) -> str:
    """The first word of the display name, for «Hola, Pepe.»."""
    return display_name.split()[0] if display_name.strip() else display_name


def render_link_email(
    *,
    kind: AccountEmail,
    to: str,
    name: str,
    token: str,
    ttl: timedelta,
    base_url: str,
    organization_name: str | None,
    provider_name: str | None = None,
    lock_minutes: int | None = None,
) -> EmailMessage:
    """Renders an account email with its single-use link.

    Args:
        kind: Which email (any but the welcome).
        to: Recipient.
        name: Display name of the user.
        token: The token of the link; it travels only here.
        ttl: Lifetime of the link.
        base_url: Base URL of the user's installation.
        organization_name: Organization of the user, if any.
        provider_name: Identity provider the account was created with (e.g. «Google»).
        lock_minutes: How long the password sign in stays blocked, for the account-locked email.

    Returns:
        The email, ready to send.
    """
    copy = _link_copy(
        kind,
        expires=_expires(ttl),
        organization_name=organization_name,
        provider_name=provider_name,
        lock_minutes=lock_minutes,
    )
    query = {"token": token}
    if kind is not AccountEmail.VERIFY_EMAIL:
        query["kind"] = "set" if kind is AccountEmail.SET_PASSWORD else "reset"
    context = {
        "subject": copy.subject,
        "heading": copy.heading,
        "organization_name": organization_name,
        "first_name": _first_name(name),
        "email": to,
        "lead_before": copy.lead_before,
        "lead_after": copy.lead_after,
        "button": copy.button,
        "link": f"{base_url}{copy.path}?{urlencode(query)}",
        "link_note": copy.link_note,
        "safety_strong": copy.safety_strong,
        "safety": copy.safety,
    }
    return EmailMessage(
        to=to,
        subject=copy.subject,
        html=_templates.get_template("account_link.html.j2").render(context),
        text=_templates.get_template("account_link.txt.j2").render(context),
    )


def render_welcome_email(
    *,
    to: str,
    name: str,
    base_url: str,
    organization_name: str | None,
    provider_name: str | None,
    password_email_follows: bool,
) -> EmailMessage:
    """Renders the welcome email.

    Args:
        to: Recipient.
        name: Display name of the user.
        base_url: Base URL of the user's installation, for «Buscar vuelos».
        organization_name: Organization of the user, if any.
        provider_name: Identity provider the account was created with; `None` if it was verified by email.
        password_email_follows: Whether the email to create a password is sent right after.

    Returns:
        The email, ready to send.
    """
    if provider_name:
        intro = f"Entraste con {provider_name}."
    elif organization_name:
        intro = f"{organization_name} te dio acceso."
    else:
        intro = "Verificaste tu email."
    context = {
        "subject": "Te damos la bienvenida a Vuelos",
        "organization_name": organization_name,
        "first_name": _first_name(name),
        "intro": f"{intro} Desde ahora puedes buscar, armar y reservar tus viajes de trabajo.",
        "link": f"{base_url}/",
        "password_email_follows": password_email_follows,
    }
    return EmailMessage(
        to=to,
        subject=context["subject"],
        html=_templates.get_template("account_welcome.html.j2").render(context),
        text=_templates.get_template("account_welcome.txt.j2").render(context),
    )
