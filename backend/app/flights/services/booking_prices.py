"""Prices of a booking: the one the traveler saw, the new one offered and the one approved.

The cost and the markup are never stored: they are recalculated with the pricing policy.
"""

from app.core.money import Money
from app.flights.domain.models.bookings import Booking


def offered_price(booking: Booking) -> Money | None:
    """New price found when refreshing the offer, if it changed."""
    if booking.offered_amount is None or booking.offered_currency is None:
        return None
    return Money(amount=booking.offered_amount, currency=booking.offered_currency)


def approved_price(booking: Booking) -> Money | None:
    """Price the traveler approved after a change, if any."""
    if booking.approved_amount is None or booking.approved_currency is None:
        return None
    return Money(amount=booking.approved_amount, currency=booking.approved_currency)


def price_to_charge(booking: Booking) -> Money:
    """Sale price the booking may charge: the approved one or, without a change, the expected one."""
    return approved_price(booking) or Money(amount=booking.expected_amount, currency=booking.expected_currency)
