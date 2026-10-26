"""Shared test setup.

Safety nets: no test can reach a real provider, and tests only touch the test database and the
test Redis database, never the development ones.
"""

import os

import httpx2
import pytest

from app.core.cache import create_redis
from app.core.config import get_settings
from app.core.db import Base, create_engine, create_session_factory
from app.core.http import get_http_client
from app.flights.core.config import get_duffel_settings
from app.main import app

# Isolated infrastructure for integration tests (see docker-compose.yml).
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
TEST_REDIS_URL = os.environ.get("TEST_REDIS_URL")


def reject_unexpected_request(request: httpx2.Request) -> httpx2.Response:
    """`MockTransport` handler that fails on any request.

    Args:
        request: The outgoing request.

    Raises:
        AssertionError: Always, naming the request, so the test shows what it tried to call.
    """
    raise AssertionError(f"Unexpected outbound HTTP request in tests: {request.method} {request.url}")


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch):
    """Sets fake credentials, an unroutable provider URL and the test databases.

    Args:
        monkeypatch: Pytest fixture used to override environment variables.

    Yields:
        Control to the test; settings caches are cleared before and after it.
    """
    monkeypatch.setenv("DUFFEL_API_URL", "http://duffel.invalid")
    monkeypatch.setenv("DUFFEL_API_TOKEN", "duffel_test_fake_token")
    monkeypatch.setenv("PRICING_SECRET", "test-secret")
    if TEST_DATABASE_URL:
        monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    if TEST_REDIS_URL:
        monkeypatch.setenv("REDIS_URL", TEST_REDIS_URL)
    get_settings.cache_clear()
    get_duffel_settings.cache_clear()
    yield
    get_settings.cache_clear()
    get_duffel_settings.cache_clear()


@pytest.fixture(autouse=True)
def block_outbound_http():
    """Makes the app's shared HTTP client fail on any request a test didn't mock.

    Yields:
        Control to the test; dependency overrides are cleared after it.
    """
    blocked = httpx2.AsyncClient(transport=httpx2.MockTransport(reject_unexpected_request))
    app.dependency_overrides[get_http_client] = lambda: blocked
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def anyio_backend():
    """Runs `@pytest.mark.anyio` tests on asyncio."""
    return "asyncio"


@pytest.fixture
async def db_session():
    """Session on the test database, with every table recreated empty.

    Yields:
        An `AsyncSession`; the test commits what it needs.
    """
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not set")
    engine = create_engine(TEST_DATABASE_URL)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)
    async with create_session_factory(engine)() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def redis_client():
    """Client of the test Redis database, emptied before the test.

    Yields:
        A `redis.asyncio.Redis` client.
    """
    if not TEST_REDIS_URL:
        pytest.skip("TEST_REDIS_URL is not set")
    redis = create_redis(TEST_REDIS_URL, timeout_s=1)
    await redis.flushdb()
    yield redis
    await redis.aclose()
