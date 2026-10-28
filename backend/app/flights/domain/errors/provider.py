"""Errors of the flight provider. Adapters translate provider failures into these."""

from app.core.errors import AppError


class ProviderError(AppError):
    """The provider failed: server error, authentication, network...

    Answered as HTTP 502. The message never includes provider internals or credentials.
    """

    code = "provider_error"


class ProviderTimeoutError(ProviderError):
    """The provider didn't answer in time. Answered as HTTP 504."""

    code = "provider_timeout"


class OfferExpiredError(AppError):
    """The offer expired; a new search is needed."""

    code = "offer_expired"


class OfferUnavailableError(AppError):
    """The offer doesn't exist anymore or can't be booked, e.g. its search was already booked."""

    code = "offer_unavailable"


class OfferAlreadyBookedError(OfferUnavailableError):
    """Another order was already created from the same search. It may be ours: reconcile first."""

    code = "offer_already_booked"


class OrderRejectedError(AppError):
    """The provider rejected the order for good, e.g. invalid passenger data."""

    code = "provider_rejected"
