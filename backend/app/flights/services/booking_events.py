"""Stream of the state changes of one booking, for Server-Sent Events."""

import asyncio
import uuid
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.messaging.broadcaster import EventBroadcaster
from app.flights.domain.dtos.bookings import BookingOwner, BookingStatus
from app.flights.domain.errors.bookings import BookingNotFoundError
from app.flights.repositories.bookings import BookingRepository
from app.flights.services.booking_state import event_payload

# Without events, the state is read again from the database this often, in case an event was
# lost (RabbitMQ down, API restarted...).
RECHECK_INTERVAL_S = 15


async def booking_status_stream(
    booking_id: uuid.UUID,
    owner: BookingOwner,
    session_factory: async_sessionmaker[AsyncSession],
    broadcaster: EventBroadcaster,
    *,
    recheck_interval_s: float = RECHECK_INTERVAL_S,
) -> AsyncIterator[dict[str, Any]]:
    """Yields the state of a booking now and every time it changes, until it is final.

    It subscribes to the events **before** reading the database, so a change between the read
    and the subscription isn't lost. Events with a version already sent are skipped, so a
    duplicated or late event never moves the state backwards.

    Args:
        booking_id: Id of the booking; it must exist.
        owner: Who watches it; every read is filtered by them.
        session_factory: Factory of database sessions (each read uses a short one, so the
            connection isn't held for the whole stream).
        broadcaster: Source of the booking events.
        recheck_interval_s: Wait before reading the database again when no event arrives.

    Yields:
        `{"booking_id", "status", "version"}`, the same body as the events.
    """
    async with broadcaster.subscribe(booking_id) as events:
        current = await _read(session_factory, booking_id, owner)
        yield current
        while not BookingStatus(current["status"]).is_final:
            try:
                candidate = (await asyncio.wait_for(events.get(), recheck_interval_s)).payload
            except TimeoutError:
                candidate = await _read(session_factory, booking_id, owner)
            if candidate["version"] > current["version"]:
                current = candidate
                yield current


async def _read(
    session_factory: async_sessionmaker[AsyncSession], booking_id: uuid.UUID, owner: BookingOwner
) -> dict[str, Any]:
    """Reads the current state of a booking of the owner."""
    async with session_factory() as session:
        booking = await BookingRepository(session).get_owned(booking_id, owner)
        if booking is None:
            raise BookingNotFoundError("Booking not found.")
        return event_payload(booking)
