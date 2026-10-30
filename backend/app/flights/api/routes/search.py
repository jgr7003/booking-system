"""Endpoint of the flight search."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.flights.api.dependencies import get_flight_search_service
from app.flights.api.mappers.search import to_search_response
from app.flights.api.schemas.search import SearchResponse
from app.flights.domain.dtos.search import SearchCriteria
from app.flights.services.flight_search import FlightSearchService
from app.identity.public import installation_principal

# In an organization's installation only its signed-in users may use it; on the main platform it is public.
router = APIRouter(dependencies=[Depends(installation_principal)])


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
    return to_search_response(await service.search(criteria))
