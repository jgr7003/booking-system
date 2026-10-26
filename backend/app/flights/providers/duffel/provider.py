"""Duffel adapter for the `FlightProvider` port."""

from app.flights.domain.dtos import SearchCriteria, SearchResult
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
