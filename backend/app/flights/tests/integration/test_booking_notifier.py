"""BookingConfirmationNotifier against the test PostgreSQL, with a recording email sender."""

import uuid
from decimal import Decimal

import pytest

from app.core.messaging.consumer import Delivery, RetryLater
from app.core.messaging.envelope import Event
from app.core.money import Money
from app.flights.domain.dtos.bookings import BookingRequest, BookingStatus
from app.flights.domain.models.bookings import Booking
from app.flights.notifications.booking_notifier import BookingConfirmationNotifier
from app.flights.providers.duffel import mapper
from app.flights.services.bookings import BookingService
from app.flights.tests.support import BOOKING_OFFER_ID, TEST_OWNER, load_fixture, make_booking_passenger
from app.notifications.public import EmailDeliveryError, EmailMessage

pytestmark = pytest.mark.anyio


class RecordingSender:
    """An `EmailSender` that keeps what it would send, or fails like a mail server that is down.

    Attributes:
        sent: Every email received, in order.
        failing: Whether `send` raises `EmailDeliveryError`.
    """

    def __init__(self) -> None:
        """Starts empty and working."""
        self.sent: list[EmailMessage] = []
        self.failing = False

    async def send(self, message: EmailMessage) -> None:
        """Records the email, or fails."""
        if self.failing:
            raise EmailDeliveryError("SMTP down")
        self.sent.append(message)


async def confirmed_booking(session_factory, *, confirm: bool = True) -> uuid.UUID:
    """Creates a booking for ana.prueba@example.com and, optionally, confirms it with the captured order.

    Args:
        session_factory: Factory of sessions on the test database.
        confirm: Whether to leave it confirmed or pending.

    Returns:
        The booking id.
    """
    request = BookingRequest(
        offer_id=BOOKING_OFFER_ID,
        expected_price=Money(amount=Decimal("250.00"), currency="USD"),
        passenger=make_booking_passenger(),
        payment_token="tok_fake_4242",
    )
    async with session_factory() as session:
        booking, _ = await BookingService(session, "duffel").create(uuid.uuid4(), request, TEST_OWNER)
    if confirm:
        order = mapper.to_order(load_fixture("duffel/order_create_response.json")["data"])
        async with session_factory() as session, session.begin():
            row = await session.get(Booking, booking.id)
            row.status = BookingStatus.CONFIRMED
            row.booking_reference = order.booking_reference
            row.order = order.model_dump(mode="json", exclude={"id", "offer_id", "booking_id", "total"})
    return booking.id


def confirmed_event(booking_id: uuid.UUID, message_id: uuid.UUID | None = None, attempt: int = 1) -> Delivery:
    """A `booking.confirmed` event of a booking."""
    event = Event(
        message_id=message_id or uuid.uuid4(),
        type="booking.confirmed",
        aggregate_id=booking_id,
        payload={"booking_id": str(booking_id), "status": "confirmed", "version": 3},
    )
    return Delivery(event=event, attempt=attempt, max_attempts=10)


@pytest.fixture
def sender() -> RecordingSender:
    """The recording sender."""
    return RecordingSender()


@pytest.fixture
def notifier(db_session_factory, sender) -> BookingConfirmationNotifier:
    """The notifier under test."""
    return BookingConfirmationNotifier(db_session_factory, sender, app_url="http://localhost:5173")


async def test_emails_the_traveller_at_the_address_saved_in_travellers(notifier, sender, db_session_factory):
    booking_id = await confirmed_booking(db_session_factory)

    await notifier.handle(confirmed_event(booking_id))

    (email,) = sender.sent
    assert email.to == "ana.prueba@example.com"
    assert email.subject == "Reserva confirmada · M6BM7T · London → New York, 15 dic"
    assert f"/bookings/{booking_id}" in email.html


async def test_a_redelivered_event_doesnt_send_it_again(notifier, sender, db_session_factory):
    booking_id = await confirmed_booking(db_session_factory)
    event = confirmed_event(booking_id)

    await notifier.handle(event)
    await notifier.handle(event)

    assert len(sender.sent) == 1


async def test_a_mail_server_that_is_down_retries_later(notifier, sender, db_session_factory):
    booking_id = await confirmed_booking(db_session_factory)
    event = confirmed_event(booking_id)
    sender.failing = True

    with pytest.raises(RetryLater):
        await notifier.handle(event)

    sender.failing = False
    await notifier.handle(confirmed_event(booking_id, message_id=event.event.message_id, attempt=2))
    assert len(sender.sent) == 1


async def test_a_booking_that_isnt_confirmed_gets_no_email(notifier, sender, db_session_factory):
    booking_id = await confirmed_booking(db_session_factory, confirm=False)

    await notifier.handle(confirmed_event(booking_id))

    assert sender.sent == []
