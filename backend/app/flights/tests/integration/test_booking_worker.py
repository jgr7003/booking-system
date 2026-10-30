"""BookingProcessor against the test PostgreSQL, the simulated payment gateway and a scripted provider."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.messaging.consumer import Delivery, RetryLater
from app.core.messaging.envelope import Event
from app.core.messaging.inbox import was_processed
from app.core.messaging.models import OutboxMessage
from app.core.money import Money
from app.core.pricing.fixed_fee_random_percent import FixedFeeRandomPercentPolicy
from app.flights.domain.dtos.bookings import (
    BookingRequest,
    BookingStatus,
    PriceDecision,
    PriceDecisionRequest,
)
from app.flights.domain.dtos.offers import OfferAmounts
from app.flights.domain.dtos.orders import BookableOffer, Order, OrderRequest
from app.flights.domain.errors.provider import (
    ProviderError,
    OfferAlreadyBookedError,
    OfferExpiredError,
    OrderRejectedError,
    ProviderTimeoutError,
)
from app.flights.domain.models.bookings import Booking
from app.flights.providers.duffel import mapper
from app.flights.repositories.bookings import BookingRepository
from app.flights.services.booking_worker import CONSUMER, BookingProcessor
from app.flights.services.bookings import BookingService
from app.flights.services.pricing import apply_pricing
from app.flights.tests.support import BOOKING_OFFER_ID, TEST_OWNER, load_fixture, make_booking_passenger
from app.payments.public import Authorization, PaymentError, PaymentGateway, create_payment_gateway

pytestmark = pytest.mark.anyio

# Same policy and secret as the API under test, so prices match.
PRICING = FixedFeeRandomPercentPolicy("test-secret")


class ScriptedProvider:
    """A `FlightProvider` that answers what each test scripts, and records the orders asked for.

    Attributes:
        offer: What `get_offer` returns (or raises, if it's an exception).
        existing_order: What `find_order` returns; set to the created order once one is created.
        create_error: If set, what `create_order` raises instead of creating the order.
        created: Requests of every `create_order` call.
    """

    name = "duffel"

    def __init__(self) -> None:
        """Starts with the captured Duffel offer and order."""
        self.offer: BookableOffer | Exception = mapper.to_bookable_offer(load_fixture("duffel/offer_get_response.json")["data"])
        self.existing_order: Order | None = None
        self.create_error: Exception | None = None
        self.find_error: Exception | None = None
        self.order_created_despite_error = False
        self.created: list[OrderRequest] = []

    def change_cost(self, amount: str) -> None:
        """Makes the airline charge another total from now on.

        Args:
            amount: New total cost.
        """
        offer = self.offer.offer
        cost = OfferAmounts(total=Money(amount=Decimal(amount), currency="USD"), base=None, taxes=offer.cost.taxes)
        self.offer = self.offer.model_copy(update={"offer": offer.model_copy(update={"cost": cost})})

    async def get_offer(self, offer_id: str) -> BookableOffer:
        """Returns or raises the scripted offer."""
        if isinstance(self.offer, Exception):
            raise self.offer
        return self.offer

    async def find_order(self, offer_id: str, booking_id: uuid.UUID) -> Order | None:
        """Returns the scripted order if it belongs to the booking, or raises the scripted error."""
        if self.find_error is not None:
            raise self.find_error
        order = self.existing_order
        return order if order is not None and order.booking_id == booking_id else None

    async def create_order(self, request: OrderRequest) -> Order:
        """Records the request and returns the captured order, or raises the scripted error."""
        self.created.append(request)
        order = mapper.to_order(load_fixture("duffel/order_create_response.json")["data"])
        order = order.model_copy(update={"booking_id": request.booking_id})
        if self.create_error is not None:
            if self.order_created_despite_error:
                self.existing_order = order
            raise self.create_error
        self.existing_order = order
        return order


class Clock:
    """A clock tests move forward, to let leases expire."""

    def __init__(self) -> None:
        """Starts now."""
        self.now = datetime.now(UTC)

    def __call__(self) -> datetime:
        """Returns the current time."""
        return self.now


@pytest.fixture
def provider() -> ScriptedProvider:
    """The scripted provider."""
    return ScriptedProvider()


@pytest.fixture
def clock() -> Clock:
    """The test clock."""
    return Clock()


@pytest.fixture
def gateway(db_session_factory) -> PaymentGateway:
    """The simulated payment gateway on the test database."""
    return create_payment_gateway(db_session_factory)


@pytest.fixture
def processor(db_session_factory, provider, clock, gateway) -> BookingProcessor:
    """The processor under test.

    Args:
        db_session_factory: Factory of sessions on the test database.
        provider: The scripted provider.
        clock: The test clock.
        gateway: The simulated payment gateway.

    Returns:
        The processor.
    """
    return BookingProcessor(db_session_factory, provider, PRICING, gateway, clock=clock)


def sale_price(provider: ScriptedProvider) -> Money:
    """Sale price of the scripted offer, as the search showed it."""
    return apply_pricing(provider.offer.offer, PRICING).price.total


async def create_booking(session_factory, provider, *, payment_token: str = "tok_fake_4242", **traveller) -> uuid.UUID:
    """Creates a pending booking through the API's service, at the price the search showed.

    Args:
        session_factory: Factory of sessions on the test database.
        provider: The scripted provider.
        payment_token: Simulated card.
        **traveller: Personal data to change.

    Returns:
        The booking id.
    """
    request = BookingRequest(
        offer_id=BOOKING_OFFER_ID,
        expected_price=sale_price(provider),
        passenger=make_booking_passenger(**traveller),
        payment_token=payment_token,
    )
    async with session_factory() as session:
        booking, _ = await BookingService(session, "duffel").create(uuid.uuid4(), request, TEST_OWNER)
    return booking.id


def delivery(booking_id: uuid.UUID, *, attempt: int = 1, max_attempts: int = 10, message_id: uuid.UUID | None = None) -> Delivery:
    """A `booking.requested` command for a booking.

    Args:
        booking_id: Id of the booking.
        attempt: Attempt number.
        max_attempts: Attempts allowed.
        message_id: Id of the message; a new one if not given.

    Returns:
        The delivery.
    """
    event = Event(
        message_id=message_id or uuid.uuid4(),
        type="booking.requested",
        aggregate_id=booking_id,
        payload={"booking_id": str(booking_id), "status": "pending", "version": 1},
    )
    return Delivery(event=event, attempt=attempt, max_attempts=max_attempts)


async def booking_of(session_factory, booking_id: uuid.UUID) -> Booking:
    """Reads a booking."""
    async with session_factory() as session:
        return await session.get(Booking, booking_id)


async def authorization_of(session_factory, gateway, booking_id: uuid.UUID) -> Authorization | None:
    """The charge the booking keeps at the gateway, if any.

    Args:
        session_factory: Factory of sessions on the test database.
        gateway: The simulated payment gateway.
        booking_id: Id of the booking.

    Returns:
        The authorization, or `None`.
    """
    authorization_id = (await booking_of(session_factory, booking_id)).payment_authorization_id
    return await gateway.get(authorization_id) if authorization_id else None


async def events(session_factory, booking_id: uuid.UUID) -> list[str]:
    """Routing keys of the outbox events of a booking, oldest first."""
    async with session_factory() as session:
        rows = await session.scalars(
            select(OutboxMessage.routing_key)
            .where(OutboxMessage.aggregate_id == booking_id)
            .order_by(OutboxMessage.created_at)
        )
        return list(rows.all())


async def test_confirms_the_booking_charging_the_sale_price_and_paying_the_cost(processor, provider, db_session_factory, gateway):
    booking_id = await create_booking(db_session_factory, provider)
    command = delivery(booking_id)

    await processor.handle(command)

    booking = await booking_of(db_session_factory, booking_id)
    assert booking.status == BookingStatus.CONFIRMED
    assert booking.booking_reference == "M6BM7T"
    assert booking.provider_order_id == "ord_0000BBq6AsxIyF0XrJSB82"
    assert "total" not in booking.order and booking.order["tickets"][0]["number"] == "1"
    assert booking.lease_until is None
    (request,) = provider.created
    assert request.payment == Money(amount=Decimal("226.75"), currency="USD")
    assert request.passenger_id == "pas_0000BBq6AZuVnyKVD7xG8Q"
    assert request.booking_id == booking_id
    authorization = await authorization_of(db_session_factory, gateway, booking_id)
    assert (authorization.status, authorization.amount) == ("captured", sale_price(provider))
    assert await events(db_session_factory, booking_id) == ["booking.requested", "booking.processing", "booking.confirmed"]
    async with db_session_factory() as session:
        assert await was_processed(session, command.event.message_id, CONSUMER)


async def test_a_redelivered_command_does_nothing(processor, provider, db_session_factory, gateway):
    booking_id = await create_booking(db_session_factory, provider)
    command = delivery(booking_id)
    await processor.handle(command)

    await processor.handle(command)
    await processor.handle(delivery(booking_id))  # another copy, e.g. published twice by the relay

    assert len(provider.created) == 1
    assert len(await events(db_session_factory, booking_id)) == 3


async def test_a_new_price_waits_for_the_travelers_approval_without_charging(processor, provider, db_session_factory, gateway):
    booking_id = await create_booking(db_session_factory, provider)
    provider.change_cost("240.00")

    await processor.handle(delivery(booking_id))

    booking = await booking_of(db_session_factory, booking_id)
    assert booking.status == BookingStatus.AWAITING_PRICE_APPROVAL
    assert Money(amount=booking.offered_amount, currency=booking.offered_currency) == sale_price(provider)
    assert provider.created == []
    assert await authorization_of(db_session_factory, gateway, booking_id) is None


async def test_after_approval_it_books_at_the_approved_price(processor, provider, db_session_factory, gateway):
    booking_id = await create_booking(db_session_factory, provider)
    provider.change_cost("240.00")
    await processor.handle(delivery(booking_id))
    new_price = sale_price(provider)

    async with db_session_factory() as session:
        await BookingService(session, "duffel").decide_price(
            booking_id, PriceDecisionRequest(decision=PriceDecision.ACCEPT, price=new_price), TEST_OWNER
        )
    await processor.handle(delivery(booking_id))

    assert (await booking_of(db_session_factory, booking_id)).status == BookingStatus.CONFIRMED
    assert provider.created[0].payment == Money(amount=Decimal("240.00"), currency="USD")
    authorization = await authorization_of(db_session_factory, gateway, booking_id)
    assert (authorization.status, authorization.amount) == ("captured", new_price)


async def test_a_second_change_after_the_approval_asks_again(processor, provider, db_session_factory, gateway):
    booking_id = await create_booking(db_session_factory, provider)
    provider.change_cost("240.00")
    await processor.handle(delivery(booking_id))
    async with db_session_factory() as session:
        await BookingService(session, "duffel").decide_price(
            booking_id, PriceDecisionRequest(decision=PriceDecision.ACCEPT, price=sale_price(provider)), TEST_OWNER
        )
    provider.change_cost("250.00")

    await processor.handle(delivery(booking_id))

    booking = await booking_of(db_session_factory, booking_id)
    assert booking.status == BookingStatus.AWAITING_PRICE_APPROVAL
    assert Money(amount=booking.offered_amount, currency="USD") == sale_price(provider)
    assert provider.created == []


async def test_an_expired_offer_fails_the_booking(processor, provider, db_session_factory, gateway):
    booking_id = await create_booking(db_session_factory, provider)
    provider.offer = OfferExpiredError("expired")

    await processor.handle(delivery(booking_id))

    booking = await booking_of(db_session_factory, booking_id)
    assert (booking.status, booking.failure_code) == (BookingStatus.FAILED, "offer_expired")


async def test_a_declined_card_fails_the_booking_without_booking(processor, provider, db_session_factory, gateway):
    booking_id = await create_booking(db_session_factory, provider, payment_token="tok_fake_0002")

    await processor.handle(delivery(booking_id))

    booking = await booking_of(db_session_factory, booking_id)
    assert (booking.status, booking.failure_code) == (BookingStatus.FAILED, "payment_declined")
    assert provider.created == []


async def test_a_rejected_order_fails_and_releases_the_charge(processor, provider, db_session_factory, gateway):
    booking_id = await create_booking(db_session_factory, provider)
    provider.create_error = OrderRejectedError("invalid passenger")

    await processor.handle(delivery(booking_id))

    booking = await booking_of(db_session_factory, booking_id)
    assert (booking.status, booking.failure_code) == (BookingStatus.FAILED, "provider_rejected")
    authorization = await authorization_of(db_session_factory, gateway, booking_id)
    assert authorization.status == "voided"


async def test_a_missing_passport_fails_before_charging(processor, provider, db_session_factory, gateway):
    booking_id = await create_booking(db_session_factory, provider)
    offer = provider.offer.offer.model_copy(update={"requires_identity_documents": True})
    provider.offer = provider.offer.model_copy(update={"offer": offer})

    await processor.handle(delivery(booking_id))

    booking = await booking_of(db_session_factory, booking_id)
    assert (booking.status, booking.failure_code) == (BookingStatus.FAILED, "passenger_rejected")
    assert await authorization_of(db_session_factory, gateway, booking_id) is None


async def test_a_traveler_under_18_on_the_departure_day_fails_as_adult(processor, provider, db_session_factory, gateway):
    # The captured offer departs on 2026-12-15.
    booking_id = await create_booking(db_session_factory, provider, born_on="2008-12-16")

    await processor.handle(delivery(booking_id))

    assert (await booking_of(db_session_factory, booking_id)).failure_code == "passenger_rejected"


async def test_an_order_created_by_an_earlier_attempt_is_adopted_instead_of_booking_again(
    processor, provider, db_session_factory, clock, gateway
):
    booking_id = await create_booking(db_session_factory, provider)
    provider.create_error = ProviderTimeoutError("slow")
    provider.order_created_despite_error = True

    with pytest.raises(RetryLater):
        await processor.handle(delivery(booking_id, attempt=1))
    assert (await booking_of(db_session_factory, booking_id)).status == BookingStatus.PROCESSING

    # The retry doesn't wait for any lease: the failing worker freed the booking.
    await processor.handle(delivery(booking_id, attempt=2))

    assert (await booking_of(db_session_factory, booking_id)).status == BookingStatus.CONFIRMED
    assert len(provider.created) == 1
    authorization = await authorization_of(db_session_factory, gateway, booking_id)
    assert authorization.status == "captured"


async def test_an_offer_already_booked_by_this_booking_is_adopted(processor, provider, db_session_factory, gateway):
    booking_id = await create_booking(db_session_factory, provider)
    provider.create_error = OfferAlreadyBookedError("already booked")
    provider.order_created_despite_error = True

    await processor.handle(delivery(booking_id))

    assert (await booking_of(db_session_factory, booking_id)).status == BookingStatus.CONFIRMED


async def test_an_offer_already_booked_by_someone_else_fails(processor, provider, db_session_factory, gateway):
    booking_id = await create_booking(db_session_factory, provider)
    provider.create_error = OfferAlreadyBookedError("already booked")

    await processor.handle(delivery(booking_id))

    booking = await booking_of(db_session_factory, booking_id)
    assert (booking.status, booking.failure_code) == (BookingStatus.FAILED, "offer_unavailable")
    authorization = await authorization_of(db_session_factory, gateway, booking_id)
    assert authorization.status == "voided"


async def test_a_retry_after_a_provider_failure_takes_the_booking_at_once(
    processor, provider, db_session_factory
):
    booking_id = await create_booking(db_session_factory, provider)
    provider.create_error = ProviderTimeoutError("slow")
    with pytest.raises(RetryLater):
        await processor.handle(delivery(booking_id))
    booking = await booking_of(db_session_factory, booking_id)
    assert (booking.status, booking.lease_until) == (BookingStatus.PROCESSING, None)
    provider.create_error = None

    await processor.handle(delivery(booking_id, attempt=2))

    assert (await booking_of(db_session_factory, booking_id)).status == BookingStatus.CONFIRMED


async def test_every_retry_after_a_provider_failure_calls_the_provider_again(processor, provider, db_session_factory):
    booking_id = await create_booking(db_session_factory, provider)
    provider.create_error = ProviderTimeoutError("slow")

    for attempt in (1, 2, 3):
        with pytest.raises(RetryLater, match="slow"):
            await processor.handle(delivery(booking_id, attempt=attempt))

    # Nothing was dropped as "held by another worker": each attempt reached the provider.
    assert len(provider.created) == 3


async def test_a_booking_held_by_a_live_worker_is_retried_until_its_lease_expires(
    processor, provider, db_session_factory, clock
):
    booking_id = await create_booking(db_session_factory, provider)
    # Another worker takes the booking and keeps it (a live lease, no failure to release it).
    async with db_session_factory() as session, session.begin():
        await BookingRepository(session).claim(booking_id, now=clock(), lease=timedelta(minutes=4))

    with pytest.raises(RetryLater, match="another worker"):
        await processor.handle(delivery(booking_id, attempt=2))
    assert provider.created == []

    clock.now += timedelta(minutes=5)  # that worker died: its lease expired
    await processor.handle(delivery(booking_id, attempt=3))
    assert (await booking_of(db_session_factory, booking_id)).status == BookingStatus.CONFIRMED


async def test_on_the_last_attempt_without_an_order_it_fails_and_releases_the_charge(
    processor, provider, db_session_factory, gateway
):
    booking_id = await create_booking(db_session_factory, provider)
    provider.create_error = ProviderTimeoutError("slow")

    await processor.handle(delivery(booking_id, attempt=10, max_attempts=10))

    booking = await booking_of(db_session_factory, booking_id)
    assert (booking.status, booking.failure_code) == (BookingStatus.FAILED, "provider_unavailable")
    authorization = await authorization_of(db_session_factory, gateway, booking_id)
    assert authorization.status == "voided"


async def test_commands_of_finished_bookings_are_ignored(processor, provider, db_session_factory, gateway):
    booking_id = await create_booking(db_session_factory, provider)
    provider.offer = OfferExpiredError("expired")
    await processor.handle(delivery(booking_id))

    await processor.handle(delivery(booking_id))

    assert await events(db_session_factory, booking_id) == ["booking.requested", "booking.processing", "booking.failed"]


class FailingCaptureGateway:
    """A gateway whose authorizations work but whose captures are refused, like an expired hold."""

    def __init__(self, gateway: PaymentGateway) -> None:
        """Wraps a working gateway."""
        self._gateway = gateway

    async def verify_card(self, request):
        """Verifies normally."""
        return await self._gateway.verify_card(request)

    async def authorize(self, request):
        """Authorizes normally."""
        return await self._gateway.authorize(request)

    async def capture(self, authorization_id):
        """Refuses to capture."""
        raise PaymentError("The authorization expired.")

    async def void(self, authorization_id):
        """Voids normally."""
        return await self._gateway.void(authorization_id)

    async def get(self, authorization_id):
        """Reads normally."""
        return await self._gateway.get(authorization_id)


async def test_an_order_whose_charge_cant_be_captured_is_an_issuance_error_and_keeps_the_hold(
    provider, db_session_factory, gateway, clock
):
    processor = BookingProcessor(db_session_factory, provider, PRICING, FailingCaptureGateway(gateway), clock=clock)
    booking_id = await create_booking(db_session_factory, provider)

    await processor.handle(delivery(booking_id))

    booking = await booking_of(db_session_factory, booking_id)
    assert (booking.status, booking.failure_code) == (BookingStatus.ISSUANCE_ERROR, "capture_failed")
    assert booking.lease_until is None
    # The ticket exists, so it is kept for whoever reconciles it; the money is not released.
    assert (booking.provider_order_id, booking.booking_reference) == ("ord_0000BBq6AsxIyF0XrJSB82", "M6BM7T")
    assert (await authorization_of(db_session_factory, gateway, booking_id)).status == "authorized"
    assert len(provider.created) == 1


async def test_an_issuance_error_is_not_processed_again_nor_booked_twice(provider, db_session_factory, gateway, clock):
    processor = BookingProcessor(db_session_factory, provider, PRICING, FailingCaptureGateway(gateway), clock=clock)
    booking_id = await create_booking(db_session_factory, provider)
    await processor.handle(delivery(booking_id))

    await processor.handle(delivery(booking_id))

    assert len(provider.created) == 1
    assert (await booking_of(db_session_factory, booking_id)).status == BookingStatus.ISSUANCE_ERROR


async def test_if_the_provider_cant_even_say_whether_the_order_exists_it_is_an_issuance_error_not_a_failure(
    processor, provider, db_session_factory, gateway
):
    booking_id = await create_booking(db_session_factory, provider)
    provider.create_error = ProviderTimeoutError("slow")
    with pytest.raises(RetryLater):
        await processor.handle(delivery(booking_id, attempt=1))  # authorizes, then the order times out
    provider.find_error = ProviderError("provider down")  # and now nothing can be verified

    await processor.handle(delivery(booking_id, attempt=10, max_attempts=10))

    booking = await booking_of(db_session_factory, booking_id)
    assert (booking.status, booking.failure_code) == (BookingStatus.ISSUANCE_ERROR, "order_unverified")
    # A ticket may have been issued: the money is not released.
    assert (await authorization_of(db_session_factory, gateway, booking_id)).status == "authorized"


async def test_an_unexpected_error_frees_the_booking_for_the_retry(processor, provider, db_session_factory):
    booking_id = await create_booking(db_session_factory, provider)
    provider.offer = RuntimeError("a bug")

    with pytest.raises(RuntimeError):
        await processor.handle(delivery(booking_id))

    assert (await booking_of(db_session_factory, booking_id)).lease_until is None


async def test_the_card_is_verified_before_the_real_charge_and_a_failed_reversal_doesnt_stop_the_booking(
    processor, provider, db_session_factory, gateway, caplog
):
    booking_id = await create_booking(db_session_factory, provider, payment_token="tok_fake_0003")

    await processor.handle(delivery(booking_id))

    # The card works, so the booking goes on; the small charge is left for a human to refund.
    assert (await booking_of(db_session_factory, booking_id)).status == BookingStatus.CONFIRMED
    assert "was not reversed; refund it by hand" in caplog.text
    assert (await authorization_of(db_session_factory, gateway, booking_id)).status == "captured"


async def test_a_card_that_fails_the_verification_never_gets_the_real_charge(
    processor, provider, db_session_factory, gateway
):
    booking_id = await create_booking(db_session_factory, provider, payment_token="tok_fake_0002")

    await processor.handle(delivery(booking_id))

    booking = await booking_of(db_session_factory, booking_id)
    assert (booking.status, booking.failure_code) == (BookingStatus.FAILED, "payment_declined")
    assert booking.payment_authorization_id is None
    assert provider.created == []
