"""Sign in through an OIDC provider, with a fake provider and the test PostgreSQL and Redis."""

from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import httpx2
import pytest
from sqlalchemy import select

from app.identity.domain.models.blocked_ips import BlockedIp
from app.identity.domain.models.providers import LoginAttempt
from app.identity.domain.models.users import User
from app.identity.services.providers import register_provider
from app.identity.testing import DeviceKey, reload_identity_settings, sign_in
from app.identity.tests.support import CLIENT_ID, CLIENT_SECRET, ISSUER, FakeIdp, assert_refused, authorize, callback

pytestmark = pytest.mark.anyio

BASE = "http://test"


@pytest.fixture
async def platform_idp(db_session_factory, idp):
    """The fake provider registered for the main installation as `test-idp`."""
    async with db_session_factory() as session, session.begin():
        await register_provider(
            session,
            organization_id=None,
            slug="test-idp",
            display_name="Proveedor de prueba",
            issuer=ISSUER,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
        )
    return idp


async def provider_sign_in(client, idp: FakeIdp, device: DeviceKey | None = None, base: str = BASE, **claims):
    """The whole round trip: authorize, sign in at the provider, callback."""
    device = device or DeviceKey()
    url = (await authorize(client, device, base, return_to="/trip")).json()["authorization_url"]
    code, state = idp.sign_in(url, **claims)
    return await callback(client, device, code, state, base), device


def error_code(response) -> str:
    """Machine-readable code of an error response."""
    return response.json()["error"]["code"]


async def test_methods_list_the_providers_of_the_installation(api, platform_idp):
    async with api() as client:
        response = await client.get("/api/v1/auth/methods")

    assert response.json() == {
        "organization_name": None,
        "password_enabled": True,
        "signup_enabled": True,
        "providers": [{"slug": "test-idp", "display_name": "Proveedor de prueba"}],
    }


async def test_authorization_url_uses_pkce_and_this_installations_callback(api, platform_idp):
    async with api() as client:
        response = await authorize(client, DeviceKey())

    url = response.json()["authorization_url"]
    query = {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}
    assert url.startswith(f"{ISSUER}/auth?")
    assert query["code_challenge_method"] == "S256" and len(query["code_challenge"]) == 43
    assert query["redirect_uri"] == "http://test:5173/auth/callback"
    assert query["client_id"] == CLIENT_ID and query["scope"] == "openid email profile"
    assert "code_verifier" not in query


async def test_known_identity_signs_in_and_goes_back(api, platform_idp, db_session_factory):
    await sign_in(db_session_factory, email="ana@example.test")  # verified account, not linked yet
    async with api() as client:
        first, _ = await provider_sign_in(client, platform_idp)
        second, _ = await provider_sign_in(client, platform_idp, email="ana.nueva@example.test")

    assert first.json()["status"] == "signed_in"
    assert first.json()["tokens"]["return_to"] == "/trip"
    # Linked by `sub`: a new email at the provider still finds the account.
    assert second.json()["status"] == "signed_in"


async def test_unknown_identity_asks_to_create_the_account(api, platform_idp, sender, db_session_factory):
    async with api() as client:
        response, device = await provider_sign_in(client, platform_idp, sub="sub-nuevo", email="nuevo@example.test")
        data = response.json()
        path = f"/api/v1/auth/signup/pending/{data['attempt_id']}"
        shown = await client.get(path, headers=device.headers("GET", f"{BASE}{path}"))
        created = await client.post(path, json={}, headers=device.headers("POST", f"{BASE}{path}"))

    assert data["status"] == "account_not_found"
    assert data["email"] == "nuevo@example.test" and data["can_create"] is True
    assert shown.json()["email"] == "nuevo@example.test"
    assert created.status_code == 200 and created.json()["return_to"] == "/trip"
    assert [m.subject for m in sender.sent] == [
        "Te damos la bienvenida a Vuelos",
        "Si quieres, crea una contraseña para Vuelos",
    ]
    assert "Entraste con Proveedor de prueba" in sender.sent[0].text
    assert "ya funciona con Proveedor de prueba" in sender.sent[1].text
    async with db_session_factory() as session:
        user = await session.scalar(select(User).where(User.email == "nuevo@example.test"))
    assert user.email_verified_at is not None and user.password is None


async def test_another_account_discards_the_identity(api, platform_idp, db_session_factory):
    async with api() as client:
        response, device = await provider_sign_in(client, platform_idp, sub="sub-nuevo", email="nuevo@example.test")
        path = f"/api/v1/auth/signup/pending/{response.json()['attempt_id']}"
        discarded = await client.delete(path, headers=device.headers("DELETE", f"{BASE}{path}"))
        again = await authorize(client, device, another_account=True)

    assert discarded.status_code == 204
    assert parse_qs(urlsplit(again.json()["authorization_url"]).query)["prompt"] == ["login"]
    async with db_session_factory() as session:
        attempts = (await session.scalars(select(LoginAttempt))).all()
    # Only the new sign in is left; the discarded identity is gone.
    assert [(a.status, a.verified_identity) for a in attempts] == [("started", None)]


async def test_only_the_device_that_signed_in_can_create_the_account(api, platform_idp):
    async with api() as client:
        response, _ = await provider_sign_in(client, platform_idp, sub="sub-nuevo", email="nuevo@example.test")
        path = f"/api/v1/auth/signup/pending/{response.json()['attempt_id']}"
        other = DeviceKey()
        created = await client.post(path, json={}, headers=other.headers("POST", f"{BASE}{path}"))

    assert created.status_code == 400
    assert error_code(created) == "invalid_login_attempt"


