"""Fixtures shared by the flights tests."""

import pytest

from app.flights.domain.dtos import SearchResult
from app.flights.providers.duffel import mapper
from app.flights.tests.support import load_fixture


@pytest.fixture
def duffel_search_response() -> dict:
    """Real Duffel answer for LHR → JFK, 1 adult, economy (56 offers)."""
    return load_fixture("duffel/offer_request_response.json")


@pytest.fixture
def search_result(duffel_search_response) -> SearchResult:
    """The real Duffel answer already mapped to the platform's `SearchResult`."""
    return mapper.to_search_result(duffel_search_response["data"])
