"""Organizations and installation resolution against the test PostgreSQL."""

from typing import Annotated

import anyio
import httpx2
import pytest
from fastapi import Depends, FastAPI

from app.core.errors import register_core_error_handlers
from app.main import app as main_app
from app.organizations.api.errors import register_organizations_error_handlers
from app.organizations.commands import create_organization as create_command
from app.organizations.domain.dtos import NewOrganization, OrganizationSettings
from app.organizations.domain.errors import OrganizationAlreadyExistsError
from app.organizations.public import (
    Installation,
    OrganizationLookup,
    current_installation,
    get_organization_by_slug,
    get_organization_lookup,
)
from app.organizations.services.organizations import create_organization

pytestmark = pytest.mark.anyio


async def add_acme(session_factory, **settings) -> None:
    """Creates the organization Acme at `acme.localhost`.

    Args:
        session_factory: Factory of sessions on the test database.
        **settings: Settings of the organization.
    """
    async with session_factory() as session, session.begin():
        new = NewOrganization(
            slug="acme", name="Acme", hostnames=["acme.localhost"], settings=OrganizationSettings(**settings)
        )
        await create_organization(session, new)


@pytest.fixture
def probe(db_session_factory):
    """A tiny app whose only endpoint answers with the installation of the request.

    Args:
        db_session_factory: Factory of sessions on the test database.

    Returns:
        A function that returns an HTTP client for a base URL.
    """
    app = FastAPI()
    register_core_error_handlers(app)
    register_organizations_error_handlers(app)

    @app.get("/probe")
    async def probe_endpoint(installation: Annotated[Installation, Depends(current_installation)]) -> dict:
        return {"host": installation.host, "organization": installation.organization and installation.organization.slug}

    app.dependency_overrides[get_organization_lookup] = lambda: OrganizationLookup(lambda: db_session_factory)

    def client(base_url: str) -> httpx2.AsyncClient:
        return httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), base_url=base_url)

    return client


async def test_platform_host_is_the_installation_of_private_travellers(probe):
    async with probe("http://localhost:8000") as client:
        response = await client.get("/probe")

    assert response.json() == {"host": "localhost", "organization": None}


async def test_organization_host_resolves_its_organization(probe, db_session_factory):
    await add_acme(db_session_factory)

    async with probe("http://acme.localhost:5173") as client:
        response = await client.get("/probe")

    assert response.json() == {"host": "acme.localhost", "organization": "acme"}


async def test_unknown_host_is_not_found(probe, db_session_factory):
    await add_acme(db_session_factory)

    async with probe("http://other.localhost") as client:
        response = await client.get("/probe")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_every_api_endpoint_rejects_an_unknown_host(db_session_factory):
    main_app.dependency_overrides[get_organization_lookup] = lambda: OrganizationLookup(lambda: db_session_factory)
    transport = httpx2.ASGITransport(app=main_app)
    async with httpx2.AsyncClient(transport=transport, base_url="http://unknown.localhost") as client:
        search = await client.post("/api/v1/flights/search", json={})
        places = await client.get("/api/v1/flights/places", params={"q": "bog"})

    assert search.status_code == 404
    assert places.status_code == 404


async def test_rejects_a_taken_slug_or_hostname(db_session_factory):
    await add_acme(db_session_factory)

    async with db_session_factory() as session:
        with pytest.raises(OrganizationAlreadyExistsError):
            await create_organization(
                session, NewOrganization(slug="acme", name="Otra", hostnames=["otra.localhost"])
            )
        with pytest.raises(OrganizationAlreadyExistsError):
            await create_organization(
                session, NewOrganization(slug="otra", name="Otra", hostnames=["acme.localhost"])
            )


async def test_command_creates_an_organization_with_its_settings(db_session_factory):
    code = await anyio.to_thread.run_sync(
        create_command.main, ["--slug", "acme", "--name", "Acme", "--host", "acme.localhost", "--no-password-login"]
    )

    assert code == 0
    async with db_session_factory() as session:
        organization = await get_organization_by_slug(session, "acme")
    assert organization.settings.password_login_enabled is False
