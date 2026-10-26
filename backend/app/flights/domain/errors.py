"""Errors of the flights domain. Adapters translate provider failures into these."""

from app.core.errors import AppError


class ProviderError(AppError):
    """The provider failed: server error, authentication, network...

    Answered as HTTP 502. The message never includes provider internals or credentials.
    """

    code = "provider_error"


class ProviderTimeoutError(ProviderError):
    """The provider didn't answer in time. Answered as HTTP 504."""

    code = "provider_timeout"


class InvalidSearchError(AppError):
    """The provider rejected the search criteria, e.g. an unknown airport. Answered as HTTP 422."""

    code = "invalid_search"
