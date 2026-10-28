"""Port every email sender adapter implements."""

from typing import Protocol

from app.notifications.domain.dtos import EmailMessage


class EmailSender(Protocol):
    """Delivers emails. Which one is used depends on the environment (`EMAIL_BACKEND`)."""

    async def send(self, message: EmailMessage) -> None:
        """Hands an email to the mail server.

        Delivery is at least once: a caller that retries after a failure may send the email
        twice, so callers deduplicate on their side (e.g. with the inbox).

        Args:
            message: The email.

        Raises:
            EmailDeliveryError: The server didn't accept it.
        """
        ...
