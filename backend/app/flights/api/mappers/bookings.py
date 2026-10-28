"""From a stored booking to its public view (screen 6, the API and the confirmation email)."""

from app.flights.api.schemas.bookings import BookingPassengerResponse, BookingResponse, OrderResponse
from app.flights.domain.dtos.bookings import AirlinePassenger, BookingStatus, FailureCode
from app.flights.domain.models.bookings import Booking
from app.flights.services.booking_prices import offered_price, price_to_charge


def to_booking_response(booking: Booking) -> BookingResponse:
    """Builds the public view of a booking.

    Only the names of the passenger go out: contact data and documents stay in the travellers
    module, and the order is stored without its cost.

    Args:
        booking: The stored booking.

    Returns:
        The response to send to clients.
    """
    passenger = AirlinePassenger.model_validate(booking.passenger)
    # The reference and the order are shown only for a confirmed booking: an issuance error may
    # keep them for whoever reconciles it, but the traveler must not read them as a ticket.
    confirmed = booking.status == BookingStatus.CONFIRMED
    return BookingResponse(
        id=booking.id,
        status=BookingStatus(booking.status),
        version=booking.version,
        offer_id=booking.offer_id,
        price=price_to_charge(booking),
        offered_price=offered_price(booking),
        failure_code=FailureCode(booking.failure_code) if booking.failure_code else None,
        booking_reference=booking.booking_reference if confirmed else None,
        passenger=BookingPassengerResponse(
            title=passenger.title,
            given_name=passenger.given_name,
            family_name=passenger.family_name,
        ),
        order=OrderResponse.model_validate(booking.order) if confirmed and booking.order else None,
        created_at=booking.created_at,
        updated_at=booking.updated_at,
    )
