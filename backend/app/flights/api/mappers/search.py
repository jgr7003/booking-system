"""From a priced, grouped search result to the public search response."""

from app.flights.api.schemas.search import FareResponse, FlightResponse, SearchResponse
from app.flights.domain.dtos.results import FlightOption, FlightSearchResult


def to_search_response(result: FlightSearchResult) -> SearchResponse:
    """Builds the public response of a search.

    Args:
        result: Result of `FlightSearchService.search`.

    Returns:
        The response to send to clients, with the earliest expiry of its fares.
    """
    fares = [fare for flight in result.flights for fare in flight.fares]
    return SearchResponse(
        provider=result.provider,
        search_id=result.search_id,
        passengers=result.passengers,
        expires_at=min((f.expires_at for f in fares), default=None),
        flights=[to_flight_response(f) for f in result.flights],
    )


def to_flight_response(flight: FlightOption) -> FlightResponse:
    """Builds the public flight.

    Fares are validated from dicts, so the cost and the markup they carry inside are dropped by
    the schema (it ignores unknown fields).

    Args:
        flight: Flight with priced fares.

    Returns:
        The flight to send to clients.
    """
    return FlightResponse(
        key=flight.key,
        provider=flight.provider,
        owner=flight.owner,
        emissions_kg=flight.emissions_kg,
        lowest_price=flight.fares[0].price.total,
        slices=flight.slices,
        fares=[FareResponse.model_validate(fare.model_dump()) for fare in flight.fares],
    )
