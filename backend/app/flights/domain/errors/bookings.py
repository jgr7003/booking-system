"""Errors of the bookings API."""

from app.core.errors import AppError


class IdempotencyKeyRequiredError(AppError):
    """`POST /bookings` came without a valid `Idempotency-Key` header. Answered as HTTP 400."""

    code = "idempotency_key_required"


class IdempotencyKeyReusedError(AppError):
    """The `Idempotency-Key` was already used with another body. Answered as HTTP 422."""

    code = "idempotency_key_reused"


class BookingNotFoundError(AppError):
    """There is no booking with that id. Answered as HTTP 404."""

    code = "booking_not_found"


class PriceDecisionNotApplicableError(AppError):
    """The booking isn't waiting for a price decision. Answered as HTTP 409."""

    code = "price_decision_not_applicable"


class PriceMismatchError(AppError):
    """The decision refers to a price that isn't the one offered. Answered as HTTP 422."""

    code = "price_mismatch"
