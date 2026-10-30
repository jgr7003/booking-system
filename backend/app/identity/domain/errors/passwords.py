"""Errors of email-and-password sign in and of the email links."""

from app.core.errors import AppError


class PasswordLoginDisabledError(AppError):
    """The installation doesn't accept passwords (or sign ups). Answered as HTTP 404, like any unknown route."""

    code = "not_found"


class InvalidLinkError(AppError):
    """The link is unknown, expired or already used. Answered as HTTP 410."""

    code = "invalid_link"


class TooManyAttemptsError(AppError):
    """Too many attempts in a short time. Answered as HTTP 429."""

    code = "too_many_attempts"


class LoginFailedError(AppError):
    """Any failed sign in. Answered as HTTP 401 with the same code and message whatever the reason.

    Wrong password, unknown account, blocked account or address, unverified email, no password:
    from outside they all look alike, so an attacker learns nothing. The reason goes to the logs.
    """

    code = "login_failed"
