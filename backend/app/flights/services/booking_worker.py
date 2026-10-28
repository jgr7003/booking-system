"""Background processing of a booking: reconfirm the price, charge and book with the provider.

Runs in the booking worker for each `booking.requested` command. The steps and why they are
safe to repeat are in docs/superpowers/specs/2026-10-27-reserva-vuelos-design.md §5.4.
"""

import logging
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.messaging.consumer import Delivery, RetryLater
from app.core.messaging.inbox import mark_processed, was_processed
from app.core.money import Money
from app.core.pricing.base import PricingPolicy
from app.flights.domain.constants.bookings import BOOKING_LEASE_S, MAX_PASSENGERS_PER_BOOKING
from app.flights.domain.constants.search import ADULT_AGE
from app.flights.domain.dtos.bookings import AirlinePassenger, BookingStatus, FailureCode
from app.flights.domain.dtos.orders import BookableOffer, Order, OrderRequest
from app.flights.domain.errors.provider import (
    OfferAlreadyBookedError,
    OfferExpiredError,
    OfferUnavailableError,
    OrderRejectedError,
    ProviderError,
)
from app.flights.domain.models.bookings import Booking
from app.flights.domain.validators.passengers import age_on
from app.flights.providers.base import FlightProvider
from app.flights.repositories.bookings import BookingRepository
from app.flights.services.booking_state import announce, change_status
from app.flights.services.booking_prices import price_to_charge
from app.flights.services.pricing import apply_pricing
from app.payments.public import (
    CardVerificationRequest,
    PaymentDeclinedError,
    PaymentError,
    PaymentGateway,
    PaymentRequest,
)

logger = logging.getLogger(__name__)

# Name of this consumer in the inbox.
CONSUMER = "flights.booking-worker"


