"""HTTP status codes of the flights domain errors."""

from fastapi import FastAPI

from app.core.errors import add_error_handlers
from app.flights.domain.errors.bookings import (
    BookingNotFoundError,
    IdempotencyKeyRequiredError,
    IdempotencyKeyReusedError,
    PriceDecisionNotApplicableError,
    PriceMismatchError,
)
from app.flights.domain.errors.provider import ProviderError, ProviderTimeoutError
from app.flights.domain.errors.search import InvalidSearchError


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
            IdempotencyKeyRequiredError: 400,
            IdempotencyKeyReusedError: 422,
            BookingNotFoundError: 404,
            PriceDecisionNotApplicableError: 409,
            PriceMismatchError: 422,
        },
    )
