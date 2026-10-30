"""Errors of the organizations module."""

from app.core.errors import AppError


class UnknownInstallationError(AppError):
    """The request's host isn't the platform's nor an active organization's. Answered as HTTP 404."""

    code = "not_found"


class OrganizationAlreadyExistsError(AppError):
    """The slug or one of the hostnames is already taken."""

    code = "organization_already_exists"


class OrganizationNotFoundError(AppError):
    """There is no organization with that slug."""

    code = "organization_not_found"
