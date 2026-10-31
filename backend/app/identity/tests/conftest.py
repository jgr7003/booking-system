"""Fixtures shared by the identity tests."""

from contextlib import asynccontextmanager

import httpx2
import pytest

from app.core.db import get_db_session, get_session_factory
from app.core.http import get_http_client
from app.identity.api.dependencies import get_email_sender, get_identity_redis
from app.identity.testing import RecordingEmailSender
from app.identity.tests.support import FakeIdp
from app.main import app
from app.organizations.public import (
    NewOrganization,
    OrganizationLookup,
    OrganizationSettings,
    create_organization,
    get_organization_lookup,
)


@pytest.fixture
def sender() -> RecordingEmailSender:
    """Email sender that keeps the emails in memory."""
    return RecordingEmailSender()


@pytest.fixture
def api(db_session_factory, redis_client, sender):
    """Opens HTTP clients of the app wired to the test database, Redis and the recording sender.

    Args:
        db_session_factory: Factory of sessions on the test database.
        redis_client: Client of the test Redis.
        sender: Recording email sender.

    Returns:
        A function `api(base_url="http://test")` usable as an async context manager.
    """

    async def session():
        """One session per request, as in production."""
        async with db_session_factory() as s:
            yield s

    app.dependency_overrides[get_db_session] = session
    app.dependency_overrides[get_session_factory] = lambda: db_session_factory
    app.dependency_overrides[get_identity_redis] = lambda: redis_client
    app.dependency_overrides[get_email_sender] = lambda: sender
    app.dependency_overrides[get_organization_lookup] = lambda: OrganizationLookup(lambda: db_session_factory)

    @asynccontextmanager
    async def client(base_url: str = "http://test"):
        async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), base_url=base_url) as http:
            yield http

    return client


@pytest.fixture
def add_organization(db_session_factory):
    """Creates organizations in the test database.

    Args:
        db_session_factory: Factory of sessions on the test database.

    Returns:
        A function `await add_organization(slug, host, **settings)` that returns the organization.
    """

    async def add(slug: str = "acme", host: str = "acme.localhost", **settings):
        async with db_session_factory() as session, session.begin():
            return await create_organization(
                session,
                NewOrganization(
                    slug=slug, name=slug.capitalize(), hostnames=[host], settings=OrganizationSettings(**settings)
                ),
            )

    return add


@pytest.fixture
def idp() -> FakeIdp:
    """The fake OIDC provider, reachable through the app's HTTP client."""
    provider = FakeIdp()
    client = httpx2.AsyncClient(transport=httpx2.MockTransport(provider.handler))
    app.dependency_overrides[get_http_client] = lambda: client
    return provider
