"""Email sender that only logs: for tests and environments without a mail server."""

import logging

from app.notifications.domain.dtos import EmailMessage

logger = logging.getLogger(__name__)


class ConsoleEmailSender:
    """Logs who would get each email and its subject. The body isn't logged: it has personal data."""

    async def send(self, message: EmailMessage) -> None:
        """Logs the email instead of sending it; see `EmailSender.send`."""
        logger.info("Email not sent (console backend): to=%s subject=%r", message.to, message.subject)
