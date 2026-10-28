"""Port every flight provider adapter implements."""

import uuid
from typing import Protocol

from app.flights.domain.dtos.offers import SearchResult
from app.flights.domain.dtos.orders import BookableOffer, Order, OrderRequest
from app.flights.domain.dtos.search import SearchCriteria


class FlightProvider(Protocol):
    """A source of flights, such as Duffel.

    Adapters receive and return platform DTOs only, with prices always being the provider's
    cost, and translate their failures into `app.flights.domain.errors`. Any class with this
    shape satisfies the port; no inheritance is needed.
    """

    # Identifier of the provider, e.g. `"duffel"`.
    name: str

    async def search(self, criteria: SearchCriteria) -> SearchResult:
        """Searches flights.

        Args:
            criteria: What the traveler is looking for. If `criteria.airlines` is set, only
                offers sold by those airlines are returned.

        Returns:
            The offers found, with their cost and no sale price.

        Raises:
            InvalidSearchError: The provider rejected the criteria.
            ProviderTimeoutError: The provider didn't answer in time.
            ProviderError: The provider failed for any other reason.
        """
        ...

    async def get_offer(self, offer_id: str) -> BookableOffer:
        """Reads an offer again, with its current price, just before booking it.

        Args:
            offer_id: Provider id of the offer.

        Returns:
            The offer with its current cost, and the provider ids of its passengers.

        Raises:
            OfferExpiredError: The offer expired.
            OfferUnavailableError: The offer doesn't exist anymore.
            ProviderTimeoutError: The provider didn't answer in time.
            ProviderError: The provider failed for any other reason.
        """
        ...

    async def find_order(self, offer_id: str, booking_id: uuid.UUID) -> Order | None:
        """Finds the order a booking already created for an offer, if any.

        Used to reconcile after a crash or a timeout, so a retry never books twice.

        Args:
            offer_id: Provider id of the offer.
            booking_id: Id of the platform's booking saved in the order.

        Returns:
            The order, or `None` if that booking didn't create one.

        Raises:
            ProviderTimeoutError: The provider didn't answer in time.
            ProviderError: The provider failed.
        """
        ...

    async def create_order(self, request: OrderRequest) -> Order:
        """Books an offer and pays it.

        Args:
            request: Offer, passenger, payment and booking id.

        Returns:
            The confirmed order.

        Raises:
            OfferAlreadyBookedError: The search of the offer was already booked (maybe by this
                booking: reconcile with `find_order`).
            OfferExpiredError: The offer expired.
            OfferUnavailableError: The offer doesn't exist anymore.
            OrderRejectedError: The provider rejected the order for good.
            ProviderTimeoutError: The provider didn't answer in time; the order may exist.
            ProviderError: The provider failed for any other reason; the order may exist.
        """
        ...
