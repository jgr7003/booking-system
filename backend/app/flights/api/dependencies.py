"""Wiring: the only place that decides which flight provider the platform uses."""

from typing import Annotated

import httpx2
from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import JsonCache, get_redis
from app.core.db import get_db_session
from app.core.http import get_http_client
from app.core.pricing.base import PricingPolicy
from app.core.pricing.dependencies import get_pricing_policy
from app.flights.core.config import DuffelSettings, get_duffel_settings
from app.flights.providers.base import FlightProvider
from app.flights.providers.duffel.client import DuffelClient
from app.flights.providers.duffel.provider import DuffelFlightProvider
from app.flights.repositories.places import PlaceRepository
from app.flights.services.flight_search import FlightSearchService
from app.flights.services.places import PlaceSearchService


def get_flight_provider(
    http: Annotated[httpx2.AsyncClient, Depends(get_http_client)],
    settings: Annotated[DuffelSettings, Depends(get_duffel_settings)],
) -> FlightProvider:
    """FastAPI dependency that provides the flight provider.

    Tests override it with a fake provider.

    Args:
        http: Shared HTTP client.
        settings: Duffel connection settings.

    Returns:
        The Duffel adapter.
    """
    return DuffelFlightProvider(DuffelClient(http, settings))


def get_flight_search_service(
    provider: Annotated[FlightProvider, Depends(get_flight_provider)],
    pricing: Annotated[PricingPolicy, Depends(get_pricing_policy)],
) -> FlightSearchService:
    """FastAPI dependency that provides the flight search use case.

    Args:
        provider: Source of flights.
        pricing: The platform's pricing policy.

    Returns:
        The search service.
    """
    return FlightSearchService(provider, pricing)


def get_place_search_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis)],
) -> PlaceSearchService:
    """FastAPI dependency that provides the airport and city autocomplete use case.

    Args:
        session: Database session for this request.
        redis: Shared Redis client, used as cache.

    Returns:
        The place search service.
    """
    return PlaceSearchService(PlaceRepository(session, JsonCache(redis)))
