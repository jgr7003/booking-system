"""Public interface of the notifications module: the only thing other modules may import.

Example, from a vertical that confirms a booking::

    from app.notifications.public import EmailMessage, create_email_sender

    await create_email_sender().send(EmailMessage(to=..., subject=..., html=..., text=...))
"""

from app.notifications.core.config import EmailBackend, EmailSettings, get_email_settings
from app.notifications.domain.dtos import EmailMessage
from app.notifications.domain.errors import EmailDeliveryError
from app.notifications.providers.base import EmailSender
from app.notifications.providers.console.sender import ConsoleEmailSender
from app.notifications.providers.smtp.sender import SmtpEmailSender


def create_email_sender(settings: EmailSettings | None = None) -> EmailSender:
    """Returns the sender of the environment (`EMAIL_BACKEND`).

    Adding a provider (an HTTP API such as SES or SendGrid) means a new adapter in `providers/`
    and a new value of `EmailBackend`; callers don't change.

    Args:
        settings: Email settings; the environment's if not given.

    Returns:
        The sender.
    """
    settings = settings or get_email_settings()
    if settings.email_backend == EmailBackend.SMTP:
        return SmtpEmailSender(settings)
    return ConsoleEmailSender()


__all__ = ["EmailDeliveryError", "EmailMessage", "EmailSender", "create_email_sender"]
