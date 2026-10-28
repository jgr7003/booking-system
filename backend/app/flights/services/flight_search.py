"""Flight search use case."""

from app.core.pricing.base import PricingPolicy
from app.flights.domain.dtos.results import FlightSearchResult
from app.flights.domain.dtos.search import SearchCriteria
from app.flights.providers.base import FlightProvider
from app.flights.services.grouping import group_offers
from app.flights.services.pricing import apply_pricing


class FlightSearchService:
    """Searches flights: asks the provider, adds the platform's markup and groups fares by flight."""

    def __init__(self, provider: FlightProvider, pricing: PricingPolicy) -> None:
        """Initializes the service.

        Args:
            provider: Source of flights.
            pricing: Rule that decides the markup on each offer.
        """
        self._provider = provider
        self._pricing = pricing

    async def search(self, criteria: SearchCriteria) -> FlightSearchResult:
        """Searches flights and prices them for sale.

        Args:
            criteria: What the traveler is looking for.

        Returns:
            The flights found, each with its fares priced for sale. Flights are sorted by their
            cheapest fare and fares by price.

        Raises:
            InvalidSearchError: The provider rejected the criteria.
            ProviderTimeoutError: The provider didn't answer in time.
            ProviderError: The provider failed for any other reason.
        """
        result = await self._provider.search(criteria)
        priced = [apply_pricing(o, self._pricing) for o in result.offers]
        return FlightSearchResult(
            provider=result.provider,
            search_id=result.search_id,
            passengers=result.passengers,
            flights=group_offers(priced),
        )
