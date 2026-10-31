"""Errors about users."""

from app.core.errors import AppError


class UserAlreadyExistsError(AppError):
    """The installation already has a user with that email. Answered as HTTP 409."""

    code = "user_already_exists"


class UnknownOrganizationError(AppError):
    """A user was to be created in an organization that doesn't exist."""

    code = "organization_not_found"
