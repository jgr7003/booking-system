"""Errors of the list of connected devices."""

from app.core.errors import AppError


class DeviceSessionNotFoundError(AppError):
    """The user has no open session with that id. Answered as HTTP 404."""

    code = "session_not_found"
