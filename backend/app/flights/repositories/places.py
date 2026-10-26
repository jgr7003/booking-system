"""Airport and city lookups in PostgreSQL, behind a Redis cache (cache-aside)."""

from sqlalchemy import case, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import JsonCache
from app.flights.domain.constants import (
    PLACE_MAX_CITIES,
    PLACE_WORD_SIMILARITY_THRESHOLD,
    PLACES_CACHE_PREFIX,
    PLACES_CACHE_TTL_S,
)
from app.flights.domain.dtos import PlaceSuggestion, PlaceType
from app.flights.domain.models import Airport, City


class PlaceRepository:
    """Finds cities and airports by code, city or name."""

    def __init__(self, session: AsyncSession, cache: JsonCache) -> None:
        """Initializes the repository.

        Args:
            session: Database session.
            cache: Cache for search results.
        """
        self._session = session
        self._cache = cache

    async def search(self, query: str, limit: int) -> list[PlaceSuggestion]:
        """Finds the places that match `query`, reading the cache first.

        Args:
            query: Normalized text (no accents, lower case), e.g. `"new y"`.
            limit: Maximum number of suggestions.

        Returns:
            Matching cities first, then airports, best match first.
        """
        key = f"{PLACES_CACHE_PREFIX}q:{query}:{limit}"
        cached = await self._cache.get(key)
        if cached is not None:
            return [PlaceSuggestion.model_validate(item) for item in cached]

        cities = await self._search_cities(query, min(limit, PLACE_MAX_CITIES))
        airports = await self._search_airports(query, limit - len(cities), [c.code for c in cities])
        suggestions = cities + airports

        await self._cache.set(key, [s.model_dump(mode="json") for s in suggestions], ttl_s=PLACES_CACHE_TTL_S)
        return suggestions

    async def _search_cities(self, query: str, limit: int) -> list[PlaceSuggestion]:
        """Cities whose code is `query` or whose name starts with it."""
        rank = case((City.iata_code == query.upper(), 0), else_=1)
        rows = (
            await self._session.execute(
                select(City)
                .where(or_(City.iata_code == query.upper(), City.search_text.like(f"% {query}%")))
                .order_by(rank, City.name)
                .limit(limit)
            )
        ).scalars()
        cities = list(rows)
        if not cities:
            return []

        airports = await self._session.execute(
            select(Airport.city_code, Airport.iata_code)
            .where(Airport.city_code.in_([c.iata_code for c in cities]))
            .order_by(Airport.iata_code)
        )
        by_city: dict[str, list[str]] = {}
        for city_code, iata_code in airports:
            by_city.setdefault(city_code, []).append(iata_code)

        return [
            PlaceSuggestion(
                type=PlaceType.CITY,
                code=c.iata_code,
                name=c.name,
                country_code=c.country_code,
                airports=by_city.get(c.iata_code, []),
            )
            for c in cities
        ]

    async def _search_airports(self, query: str, limit: int, city_codes: list[str]) -> list[PlaceSuggestion]:
        """Airports ranked by relevance.

        Order: exact code; airports of a matching multi-airport city; airports whose city starts
        with the text; a word starting with it (name or alternative name); the text anywhere;
        similar spellings (trigrams). Within each group, busier airports go first (`importance`).

        Args:
            query: Normalized text.
            limit: Maximum number of airports.
            city_codes: Codes of the multi-airport cities that matched, whose airports rank high
                even if their own city name differs (EZE belongs to Buenos Aires).

        Returns:
            Matching airports, best match first.
        """
        if limit <= 0:
            return []
        # Only for this transaction; the `%>` operator below uses it.
        await self._session.execute(
            text(f"SET LOCAL pg_trgm.word_similarity_threshold = {PLACE_WORD_SIMILARITY_THRESHOLD}")
        )
        code = query.upper()
        # search_text is "<code> <city> <name> <alternative names>": the city starts after the code.
        city_start = func.lower(Airport.iata_code).concat(f" {query}%")
        rank = case(
            (Airport.iata_code == code, 0),
            (Airport.city_code.in_(city_codes), 1),
            (Airport.search_text.like(city_start), 2),
            (Airport.search_text.like(f"% {query}%"), 3),
            (Airport.search_text.like(f"%{query}%"), 4),
            else_=5,
        )
        rows = await self._session.execute(
            select(Airport)
            .where(
                or_(
                    Airport.iata_code == code,
                    Airport.city_code.in_(city_codes),
                    Airport.search_text.like(f"%{query}%"),
                    # Word similarity: compares against the best-matching part of the text, so a
                    # typo like "heatrow" still finds "heathrow" inside a long search_text.
                    Airport.search_text.op("%>")(query),
                )
            )
            .order_by(
                rank,
                Airport.importance.desc(),
                func.word_similarity(query, Airport.search_text).desc(),
                Airport.name,
            )
            .limit(limit)
        )
        return [
            PlaceSuggestion(
                type=PlaceType.AIRPORT,
                code=a.iata_code,
                name=a.name,
                city=a.city_name,
                country_code=a.country_code,
                time_zone=a.time_zone,
            )
            for a in rows.scalars()
        ]
