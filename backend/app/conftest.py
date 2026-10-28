"""Shared test setup.

Safety nets: no test can reach a real provider, and tests only touch the test database, the test
Redis database and the test RabbitMQ vhost, never the development ones.
"""

import os

import aio_pika
import httpx2
import pytest
from sqlalchemy import text

from app.core.cache import create_redis
from app.core.config import get_settings
from app.core.db import Base, create_engine, create_session_factory
from app.core.http import get_http_client
from app.flights.core.config import get_duffel_settings
from app.notifications.core.config import get_email_settings
from app.main import app

# Isolated infrastructure for integration tests (see docker-compose.yml).
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
TEST_REDIS_URL = os.environ.get("TEST_REDIS_URL")
TEST_RABBITMQ_URL = os.environ.get("TEST_RABBITMQ_URL")


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
    # No test sends real email unless it builds its own sender (see the Mailpit tests).
    monkeypatch.setenv("EMAIL_BACKEND", "console")
    if TEST_DATABASE_URL:
        monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    if TEST_REDIS_URL:
        monkeypatch.setenv("REDIS_URL", TEST_REDIS_URL)
    if TEST_RABBITMQ_URL:
        monkeypatch.setenv("RABBITMQ_URL", TEST_RABBITMQ_URL)
    get_settings.cache_clear()
    get_duffel_settings.cache_clear()
    get_email_settings.cache_clear()
    yield
    get_settings.cache_clear()
    get_duffel_settings.cache_clear()
    get_email_settings.cache_clear()


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
async def db_engine():
    """Engine of the test database, with every table recreated empty.

    Yields:
        An `AsyncEngine`, disposed after the test.
    """
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not set")
    engine = create_engine(TEST_DATABASE_URL)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        # Each module keeps its tables in its own schema (00-global.md §4.1).
        for schema in sorted({table.schema for table in Base.metadata.tables.values() if table.schema}):
            await connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
        await connection.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
def db_session_factory(db_engine):
    """Factory of sessions on the test database, for code that opens its own transactions.

    Args:
        db_engine: Engine of the test database.

    Returns:
        An `async_sessionmaker`.
    """
    return create_session_factory(db_engine)


@pytest.fixture
async def db_session(db_session_factory):
    """Session on the test database, with every table recreated empty.

    Args:
        db_session_factory: Factory of sessions on the test database.

    Yields:
        An `AsyncSession`; the test commits what it needs.
    """
    async with db_session_factory() as session:
        yield session


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


@pytest.fixture
async def rabbitmq_connection():
    """Connection to the test vhost of RabbitMQ.

    Tests declare their own exchanges and queues with unique names and delete them.

    Yields:
        A robust connection, closed after the test.
    """
    if not TEST_RABBITMQ_URL:
        pytest.skip("TEST_RABBITMQ_URL is not set")
    connection = await aio_pika.connect_robust(TEST_RABBITMQ_URL)
    yield connection
    await connection.close()
