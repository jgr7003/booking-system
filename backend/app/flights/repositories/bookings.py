"""Persistence of bookings in PostgreSQL."""

import uuid
from datetime import datetime, timedelta

from sqlalchemy import or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.flights.domain.dtos.bookings import BookingStatus
from app.flights.domain.models.bookings import Booking


class BookingRepository:
    """Reads and writes `flights.bookings`, inside the caller's transaction. It never commits."""

    def __init__(self, session: AsyncSession) -> None:
        """Initializes the repository.

        Args:
            session: Session of the transaction to work in.
        """
        self._session = session

    def add(self, booking: Booking) -> None:
        """Adds a new booking to the transaction.

        Args:
            booking: The booking to insert.
        """
        self._session.add(booking)

    async def get(self, booking_id: uuid.UUID, *, for_update: bool = False) -> Booking | None:
        """Finds a booking by id.

        Args:
            booking_id: Id of the booking.
            for_update: Lock the row until the transaction ends, to change it safely.

        Returns:
            The booking, or `None`.
        """
        return await self._session.get(Booking, booking_id, with_for_update=for_update, populate_existing=for_update)

    async def get_by_idempotency_key(self, idempotency_key: uuid.UUID) -> Booking | None:
        """Finds the booking created with an `Idempotency-Key`.

        Args:
            idempotency_key: The key.

        Returns:
            The booking, or `None`.
        """
        return await self._session.scalar(select(Booking).where(Booking.idempotency_key == idempotency_key))

    async def claim(self, booking_id: uuid.UUID, *, now: datetime, lease: timedelta) -> Booking | None:
        """Takes a booking for processing, atomically.

        A booking can be taken when it is `pending`, or when it is `processing` and free: its
        lease expired (the worker that had it died) or was released (the worker that had it asked
        for a retry after a transient failure).

        Args:
            booking_id: Id of the booking.
            now: Current time.
            lease: How long the caller owns the booking.

        Returns:
            The booking, now `processing` with a new version, or `None` if it can't be taken.
        """
        return await self._session.scalar(
            update(Booking)
            .where(
                Booking.id == booking_id,
                or_(
                    Booking.status == BookingStatus.PENDING,
                    (Booking.status == BookingStatus.PROCESSING)
                    & (Booking.lease_until.is_(None) | (Booking.lease_until < now)),
                ),
            )
            .values(status=BookingStatus.PROCESSING, version=Booking.version + 1, lease_until=now + lease)
            .returning(Booking)
            .execution_options(populate_existing=True)
        )