class BookingProcessor:
    """Handles the `booking.requested` commands of the booking worker."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        provider: FlightProvider,
        pricing: PricingPolicy,
        payments: PaymentGateway,
        *,
        lease: timedelta = timedelta(seconds=BOOKING_LEASE_S),
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        """Initializes the processor.

        Args:
            session_factory: Factory of database sessions; each step uses its own transaction.
            provider: Flight provider that sells the offers.
            pricing: The platform's pricing policy, to recalculate the sale price.
            payments: Gateway that charges the traveler.
            lease: How long the processor owns a booking it takes.
            clock: Current time (fixed in tests).
        """
        self._session_factory = session_factory
        self._provider = provider
        self._pricing = pricing
        self._payments = payments
        self._lease = lease
        self._clock = clock

    async def handle(self, delivery: Delivery) -> None:
        """Processes one `booking.requested` command.

        Args:
            delivery: The command, with its attempt number.

        Raises:
            RetryLater: The provider failed transiently, or another worker holds the booking;
                the consumer delivers the command again later.
        """
        message_id = delivery.event.message_id
        booking_id = uuid.UUID(delivery.event.payload["booking_id"])
        async with self._session_factory() as session:
            if await was_processed(session, message_id, CONSUMER):
                return

        booking = await self._claim(booking_id)
        if booking is None:
            await self._when_not_claimable(booking_id, delivery)
            return

        try:
            await self._process(booking, message_id)
        except ProviderError as exc:
            if not delivery.is_last_attempt:
                # This worker is alive and asking for a retry: free the booking so the next
                # delivery takes it right away instead of waiting for a lease nobody uses.
                await self._release(booking)
                raise RetryLater(str(exc)) from exc
            await self._give_up(booking, message_id)
        except Exception:
            # Not a provider failure (a bug, the database...): this worker is alive, so free the
            # booking for the retry instead of leaving it behind a lease nobody uses.
            await self._release(booking)
            raise

    async def _claim(self, booking_id: uuid.UUID) -> Booking | None:
        """Takes the booking (`processing`) and announces it, or returns `None` if it can't."""
        async with self._session_factory() as session, session.begin():
            booking = await BookingRepository(session).claim(booking_id, now=self._clock(), lease=self._lease)
            if booking is not None:
                announce(session, booking)
            return booking

    async def _release(self, booking: Booking) -> None:
        """Frees a booking this worker holds, leaving it `processing`, so a retry can take it at once."""
        async with self._session_factory() as session, session.begin():
            locked = await BookingRepository(session).get(booking.id, for_update=True)
            if locked.status == BookingStatus.PROCESSING:
                locked.lease_until = None

    async def _when_not_claimable(self, booking_id: uuid.UUID, delivery: Delivery) -> None:
        """Decides what to do with a command whose booking couldn't be taken."""
        async with self._session_factory() as session:
            booking = await BookingRepository(session).get(booking_id)
        if booking is None or booking.status != BookingStatus.PROCESSING:
            # Already decided (final, or waiting for the traveler): nothing to do.
            return
        if delivery.is_last_attempt:
            logger.warning("Booking %s is still held by another worker; dropping the command", booking_id)
            return
        # Another worker holds it with a live lease, or held it and died: retry until it expires.
        raise RetryLater(f"booking {booking_id} is being processed by another worker")

    async def _process(self, booking: Booking, message_id: uuid.UUID) -> None:
        """Reconciles, reconfirms the price, charges and books."""
        order = await self._provider.find_order(booking.offer_id, booking.id)
        if order is not None:
            await self._confirm(booking, message_id, order)
            return

        try:
            bookable = await self._provider.get_offer(booking.offer_id)
        except OfferExpiredError:
            await self._fail(booking, message_id, FailureCode.OFFER_EXPIRED)
            return
        except OfferUnavailableError:
            await self._fail(booking, message_id, FailureCode.OFFER_UNAVAILABLE)
            return

        offer = apply_pricing(bookable.offer, self._pricing)
        price = offer.price.total
        if price != price_to_charge(booking):
            await self._ask_for_approval(booking, message_id, price)
            return

        passenger = AirlinePassenger.model_validate(booking.passenger)
        if (problem := _passenger_problem(bookable, passenger)) is not None:
            logger.info("Booking %s rejected before booking: %s", booking.id, problem)
            await self._fail(booking, message_id, FailureCode.PASSENGER_REJECTED)
            return

        # Before the real charge: a small purchase checks the card, then it is reversed.
        try:
            verification = await self._payments.verify_card(
                CardVerificationRequest(
                    idempotency_key=f"flights-booking:{booking.id}:verification",
                    currency=price.currency,
                    payment_token=booking.payment_token,
                )
            )
        except PaymentDeclinedError:
            await self._fail(booking, message_id, FailureCode.PAYMENT_DECLINED)
            return
        if not verification.reversed:
            # The booking goes on: the traveler's card works. The small charge needs a refund.
            logger.error(
                "Booking %s: the card verification purchase %s (%s %s) was not reversed; refund it by hand",
                booking.id,
                verification.id,
                verification.amount.amount,
                verification.amount.currency,
            )

        try:
            authorization = await self._payments.authorize(
                PaymentRequest(
                    idempotency_key=f"flights-booking:{booking.id}:{price.amount}{price.currency}",
                    amount=price,
                    payment_token=booking.payment_token,
                )
            )
        except PaymentDeclinedError:
            await self._fail(booking, message_id, FailureCode.PAYMENT_DECLINED)
            return
        await self._save_authorization(booking, authorization.id)

        try:
            order = await self._provider.create_order(
                OrderRequest(
                    offer_id=booking.offer_id,
                    passenger_id=bookable.passenger_ids[0],
                    passenger=passenger,
                    payment=offer.cost.total,
                    booking_id=booking.id,
                )
            )
        except OfferAlreadyBookedError:
            # Maybe by this booking, in an attempt whose answer was lost.
            order = await self._provider.find_order(booking.offer_id, booking.id)
            if order is None:
                await self._fail(booking, message_id, FailureCode.OFFER_UNAVAILABLE)
                return
        except OfferExpiredError:
            await self._fail(booking, message_id, FailureCode.OFFER_EXPIRED)
            return
        except OfferUnavailableError:
            await self._fail(booking, message_id, FailureCode.OFFER_UNAVAILABLE)
            return
        except OrderRejectedError as exc:
            logger.warning("Provider rejected the order of booking %s: %s", booking.id, exc.message)
            await self._fail(booking, message_id, FailureCode.PROVIDER_REJECTED)
            return
        await self._confirm(booking, message_id, order)

    async def _give_up(self, booking: Booking, message_id: uuid.UUID) -> None:
        """Last attempt after transient failures: confirm if the order exists, fail if it doesn't.

        If the provider can't even say whether the order exists, the outcome is unknown: it is an
        issuance error (the charge stays authorized), never a failure that releases the money while
        a ticket may have been issued.
        """
        try:
            order = await self._provider.find_order(booking.offer_id, booking.id)
        except ProviderError:
            await self._issuance_error(booking, message_id, FailureCode.ORDER_UNVERIFIED)
            return
        if order is not None:
            await self._confirm(booking, message_id, order)
        else:
            await self._fail(booking, message_id, FailureCode.PROVIDER_UNAVAILABLE)

    async def _confirm(self, booking: Booking, message_id: uuid.UUID, order: Order) -> None:
        """Captures the charge and saves the confirmed order."""
        authorization_id = await self._authorization_of(booking)
        if authorization_id is None:
            # The order exists but this booking never got to authorize (shouldn't happen).
            authorization_id = (
                await self._payments.authorize(
                    PaymentRequest(
                        idempotency_key=f"flights-booking:{booking.id}:reconciled",
                        amount=price_to_charge(booking),
                        payment_token=booking.payment_token,
                    )
                )
            ).id
        try:
            await self._payments.capture(authorization_id)
        except PaymentError as exc:
            # The order exists but the money can't be collected: not a failure, nothing to roll back.
            logger.error("Booking %s: order %s exists but the charge failed: %s", booking.id, order.id, exc.message)
            await self._issuance_error(booking, message_id, FailureCode.CAPTURE_FAILED, order=order)
            return
        async with self._session_factory() as session, session.begin():
            locked = await BookingRepository(session).get(booking.id, for_update=True)
            if locked.status == BookingStatus.PROCESSING:
                change_status(
                    session,
                    locked,
                    BookingStatus.CONFIRMED,
                    payment_authorization_id=authorization_id,
                    provider_order_id=order.id,
                    booking_reference=order.booking_reference,
                    # Without `total`: it's the provider's cost, which the booking never keeps.
                    order=order.model_dump(mode="json", exclude={"id", "offer_id", "booking_id", "total"}),
                    lease_until=None,
                )
            await mark_processed(session, message_id, CONSUMER)
        logger.info("Booking %s confirmed: %s", booking.id, order.booking_reference)

    async def _issuance_error(
        self,
        booking: Booking,
        message_id: uuid.UUID,
        code: FailureCode,
        order: Order | None = None,
    ) -> None:
        """Parks a booking whose outcome with the airline or the charge can't be settled now.

        The authorization is **not** voided: the airline may have issued the booking, and releasing
        the money would leave a ticket nobody paid for. The order, if known, is kept for whoever
        reconciles it. The traveler is never shown it as confirmed.
        """
        fields: dict[str, object] = {"failure_code": code, "lease_until": None}
        if order is not None:
            fields |= {
                "provider_order_id": order.id,
                "booking_reference": order.booking_reference,
                "order": order.model_dump(mode="json", exclude={"id", "offer_id", "booking_id", "total"}),
            }
        async with self._session_factory() as session, session.begin():
            locked = await BookingRepository(session).get(booking.id, for_update=True)
            if locked.status == BookingStatus.PROCESSING:
                change_status(session, locked, BookingStatus.ISSUANCE_ERROR, **fields)
            await mark_processed(session, message_id, CONSUMER)
        logger.error(
            "Booking %s ended in an issuance error (%s). Check the provider for an order of offer %s with "
            "metadata.booking_id=%s and the payment authorization before releasing or capturing it.",
            booking.id,
            code,
            booking.offer_id,
            booking.id,
        )

    async def _ask_for_approval(self, booking: Booking, message_id: uuid.UUID, price: Money) -> None:
        """Stops before charging and waits for the traveler to answer the new price."""
        await self._void(booking)
        async with self._session_factory() as session, session.begin():
            locked = await BookingRepository(session).get(booking.id, for_update=True)
            if locked.status == BookingStatus.PROCESSING:
                change_status(
                    session,
                    locked,
                    BookingStatus.AWAITING_PRICE_APPROVAL,
                    offered_amount=price.amount,
                    offered_currency=price.currency,
                    payment_authorization_id=None,
                    lease_until=None,
                )
            await mark_processed(session, message_id, CONSUMER)
        logger.info("Booking %s waits for approval of a new price: %s %s", booking.id, price.amount, price.currency)

    async def _fail(self, booking: Booking, message_id: uuid.UUID, code: FailureCode) -> None:
        """Releases the charge, if any, and marks the booking as failed."""
        await self._void(booking)
        async with self._session_factory() as session, session.begin():
            locked = await BookingRepository(session).get(booking.id, for_update=True)
            if locked.status == BookingStatus.PROCESSING:
                change_status(session, locked, BookingStatus.FAILED, failure_code=code, lease_until=None)
            await mark_processed(session, message_id, CONSUMER)
        logger.info("Booking %s failed: %s", booking.id, code)

    async def _save_authorization(self, booking: Booking, authorization_id: uuid.UUID) -> None:
        """Keeps the authorization id, so a later attempt can capture or void it."""
        async with self._session_factory() as session, session.begin():
            locked = await BookingRepository(session).get(booking.id, for_update=True)
            locked.payment_authorization_id = authorization_id

    async def _authorization_of(self, booking: Booking) -> uuid.UUID | None:
        """Reads the authorization id saved by this or an earlier attempt."""
        async with self._session_factory() as session:
            return (await BookingRepository(session).get(booking.id)).payment_authorization_id

    async def _void(self, booking: Booking) -> None:
        """Releases the authorized charge of the booking, if there is one."""
        authorization_id = await self._authorization_of(booking)
        if authorization_id is not None:
            await self._payments.void(authorization_id)


def _passenger_problem(bookable: BookableOffer, passenger: AirlinePassenger) -> str | None:
    """Checks the passenger against the offer: count, passport and age on the departure day."""
    if len(bookable.passenger_ids) != MAX_PASSENGERS_PER_BOOKING:
        return f"the offer has {len(bookable.passenger_ids)} passengers; only {MAX_PASSENGERS_PER_BOOKING} is supported"
    if bookable.offer.requires_identity_documents and passenger.passport is None:
        return "the offer requires a passport"
    departure = bookable.offer.slices[0].segments[0].departing_at.date()
    if age_on(passenger.born_on, departure) < ADULT_AGE:
        return f"an adult must be {ADULT_AGE} or older on {departure.isoformat()}"
    return None
