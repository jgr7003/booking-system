import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.flights.api.mappers.bookings import to_booking_response
from app.flights.domain.dtos.bookings import AirlinePassenger, BookingStatus
from app.flights.domain.models.bookings import Booking
from app.flights.providers.duffel import mapper
from app.flights.tests.support import load_fixture, make_booking_passenger


def booking_with(status: BookingStatus) -> Booking:
    """A booking in a state, with the order of the captured Duffel booking already saved on it.

    Args:
        status: State of the booking.

    Returns:
        The booking, not persisted.
    """
    order = mapper.to_order(load_fixture("duffel/order_create_response.json")["data"])
    now = datetime.now(UTC)
    return Booking(
        id=uuid.uuid4(),
        idempotency_key=uuid.uuid4(),
        request_hash="",
        status=status.value,
        version=3,
        provider="duffel",
        offer_id="off_1",
        traveller_id=uuid.uuid4(),
        passenger=AirlinePassenger.from_booking(make_booking_passenger()).model_dump(mode="json"),
        expected_amount=Decimal("250.00"),
        expected_currency="USD",
        payment_token="tok_fake_4242",
        booking_reference=order.booking_reference,
        order=order.model_dump(mode="json", exclude={"id", "offer_id", "booking_id", "total"}),
        failure_code="capture_failed" if status == BookingStatus.ISSUANCE_ERROR else None,
        created_at=now,
        updated_at=now,
    )


def test_a_confirmed_booking_shows_its_reference_and_order():
    response = to_booking_response(booking_with(BookingStatus.CONFIRMED))

    assert response.booking_reference == "M6BM7T"
    assert response.order is not None


@pytest.mark.parametrize("status", [BookingStatus.ISSUANCE_ERROR, BookingStatus.PROCESSING, BookingStatus.FAILED])
def test_only_a_confirmed_booking_shows_a_reference_or_an_order(status):
    # An issuance error keeps them for whoever reconciles it; the traveler must not read them as a ticket.
    response = to_booking_response(booking_with(status))

    assert (response.booking_reference, response.order) == (None, None)


def test_an_issuance_error_is_not_final_because_it_gets_reconciled():
    assert not BookingStatus.ISSUANCE_ERROR.is_final
    assert BookingStatus.FAILED.is_final
