"""Loads or refreshes airports and multi-airport cities.

Sources:
- `airportsdata` (MIT): airports with IATA code, time zone, coordinates, and the IATA
  multi-airport cities (NYC, LON...).
- OurAirports (public domain): airport type and scheduled service, used to rank the
  autocomplete, plus alternative names (e.g. `Londres`). If it can't be downloaded, the load
  still runs without them.

Idempotent: it upserts every row, removes the ones the source no longer has and clears the
autocomplete cache. Run it with `make seed-airports`.
"""

import asyncio
import csv
import io
import logging

import airportsdata
import httpx2
from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import JsonCache, create_redis
from app.core.config import get_settings
from app.core.db import create_engine, create_session_factory
from app.core.text import normalize_search_text
from app.flights.domain.constants import PLACES_CACHE_PREFIX
from app.flights.domain.models import Airport, City

logger = logging.getLogger(__name__)

# Rows per INSERT statement.
BATCH_SIZE = 1000

# OurAirports export (public domain), refreshed nightly.
OURAIRPORTS_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"

# Importance of an airport with scheduled flights, by OurAirports type; any other type gets 1.
SCHEDULED_IMPORTANCE = {"large_airport": 4, "medium_airport": 3, "small_airport": 2}


def download_ourairports() -> dict[str, dict]:
    """Downloads OurAirports and indexes it by IATA code.

    Returns:
        OurAirports rows by IATA code; empty if the download fails.
    """
    try:
        response = httpx2.get(OURAIRPORTS_URL, timeout=60, follow_redirects=True)
        response.raise_for_status()
    except httpx2.HTTPError as exc:
        logger.warning("OurAirports unavailable (%s): loading without importance or alternative names", exc)
        return {}
    return {row["iata_code"]: row for row in csv.DictReader(io.StringIO(response.text)) if row["iata_code"]}


def importance(extra: dict | None) -> int:
    """Relevance of an airport for the autocomplete, from its OurAirports row.

    Args:
        extra: OurAirports row, or `None` if the airport isn't there.

    Returns:
        4 (large) to 1 (other) for airports with scheduled flights; 0 otherwise.
    """
    if not extra or extra["scheduled_service"] != "yes":
        return 0
    return SCHEDULED_IMPORTANCE.get(extra["type"], 1)


def city_rows() -> list[dict]:
    """Multi-airport cities (IATA MACs) as table rows."""
    return [
        {
            "iata_code": code,
            "name": mac["name"],
            "country_code": mac["country"],
            "search_text": normalize_search_text(f"{code} {mac['name']}"),
        }
        for code, mac in airportsdata.load_iata_macs().items()
    ]


def airport_rows(ourairports: dict[str, dict]) -> list[dict]:
    """Airports with an IATA code as table rows.

    Args:
        ourairports: OurAirports rows by IATA code, for importance and alternative names.

    Returns:
        One row per airport, linked to its multi-airport city if any.
    """
    city_of = {
        airport_code: city_code
        for city_code, mac in airportsdata.load_iata_macs().items()
        for airport_code in mac["airports"]
    }
    rows = []
    for code, airport in airportsdata.load("IATA").items():
        extra = ourairports.get(code)
        keywords = extra["keywords"] if extra else ""
        rows.append(
            {
                "iata_code": code,
                "icao_code": airport["icao"] or None,
                "name": airport["name"],
                "city_name": airport["city"] or None,
                "city_code": city_of.get(code),
                "country_code": airport["country"],
                "time_zone": airport["tz"],
                "latitude": airport["lat"],
                "longitude": airport["lon"],
                "importance": importance(extra),
                "search_text": normalize_search_text(f"{code} {airport['city']} {airport['name']} {keywords}"),
            }
        )
    return rows


async def upsert(session: AsyncSession, model: type[City] | type[Airport], rows: list[dict]) -> None:
    """Inserts `rows`, updating the ones that already exist.

    Args:
        session: Database session; the caller commits.
        model: `City` or `Airport`.
        rows: Rows keyed by column name, with `iata_code` as primary key.
    """
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start : start + BATCH_SIZE]
        statement = insert(model).values(batch)
        updates = {column: statement.excluded[column] for column in batch[0] if column != "iata_code"}
        await session.execute(statement.on_conflict_do_update(index_elements=["iata_code"], set_=updates))


async def delete_missing(session: AsyncSession, model: type[City] | type[Airport], rows: list[dict]) -> None:
    """Deletes the rows of `model` the source no longer has.

    Args:
        session: Database session; the caller commits.
        model: `City` or `Airport`.
        rows: Every row the source has.
    """
    await session.execute(delete(model).where(model.iata_code.not_in([r["iata_code"] for r in rows])))


async def seed() -> tuple[int, int]:
    """Loads cities and airports, then clears the autocomplete cache.

    Returns:
        How many cities and airports the database has after the load.
    """
    settings = get_settings()
    cities, airports = city_rows(), airport_rows(download_ourairports())
    engine = create_engine(settings.database_url)
    redis = create_redis(settings.redis_url, settings.cache_timeout_s)
    try:
        async with create_session_factory(engine)() as session, session.begin():
            # Airports reference cities: upsert cities first and delete them last.
            await upsert(session, City, cities)
            await upsert(session, Airport, airports)
            await delete_missing(session, Airport, airports)
            await delete_missing(session, City, cities)
        cleared = await JsonCache(redis).delete_prefix(PLACES_CACHE_PREFIX)
        logger.info("Cleared %s cached autocomplete entries", cleared)
    finally:
        await redis.aclose()
        await engine.dispose()
    return len(cities), len(airports)


def main() -> None:
    """Command-line entry point."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    cities, airports = asyncio.run(seed())
    logger.info("Loaded %s multi-airport cities and %s airports", cities, airports)


if __name__ == "__main__":
    main()
