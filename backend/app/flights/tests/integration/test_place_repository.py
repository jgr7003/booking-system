"""PlaceRepository against the test PostgreSQL and Redis (real infrastructure, isolated data)."""

import pytest
from sqlalchemy import delete

from app.core.cache import JsonCache, create_redis
from app.core.text import normalize_search_text
from app.flights.domain.constants.places import PLACES_CACHE_PREFIX
from app.flights.domain.models.airports import Airport, City
from app.flights.repositories.places import PlaceRepository

pytestmark = pytest.mark.anyio


def city(code, name, country):
    return City(iata_code=code, name=name, country_code=country, search_text=normalize_search_text(f"{code} {name}"))


def airport(code, name, city_name, country, *, city_code=None, importance=4, keywords=""):
    return Airport(
        iata_code=code,
        name=name,
        city_name=city_name,
        city_code=city_code,
        country_code=country,
        time_zone="UTC",
        latitude=0.0,
        longitude=0.0,
        importance=importance,
        search_text=normalize_search_text(f"{code} {city_name} {name} {keywords}"),
    )


@pytest.fixture
async def places(db_session):
    db_session.add_all([city("NYC", "New York", "US"), city("BUE", "Buenos Aires", "AR")])
    await db_session.flush()
    db_session.add_all(
        [
            airport("JFK", "John F Kennedy International Airport", "New York", "US", city_code="NYC"),
            airport("LGA", "LaGuardia Airport", "New York", "US", city_code="NYC"),
            airport("NYS", "Skyports Seaplane Base", "New York", "US", importance=1),
            airport("LHR", "London Heathrow Airport", "London", "GB", keywords="LON, Londres"),
            airport("ZRH", "Zürich Airport", "Zürich", "CH"),
            airport("AEP", "Jorge Newbery Airpark", "Buenos Aires", "AR", city_code="BUE"),
            airport("EZE", "Ministro Pistarini International Airport", "Ezeiza", "AR", city_code="BUE"),
            airport("PBQ", "Pimenta Bueno Airport", "Pimenta Bueno", "BR", importance=0),
        ]
    )
    await db_session.commit()
    return db_session


@pytest.fixture
def repository(places, redis_client):
    return PlaceRepository(places, JsonCache(redis_client))


def codes(suggestions):
    return [s.code for s in suggestions]


async def test_city_first_then_its_airports_then_smaller_ones(repository):
    result = await repository.search("new y", limit=8)

    assert codes(result)[0] == "NYC"
    assert set(codes(result)[1:3]) == {"JFK", "LGA"}  # same importance: either order
    assert codes(result)[3] == "NYS"
    assert result[0].type == "city"
    assert result[0].airports == ["JFK", "LGA"]


async def test_city_airports_rank_high_even_with_another_city_name(repository):
    """EZE's city is Ezeiza, but it belongs to Buenos Aires (BUE)."""
    result = await repository.search("bue", limit=8)

    assert codes(result)[:4] == ["BUE", "AEP", "EZE", "PBQ"]


async def test_exact_code_first(repository):
    assert codes(await repository.search("jfk", limit=8))[0] == "JFK"


async def test_accents_and_alternative_names(repository):
    assert codes(await repository.search("zurich", limit=8)) == ["ZRH"]
    assert codes(await repository.search("londres", limit=8)) == ["LHR"]


async def test_similar_spellings(repository):
    assert "LHR" in codes(await repository.search("heatrow", limit=8))


async def test_results_are_cached(repository, places, redis_client):
    first = await repository.search("new y", limit=8)
    await places.execute(delete(Airport))
    await places.commit()

    again = await repository.search("new y", limit=8)

    assert again == first
    assert await redis_client.exists(f"{PLACES_CACHE_PREFIX}q:new y:8")


async def test_works_without_redis(places):
    unreachable = create_redis("redis://localhost:1/0", timeout_s=0.2)
    repository = PlaceRepository(places, JsonCache(unreachable))

    result = await repository.search("jfk", limit=8)

    assert codes(result) == ["JFK"]
    await unreachable.aclose()
