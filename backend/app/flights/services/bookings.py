"""Booking use cases run by the API: create a booking, read it and answer a new price.

The slow part (refreshing the offer, charging and booking with the provider) runs in the booking
worker; see `services.booking_worker`.
"""

import hashlib
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.flights.domain.dtos.bookings import (
    AirlinePassenger,
    BookingRequest,
    BookingStatus,
    PriceDecision,
    PriceDecisionRequest,
)
from app.flights.domain.errors.bookings import (
    BookingNotFoundError,
    IdempotencyKeyReusedError,
    PriceDecisionNotApplicableError,
    PriceMismatchError,
)
from app.flights.domain.models.bookings import Booking
from app.flights.repositories.bookings import BookingRepository
from app.flights.services.booking_prices import approved_price, offered_price
from app.flights.services.booking_state import change_status, request_processing
from app.travellers.public import create_traveller


def request_hash(request: BookingRequest) -> str:
    """SHA-256 of the canonical body, to tell a retry from a key reused with another body."""
    return hashlib.sha256(request.model_dump_json().encode()).hexdigest()


class BookingService:
    """Creates and reads bookings, and records the traveler's price decisions."""

    def __init__(self, session: AsyncSession, provider: str) -> None:
        """Initializes the service.

        Args:
            session: Database session of the request; the service commits its changes.
            provider: Name of the flight provider that sells the offers, e.g. `duffel`.
        """
        self._session = session
        self._bookings = BookingRepository(session)
        self._provider = provider

    async def create(self, idempotency_key: uuid.UUID, request: BookingRequest) -> tuple[Booking, bool]:
        """Creates a booking, idempotently by `Idempotency-Key`.

        In one transaction it saves the traveller (through the travellers module), the booking
        (`pending`) and the `booking.requested` command for the worker. If two requests with the
        same key race, the `UNIQUE` constraint lets one in and the other gets the existing booking.

        Args:
            idempotency_key: Key of this checkout attempt.
            request: What the traveler confirmed.

        Returns:
            The booking, and whether it was created now (`False` for a retry).

        Raises:
            IdempotencyKeyReusedError: The key was already used with another body.
        """
        body_hash = request_hash(request)
        existing = await self._bookings.get_by_idempotency_key(idempotency_key)
        if existing is None:
            try:
                return await self._insert(idempotency_key, body_hash, request), True
            except IntegrityError:
                await self._session.rollback()
                existing = await self._bookings.get_by_idempotency_key(idempotency_key)
                if existing is None:
                    raise
        if existing.request_hash != body_hash:
            raise IdempotencyKeyReusedError("This Idempotency-Key was already used with a different body.")
        return existing, False

    async def get(self, booking_id: uuid.UUID) -> Booking:
        """Reads a booking.

        Args:
            booking_id: Id of the booking.

        Returns:
            The booking.

        Raises:
            BookingNotFoundError: There is no such booking.
        """
        booking = await self._bookings.get(booking_id)
        if booking is None:
            raise BookingNotFoundError("Booking not found.")
        return booking

    async def decide_price(self, booking_id: uuid.UUID, request: PriceDecisionRequest) -> Booking:
        """Records the traveler's answer to a new price.

        Accepting sends the booking back to the worker, which charges the approved price only if
        the offer still costs that much. Repeating the same answer is harmless.

        Args:
            booking_id: Id of the booking.
            request: The decision and the price it answers.

        Returns:
            The booking after the decision.

        Raises:
            BookingNotFoundError: There is no such booking.
            PriceMismatchError: The price isn't the one offered.
            PriceDecisionNotApplicableError: The booking isn't waiting for a decision.
        """
        booking = await self._bookings.get(booking_id, for_update=True)
        if booking is None:
            raise BookingNotFoundError("Booking not found.")
        status = BookingStatus(booking.status)

        if status == BookingStatus.AWAITING_PRICE_APPROVAL:
            if request.price != offered_price(booking):
                raise PriceMismatchError("The price doesn't match the one offered.")
            if request.decision == PriceDecision.ACCEPT:
                change_status(
                    self._session,
                    booking,
                    BookingStatus.PENDING,
                    approved_amount=request.price.amount,
                    approved_currency=request.price.currency,
                )
                request_processing(self._session, booking)
            else:
                change_status(self._session, booking, BookingStatus.CANCELLED)
            await self._session.commit()
            return booking

        # Nothing to change: the row lock is released when the request's session closes.
        if self._already_decided(booking, request):
            return booking
        raise PriceDecisionNotApplicableError(f"The booking is {status}; there is no price to decide on.")

    async def _insert(self, idempotency_key: uuid.UUID, body_hash: str, request: BookingRequest) -> Booking:
        """Saves the traveller, the booking and its command in one transaction."""
        traveller = await create_traveller(self._session, request.passenger.traveller)
        booking = Booking(
            id=uuid.uuid4(),
            idempotency_key=idempotency_key,
            request_hash=body_hash,
            status=BookingStatus.PENDING.value,
            version=1,
            provider=self._provider,
            offer_id=request.offer_id,
            traveller_id=traveller.id,
            passenger=AirlinePassenger.from_booking(request.passenger).model_dump(mode="json"),
            expected_amount=request.expected_price.amount,
            expected_currency=request.expected_price.currency,
            payment_token=request.payment_token,
        )
        self._bookings.add(booking)
        request_processing(self._session, booking)
        await self._session.commit()
        return booking

    @staticmethod
    def _already_decided(booking: Booking, request: PriceDecisionRequest) -> bool:
        """Whether the same decision was already applied (a retry of the request)."""
        if request.decision == PriceDecision.ACCEPT:
            return approved_price(booking) == request.price
        return booking.status == BookingStatus.CANCELLED and offered_price(booking) == request.price
