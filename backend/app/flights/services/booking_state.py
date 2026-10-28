"""Changes of state of a booking, each one with its event in the outbox (same transaction)."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.messaging.outbox import add_event
from app.flights.core.messaging import BOOKING_COMMANDS, BOOKING_EVENTS, BOOKING_REQUESTED
from app.flights.domain.dtos.bookings import BookingStatus
from app.flights.domain.models.bookings import Booking


def event_payload(booking: Booking) -> dict[str, object]:
    """Body of the events of a booking: ids, state and version, never personal data.

    Args:
        booking: The booking.

    Returns:
        The JSON body.
    """
    return {"booking_id": str(booking.id), "status": booking.status, "version": booking.version}


def announce(session: AsyncSession, booking: Booking) -> None:
    """Adds the `booking.<status>` event of the booking's current state to the outbox.

    Call it after any change of status that didn't go through `change_status` (e.g. the atomic
    claim of the worker).

    Args:
        session: Session of the transaction that changed the state.
        booking: The booking, already in its new state.
    """
    add_event(
        session,
        exchange=BOOKING_EVENTS.name,
        routing_key=f"booking.{booking.status}",
        aggregate_id=booking.id,
        payload=event_payload(booking),
    )


def change_status(session: AsyncSession, booking: Booking, status: BookingStatus, **fields: object) -> None:
    """Moves a booking to another state, bumps its version and announces it.

    Args:
        session: Session of the transaction; the booking must be locked in it.
        booking: The booking.
        status: The new state.
        **fields: Other columns to set at the same time, e.g. `failure_code`.
    """
    for name, value in fields.items():
        setattr(booking, name, value)
    booking.status = status
    booking.version += 1
    announce(session, booking)


def request_processing(session: AsyncSession, booking: Booking) -> None:
    """Sends the `booking.requested` command for the worker to process the booking.

    Args:
        session: Session of the transaction that left the booking `pending`.
        booking: The booking.
    """
    add_event(
        session,
        exchange=BOOKING_COMMANDS.name,
        routing_key=BOOKING_REQUESTED,
        aggregate_id=booking.id,
        payload=event_payload(booking),
    )
