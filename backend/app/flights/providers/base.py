"""Port every flight provider adapter implements."""

from typing import Protocol

from app.flights.domain.dtos import SearchCriteria, SearchResult


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
