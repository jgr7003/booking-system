"""Airport and city autocomplete use case."""

from app.core.text import normalize_search_text
from app.flights.domain.constants import PLACE_QUERY_MIN_LENGTH
from app.flights.domain.dtos import PlaceSuggestion
from app.flights.repositories.places import PlaceRepository


class PlaceSearchService:
    """Suggests cities and airports for what the traveler typed."""

    def __init__(self, repository: PlaceRepository) -> None:
        """Initializes the service.

        Args:
            repository: Place lookups.
        """
        self._repository = repository

    async def suggest(self, query: str, limit: int) -> list[PlaceSuggestion]:
        """Suggests places for a free-text query.

        Accents and case are ignored, so `"zürich"`, `"ZURICH"` and `"zurich"` give the same
        suggestions (and share the cache entry).

        Args:
            query: What the traveler typed, e.g. `"new y"` or `"jfk"`.
            limit: Maximum number of suggestions.

        Returns:
            Matching cities first, then airports; empty if the normalized query is too short.
        """
        normalized = normalize_search_text(query)
        if len(normalized) < PLACE_QUERY_MIN_LENGTH:
            return []
        return await self._repository.search(normalized, limit)
