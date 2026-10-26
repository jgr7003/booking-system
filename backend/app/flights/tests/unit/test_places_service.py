import pytest

from app.flights.services.places import PlaceSearchService

pytestmark = pytest.mark.anyio


class FakeRepository:
    def __init__(self):
        self.calls = []

    async def search(self, query, limit):
        self.calls.append((query, limit))
        return []


async def test_query_is_normalized_so_variants_share_results():
    repository = FakeRepository()
    service = PlaceSearchService(repository)

    for typed in ["Zürich", "  ZURICH ", "zurich"]:
        await service.suggest(typed, 5)

    assert repository.calls == [("zurich", 5)] * 3


async def test_too_short_after_normalizing_returns_nothing():
    repository = FakeRepository()

    assert await PlaceSearchService(repository).suggest("  é ", 5) == []
    assert repository.calls == []
