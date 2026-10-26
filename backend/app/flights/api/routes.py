"""HTTP endpoints of the flights module."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.flights.api.dependencies import get_flight_search_service, get_place_search_service
from app.flights.api.schemas import SearchResponse
from app.flights.domain.constants import (
    PLACE_QUERY_MAX_LENGTH,
    PLACE_QUERY_MIN_LENGTH,
    PLACE_SUGGESTIONS_DEFAULT,
    PLACE_SUGGESTIONS_MAX,
)
from app.flights.domain.dtos import PlaceSuggestion, SearchCriteria
from app.flights.services.flight_search import FlightSearchService
from app.flights.services.places import PlaceSearchService

router = APIRouter(prefix="/api/v1/flights", tags=["flights"])


# FastAPI publishes the docstring as the endpoint's description in Swagger, so it is written for
# API consumers instead of following the Google sections.
@router.post("/search", response_model=SearchResponse)
async def search_flights(
    criteria: SearchCriteria,
    service: Annotated[FlightSearchService, Depends(get_flight_search_service)],
) -> SearchResponse:
    """Searches flights.

    Results come grouped by flight: each flight has its fares (Light, Flex...), sorted by sale
    price. Flights are sorted by their cheapest fare. Fares expire at their `expires_at` (about
    30 minutes after the search). Errors use the format `{"error": {"code", "message"}}`:
    `validation_error` and `invalid_search` (422), `provider_error` (502) and
    `provider_timeout` (504).
    """
    return SearchResponse.from_domain(await service.search(criteria))


@router.get("/places", response_model=list[PlaceSuggestion])
async def suggest_places(
    service: Annotated[PlaceSearchService, Depends(get_place_search_service)],
    q: Annotated[
        str,
        Query(
            min_length=PLACE_QUERY_MIN_LENGTH,
            max_length=PLACE_QUERY_MAX_LENGTH,
            description="What the traveler typed: a code, a city or an airport name. Accents and case are ignored.",
        ),
    ],
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=PLACE_SUGGESTIONS_MAX,
            description="Maximum number of suggestions.",
        ),
    ] = PLACE_SUGGESTIONS_DEFAULT,
) -> list[PlaceSuggestion]:
    """Suggests cities and airports for the origin and destination fields.

    Cities with several airports (e.g. `NYC`: JFK and LGA) come first and can be used as origin
    or destination. Then airports, best match first: exact code, then name or city, then similar
    spellings. Names come from the airport database in English.
    """
    return await service.suggest(q, limit)
