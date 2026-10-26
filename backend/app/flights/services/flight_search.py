"""Flight search use case."""

from app.core.pricing.base import PricingPolicy
from app.flights.domain.dtos import FlightSearchResult, Offer, OfferAmounts, SearchCriteria
from app.flights.providers.base import FlightProvider
from app.flights.services.grouping import group_offers


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
        priced = [self._apply_pricing(o) for o in result.offers]
        return FlightSearchResult(
            provider=result.provider,
            search_id=result.search_id,
            passengers=result.passengers,
            flights=group_offers(priced),
        )

    def _apply_pricing(self, offer: Offer) -> Offer:
        """Sets the sale price of an offer.

        Taxes stay as charged by the provider; the markup goes into the base fare.

        Args:
            offer: Offer with its cost.

        Returns:
            A copy of the offer with `price` and `markup` set.
        """
        markup = self._pricing.markup(offer.cost.total, key=f"{offer.provider}:{offer.id}")
        price = OfferAmounts(
            total=offer.cost.total + markup,
            base=offer.cost.base + markup if offer.cost.base is not None else None,
            taxes=offer.cost.taxes,
        )
        return offer.model_copy(update={"price": price, "markup": markup})
