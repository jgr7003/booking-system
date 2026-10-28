"""Email sender over SMTP, with the standard library."""

import asyncio
import email.message
import email.utils
import logging
import smtplib

from app.notifications.core.config import EmailSettings
from app.notifications.domain.dtos import EmailMessage
from app.notifications.domain.errors import EmailDeliveryError

logger = logging.getLogger(__name__)


class SmtpEmailSender:
    """Sends through any SMTP server: Mailpit locally, the provider's server elsewhere.

    `smtplib` is blocking, so each email is sent in a worker thread.
    """

    def __init__(self, settings: EmailSettings) -> None:
        """Initializes the sender.

        Args:
            settings: Server, port, credentials and TLS mode.
        """
        self._settings = settings

    async def send(self, message: EmailMessage) -> None:
        """Sends an email; see `EmailSender.send`."""
        await asyncio.to_thread(self._send, build_mime(message, self._settings.email_from))

    def _send(self, mime: email.message.EmailMessage) -> None:
        """Opens a connection, authenticates if configured and sends one message."""
        s = self._settings
        smtp_class = smtplib.SMTP_SSL if s.smtp_ssl else smtplib.SMTP
        try:
            with smtp_class(s.smtp_host, s.smtp_port, timeout=s.smtp_timeout_s) as smtp:
                if s.smtp_starttls:
                    smtp.starttls()
                if s.smtp_username and s.smtp_password:
                    smtp.login(s.smtp_username, s.smtp_password.get_secret_value())
                smtp.send_message(mime)
        except (OSError, smtplib.SMTPException) as exc:
            logger.warning("SMTP %s:%s didn't take the email: %s", s.smtp_host, s.smtp_port, exc)
            raise EmailDeliveryError("The mail server didn't accept the email.") from exc


def build_mime(message: EmailMessage, sender: str) -> email.message.EmailMessage:
    """Builds the MIME message: plain text with an HTML alternative.

    Args:
        message: The email.
        sender: `From` address.

    Returns:
        The message to hand to `smtplib`.
    """
    mime = email.message.EmailMessage()
    mime["From"] = sender
    mime["To"] = message.to
    mime["Subject"] = message.subject
    mime["Date"] = email.utils.formatdate(localtime=False)
    mime["Message-ID"] = email.utils.make_msgid(domain=sender.rsplit("@", 1)[-1].rstrip(">") or None)
    mime.set_content(message.text)
    mime.add_alternative(message.html, subtype="html")
    return mime
