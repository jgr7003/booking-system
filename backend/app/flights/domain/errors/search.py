"""Errors of the flight search."""

from app.core.errors import AppError


class InvalidSearchError(AppError):
    """The provider rejected the search criteria, e.g. an unknown airport. Answered as HTTP 422."""

    code = "invalid_search"
