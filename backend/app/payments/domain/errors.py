"""Errors of the payments module."""

from app.core.errors import AppError


class PaymentDeclinedError(AppError):
    """The gateway declined the card. Retrying with the same card won't help."""

    code = "payment_declined"


class PaymentError(AppError):
    """The operation isn't valid for the authorization: unknown id, capturing a voided charge, or
    an idempotency key reused for another amount."""

    code = "payment_error"
