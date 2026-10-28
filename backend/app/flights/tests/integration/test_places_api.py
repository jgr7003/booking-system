import pytest
from fastapi.testclient import TestClient

from app.flights.api.dependencies import get_place_search_service
from app.flights.domain.dtos.places import PlaceSuggestion, PlaceType
from app.main import app

client = TestClient(app)
URL = "/api/v1/flights/places"

NYC = PlaceSuggestion(type=PlaceType.CITY, code="NYC", name="New York", country_code="US", airports=["JFK", "LGA"])
JFK = PlaceSuggestion(
    type=PlaceType.AIRPORT,
    code="JFK",
    name="John F Kennedy International Airport",
    city="New York",
    country_code="US",
    time_zone="America/New_York",
)


class FakePlaceService:
    def __init__(self):
        self.calls = []

    async def suggest(self, query, limit):
        self.calls.append((query, limit))
        return [NYC, JFK]


@pytest.fixture
def service():
    fake = FakePlaceService()
    app.dependency_overrides[get_place_search_service] = lambda: fake
    return fake


def test_returns_suggestions(service):
    response = client.get(URL, params={"q": "new y"})

    assert response.status_code == 200
    assert response.json() == [
        {
            "type": "city",
            "code": "NYC",
            "name": "New York",
            "city": None,
            "country_code": "US",
            "time_zone": None,
            "airports": ["JFK", "LGA"],
        },
        {
            "type": "airport",
            "code": "JFK",
            "name": "John F Kennedy International Airport",
            "city": "New York",
            "country_code": "US",
            "time_zone": "America/New_York",
            "airports": [],
        },
    ]
    assert service.calls == [("new y", 8)]


@pytest.mark.parametrize("params", [{"q": "x"}, {"q": "x" * 51}, {}, {"q": "new", "limit": 0}, {"q": "new", "limit": 21}])
def test_invalid_queries(service, params):
    response = client.get(URL, params=params)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert service.calls == []
