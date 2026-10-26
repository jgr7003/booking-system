"""HTTP status codes of the flights domain errors."""

from fastapi import FastAPI

from app.core.errors import add_error_handlers
from app.flights.domain.errors import InvalidSearchError, ProviderError, ProviderTimeoutError


def register_flights_error_handlers(app: FastAPI) -> None:
    """Registers how flights errors are answered over HTTP.

    Args:
        app: The FastAPI application.
    """
    add_error_handlers(
        app,
        {
            InvalidSearchError: 422,
            ProviderError: 502,
            ProviderTimeoutError: 504,
        },
    )
