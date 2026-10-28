"""Errors of the notifications module."""

from app.core.errors import AppError


class EmailDeliveryError(AppError):
    """The mail server didn't accept the email (down, refused, timeout). Retrying may work."""

    code = "email_delivery_failed"
