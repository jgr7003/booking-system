"""Sign in at an organization's installation: its own provider, its own users, its own settings."""

import pytest

from app.identity.services.organization_users import give_access
from app.identity.services.providers import register_provider
from app.identity.testing import DeviceKey, sign_in
from app.identity.tests.support import CLIENT_ID, CLIENT_SECRET, ISSUER, authorize, callback

pytestmark = pytest.mark.anyio

ACME = "http://acme.localhost"


@pytest.fixture
async def acme(add_organization, db_session_factory, idp):
    """Acme with the fake provider as its own (`acme-sso`) and one user it gave access to."""
    organization = await add_organization()
    async with db_session_factory() as session, session.begin():
        await register_provider(
            session,
            organization_id=organization.id,
            slug="acme-sso",
            display_name="Acme SSO",
            issuer=ISSUER,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
        )
        await give_access(session, organization, email="viajero@acme.test", display_name="Viajero Acme")
    return organization


async def acme_sign_in(client, idp, **claims):
    """Round trip through Acme's provider."""
    device = DeviceKey()
    url = (await authorize(client, device, ACME, slug="acme-sso")).json()["authorization_url"]
    code, state = idp.sign_in(url, **claims)
    return await callback(client, device, code, state, ACME, slug="acme-sso"), device


async def test_methods_show_the_organization_and_its_provider(api, acme):
    async with api(ACME) as client:
        acme_methods = (await client.get("/api/v1/auth/methods")).json()
    async with api() as client:
        main_methods = (await client.get("/api/v1/auth/methods")).json()

    assert acme_methods == {
        "organization_name": "Acme",
        "password_enabled": True,
        "signup_enabled": False,
        "providers": [{"slug": "acme-sso", "display_name": "Acme SSO"}],
    }
    assert main_methods["providers"] == []


async def test_providers_belong_to_their_installation(api, acme):
    async with api() as client:
        response = await authorize(client, DeviceKey(), slug="acme-sso")

    assert response.json()["error"]["code"] == "provider_not_found"


async def test_a_user_the_organization_created_signs_in_and_gets_linked(api, acme, idp):
    async with api(ACME) as client:
        first, _ = await acme_sign_in(client, idp, sub="sub-viajero", email="viajero@acme.test")
        second, _ = await acme_sign_in(client, idp, sub="sub-viajero", email="viajero.nuevo@acme.test")

    assert first.json()["status"] == "signed_in"
    assert second.json()["status"] == "signed_in"


async def test_someone_the_organization_didnt_add_cant_create_an_account(api, acme, idp):
    async with api(ACME) as client:
        response, device = await acme_sign_in(client, idp, sub="sub-intruso", email="intruso@acme.test")
        path = f"/api/v1/auth/signup/pending/{response.json()['attempt_id']}"
        create = await client.post(path, json={}, headers=device.headers("POST", f"{ACME}{path}"))
        discard = await client.delete(path, headers=device.headers("DELETE", f"{ACME}{path}"))

    assert response.json()["status"] == "account_not_found"
    assert response.json()["can_create"] is False
    assert create.status_code == 403
    assert create.json()["error"]["code"] == "signup_not_allowed"
    assert discard.status_code == 204


async def test_a_private_account_with_the_same_email_is_not_the_organizations(api, acme, idp, db_session_factory):
    """The same person may be a private traveller and an Acme user: two accounts, never mixed."""
    await sign_in(db_session_factory, email="intruso@acme.test")  # private traveller
    async with api(ACME) as client:
        response, _ = await acme_sign_in(client, idp, sub="sub-intruso", email="intruso@acme.test")

    assert response.json()["status"] == "account_not_found"


async def test_organization_without_passwords_shows_only_its_provider(api, add_organization):
    await add_organization(slug="solosso", host="solosso.localhost", password_login_enabled=False)

    async with api("http://solosso.localhost") as client:
        methods = (await client.get("/api/v1/auth/methods")).json()

    assert methods["password_enabled"] is False