async def test_callback_from_another_device_is_refused(api, platform_idp, caplog):
    """Login CSRF: a code obtained by someone else can't be finished on the victim's device."""
    async with api() as client:
        url = (await authorize(client, DeviceKey())).json()["authorization_url"]
        code, state = platform_idp.sign_in(url)
        response = await callback(client, DeviceKey(), code, state)

    assert_refused(response, caplog, "invalid_login_attempt")
    assert platform_idp.token_requests == 0


async def test_callback_works_once(api, platform_idp, caplog):
    async with api() as client:
        device = DeviceKey()
        url = (await authorize(client, device)).json()["authorization_url"]
        code, state = platform_idp.sign_in(url)
        first = await callback(client, device, code, state)
        again = await callback(client, device, code, state)

    assert first.status_code == 200
    assert_refused(again, caplog, "invalid_login_attempt")


@pytest.mark.parametrize(
    "claims",
    [
        {"email_verified": False},
        {"nonce": "otro"},
        {"aud": "otro-cliente"},
        {"iss": "https://otro.test"},
        {"exp": 1},
    ],
    ids=["unverified-email", "nonce", "audience", "issuer", "expired"],
)
async def test_id_token_that_fails_a_check_is_refused(api, platform_idp, claims, caplog):
    async with api() as client:
        response, _ = await provider_sign_in(client, platform_idp, **claims)

    assert_refused(response, caplog, "invalid_identity")


async def test_reads_the_keys_again_when_the_provider_rotates_them(api, platform_idp, db_session_factory):
    await sign_in(db_session_factory, email="ana@example.test")
    async with api() as client:
        await provider_sign_in(client, platform_idp)
        platform_idp.rotate_key()
        response, _ = await provider_sign_in(client, platform_idp)

    assert response.json()["status"] == "signed_in"
    assert platform_idp.jwks_requests == 2


async def test_never_links_an_unverified_account(api, platform_idp, db_session_factory, caplog):
    """Pre-account takeover: whoever registered the email without proving it loses that account."""
    async with api() as client:
        await client.post(
            "/api/v1/auth/password/signup",
            json={"email": "ana@example.test", "display_name": "Intruso", "password": "clave-del-intruso"},
        )
        response, device = await provider_sign_in(client, platform_idp)
        path = f"/api/v1/auth/signup/pending/{response.json()['attempt_id']}"
        await client.post(path, json={}, headers=device.headers("POST", f"{BASE}{path}"))
        intruder = await client.post(
            "/api/v1/auth/password/login",
            json={"email": "ana@example.test", "password": "clave-del-intruso"},
            headers=DeviceKey().headers("POST", f"{BASE}/api/v1/auth/password/login"),
        )

    assert response.json()["status"] == "account_not_found"
    assert_refused(intruder, caplog, "password_not_set")


async def test_a_refused_code_looks_like_any_other_failure(api, platform_idp, caplog):
    async with api() as client:
        device = DeviceKey()
        url = (await authorize(client, device)).json()["authorization_url"]
        _, state = platform_idp.sign_in(url)
        response = await callback(client, device, "codigo-falso", state)

    assert_refused(response, caplog, "identity_provider_error")


async def test_unknown_provider_is_not_found(api, platform_idp):
    async with api() as client:
        response = await authorize(client, DeviceKey(), slug="nadie")

    assert error_code(response) == "provider_not_found"


async def test_return_to_must_be_a_path_of_this_app(api, platform_idp):
    async with api() as client:
        response = await authorize(client, DeviceKey(), return_to="https://malo.test/robar")

    assert response.status_code == 422


async def test_creating_the_account_keeps_the_optional_phone_and_language(api, platform_idp, db_session_factory):
    async with api() as client:
        response, device = await provider_sign_in(client, platform_idp, sub="sub-nuevo", email="nuevo@example.test")
        path = f"/api/v1/auth/signup/pending/{response.json()['attempt_id']}"
        body = {"phone_number": "+5491112345678", "language": "es"}
        created = await client.post(path, json=body, headers=device.headers("POST", f"{BASE}{path}"))

    assert created.status_code == 200
    async with db_session_factory() as session:
        user = await session.scalar(select(User).where(User.email == "nuevo@example.test"))
    assert user.phone_number == "+5491112345678"
    assert user.language == "es"


async def test_an_address_blocked_for_passwords_can_still_sign_in_through_the_provider(
    api, platform_idp, db_session_factory
):
    """The provider vouches for its people: the password limits don't apply to it."""
    await sign_in(db_session_factory, email="ana@example.test")
    async with db_session_factory() as session, session.begin():
        session.add(BlockedIp(ip="127.0.0.1", blocked_until=datetime.now(UTC) + timedelta(hours=1), reason="test"))
    async with api() as client:
        response, _ = await provider_sign_in(client, platform_idp)

    assert response.json()["status"] == "signed_in"


async def test_provider_failures_dont_count_against_the_address(api, platform_idp, sender, monkeypatch):
    monkeypatch.setenv("IP_FAILED_LOGINS_LIMIT", "2")
    reload_identity_settings()
    async with api() as client:
        for _ in range(3):
            await provider_sign_in(client, platform_idp, nonce="otro")
        lookup = await client.post("/api/v1/auth/password/lookup", json={"email": "ana@example.test"})

    assert lookup.status_code == 200
