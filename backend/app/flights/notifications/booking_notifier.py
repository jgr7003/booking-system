"""Sends the confirmation email when a booking is confirmed (`booking.confirmed` event).

It runs apart from the booking: the booking is already confirmed and paid, so a mail server
that is down only delays the email (retries), it never undoes the booking.
"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.messaging.consumer import Delivery, RetryLater
from app.core.messaging.inbox import mark_processed, was_processed
from app.flights.api.mappers.bookings import to_booking_response
from app.flights.domain.dtos.bookings import BookingStatus
from app.flights.notifications.confirmation_email import render_booking_confirmed
from app.flights.repositories.bookings import BookingRepository
from app.notifications.public import EmailDeliveryError, EmailMessage, EmailSender
from app.travellers.public import get_traveller

logger = logging.getLogger(__name__)

# Name of this consumer in the inbox.
CONSUMER = "flights.booking-notifier"


class BookingConfirmationNotifier:
    """Emails the traveler their confirmation, once per `booking.confirmed` event."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession], sender: EmailSender, *, app_url: str) -> None:
        """Initializes the notifier.

        Args:
            session_factory: Factory of database sessions.
            sender: Email sender of the environment (Mailpit, a real SMTP server, console...).
            app_url: Public URL of the web app, for the link to the booking.
        """
        self._session_factory = session_factory
        self._sender = sender
        self._app_url = app_url

    async def handle(self, delivery: Delivery) -> None:
        """Sends the email of one `booking.confirmed` event.

        The inbox, keyed by the event id, keeps a redelivered event from sending the email again.
        If the process dies between sending and recording it, the email goes out twice: email
        delivery is at least once.

        Args:
            delivery: The event.

        Raises:
            RetryLater: The mail server didn't take the email; it is retried later.
        """
        message_id = delivery.event.message_id
        booking_id = uuid.UUID(delivery.event.payload["booking_id"])
        async with self._session_factory() as session:
            if await was_processed(session, message_id, CONSUMER):
                return
            booking = await BookingRepository(session).get_for_processing(booking_id)
            if booking is None or booking.status != BookingStatus.CONFIRMED:
                logger.warning("Booking %s isn't confirmed; no email", booking_id)
                await self._done(message_id)
                return
            view = to_booking_response(booking)
            traveller = await get_traveller(session, booking.traveller_id)

        if traveller is None:
            logger.warning("Booking %s has no traveller; no email", booking_id)
            await self._done(message_id)
            return

        email = render_booking_confirmed(view, app_url=self._app_url)
        try:
            await self._sender.send(EmailMessage(to=traveller.email, subject=email.subject, html=email.html, text=email.text))
        except EmailDeliveryError as exc:
            raise RetryLater(str(exc)) from exc
        await self._done(message_id)
        logger.info("Confirmation email of booking %s sent", booking_id)

    async def _done(self, message_id: uuid.UUID) -> None:
        """Records the event as processed."""
        async with self._session_factory() as session, session.begin():
            await mark_processed(session, message_id, CONSUMER)
