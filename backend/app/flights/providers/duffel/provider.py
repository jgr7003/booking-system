"""Duffel adapter for the `FlightProvider` port."""

import uuid

from app.flights.domain.dtos.offers import SearchResult
from app.flights.domain.dtos.orders import BookableOffer, Order, OrderRequest
from app.flights.domain.dtos.search import SearchCriteria
from app.flights.providers.duffel import mapper
from app.flights.providers.duffel.client import DuffelClient


class DuffelFlightProvider:
    """Implements `FlightProvider` on top of the Duffel API."""

    # Identifier of the provider: always `"duffel"`.
    name = mapper.PROVIDER

    def __init__(self, client: DuffelClient) -> None:
        """Initializes the adapter.

        Args:
            client: HTTP client for the Duffel API.
        """
        self._client = client

    async def search(self, criteria: SearchCriteria) -> SearchResult:
        """Searches flights in Duffel.

        Duffel can't restrict a search to specific airlines, so when `criteria.airlines` is set
        the adapter filters the answer, keeping the offers whose `owner` is in the list.

        Args:
            criteria: What the traveler is looking for.

        Returns:
            The offers found, with their cost and no sale price.

        Raises:
            InvalidSearchError: Duffel rejected the criteria.
            ProviderTimeoutError: Duffel didn't answer in time.
            ProviderError: Duffel failed for any other reason.
        """
        data = await self._client.create_offer_request(mapper.to_offer_request(criteria))
        result = mapper.to_search_result(data)
        if criteria.airlines:
            airlines = set(criteria.airlines)
            result = result.model_copy(update={"offers": [o for o in result.offers if o.owner.code in airlines]})
        return result

    async def get_offer(self, offer_id: str) -> BookableOffer:
        """Reads an offer from Duffel; see `FlightProvider.get_offer`."""
        return mapper.to_bookable_offer(await self._client.get_offer(offer_id))

    async def find_order(self, offer_id: str, booking_id: uuid.UUID) -> Order | None:
        """Finds our order for an offer through its metadata; see `FlightProvider.find_order`."""
        orders = [mapper.to_order(o) for o in await self._client.list_orders(offer_id)]
        return next((o for o in orders if o.booking_id == booking_id), None)

    async def create_order(self, request: OrderRequest) -> Order:
        """Creates an instant order paid from the Duffel balance; see `FlightProvider.create_order`."""
        return mapper.to_order(await self._client.create_order(mapper.to_order_payload(request)))
