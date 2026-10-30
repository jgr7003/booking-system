"""Tokens, DPoP and device sessions through the API, against the test PostgreSQL and Redis."""

import asyncio

import httpx2
import pytest
from sqlalchemy import select

from app.core.db import get_db_session, get_session_factory
from app.identity.api.dependencies import get_identity_redis
from app.identity.core.config import get_identity_settings
from app.identity.domain.dtos.tokens import DeviceInfo
from app.identity.domain.models.sessions import DeviceSession
from app.identity.repositories.users import UserRepository
from app.identity.services.sessions import SessionStatusCache, open_device_session
from app.identity.testing import DeviceKey, TestSession, sign_in
from app.main import app

pytestmark = pytest.mark.anyio

BASE = "http://test"
ME = "/api/v1/me"
REFRESH = "/api/v1/auth/token/refresh"


@pytest.fixture
async def client(db_session_factory, redis_client):
    """HTTP client of the app wired to the test database and the test Redis.

    Args:
        db_session_factory: Factory of sessions on the test database.
        redis_client: Client of the test Redis.

    Yields:
        The client.
    """

    async def session():
        """One session per request, as in production."""
        async with db_session_factory() as s:
            yield s

    app.dependency_overrides[get_db_session] = session
    app.dependency_overrides[get_session_factory] = lambda: db_session_factory
    app.dependency_overrides[get_identity_redis] = lambda: redis_client
    async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=app), base_url=BASE) as http:
        yield http


async def get_me(client: httpx2.AsyncClient, signed: TestSession) -> httpx2.Response:
    """`GET /me` as a well-behaved device."""
    return await client.get(ME, headers=signed.headers("GET", ME))


async def refresh(client: httpx2.AsyncClient, device: DeviceKey, refresh_token: str) -> httpx2.Response:
    """`POST /auth/token/refresh` signed by a device."""
    return await client.post(
        REFRESH, json={"refresh_token": refresh_token}, headers=device.headers("POST", f"{BASE}{REFRESH}")
    )


async def session_row(session_factory, signed: TestSession) -> DeviceSession:
    """The stored device session of a signed-in test session."""
    async with session_factory() as s:
        return await s.scalar(select(DeviceSession).where(DeviceSession.id == signed.tokens.session_id))


def error_code(response: httpx2.Response) -> str:
    """Machine-readable code of an error response."""
    return response.json()["error"]["code"]


async def test_me_answers_the_signed_in_user(client, db_session_factory):
    signed = await sign_in(db_session_factory)

    response = await get_me(client, signed)

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "ana@example.test"
    assert data["organization"] is None
    assert data["has_password"] is False
    assert data["session_id"] == str(signed.tokens.session_id)


async def test_without_authorization_asks_to_sign_in(client):
    response = await client.get(ME)

    assert response.status_code == 401
    assert error_code(response) == "authentication_required"


async def test_publishes_only_public_signing_keys(client):
    keys = (await client.get("/api/v1/auth/jwks.json")).json()["keys"]

    assert keys and all("d" not in key and key["alg"] == "ES256" and key["kid"] for key in keys)


async def test_bearer_token_closes_the_session(client, db_session_factory):
    signed = await sign_in(db_session_factory)

    stolen = await client.get(ME, headers={"Authorization": f"Bearer {signed.tokens.access_token}"})
    after = await get_me(client, signed)

    assert error_code(stolen) == "token_binding_mismatch"
    assert error_code(after) == "session_revoked"
    assert (await session_row(db_session_factory, signed)).revoked_reason == "key_mismatch"


async def test_token_without_proof_closes_the_session(client, db_session_factory):
    signed = await sign_in(db_session_factory)

    stolen = await client.get(ME, headers={"Authorization": f"DPoP {signed.tokens.access_token}"})

    assert error_code(stolen) == "token_binding_mismatch"
    assert error_code(await get_me(client, signed)) == "session_revoked"


async def test_token_with_another_devices_proof_closes_the_session(client, db_session_factory):
    signed = await sign_in(db_session_factory)
    thief = DeviceKey()

    stolen = await client.get(ME, headers=thief.headers("GET", f"{BASE}{ME}", signed.tokens.access_token))

    assert error_code(stolen) == "token_binding_mismatch"
    assert error_code(await get_me(client, signed)) == "session_revoked"


@pytest.mark.parametrize(
    "overrides",
    [
        {"htu": f"{BASE}/api/v1/me/sessions"},
        {"htm": "POST"},
        {"iat": 1},
        {"ath": "otro"},
        {"jti": "x"},
    ],
    ids=["other-url", "other-method", "stale", "other-token", "short-jti"],
)
async def test_invalid_proof_is_refused_but_keeps_the_session(client, db_session_factory, overrides):
    signed = await sign_in(db_session_factory)
    token = signed.tokens.access_token
    headers = {"Authorization": f"DPoP {token}", "DPoP": signed.device.proof("GET", f"{BASE}{ME}", token, **overrides)}

    response = await client.get(ME, headers=headers)

    assert error_code(response) == "invalid_dpop_proof"
    assert (await get_me(client, signed)).status_code == 200


async def test_replayed_proof_is_refused(client, db_session_factory):
    signed = await sign_in(db_session_factory)
    headers = signed.headers("GET", ME)

    first = await client.get(ME, headers=headers)
    replay = await client.get(ME, headers=headers)

    assert first.status_code == 200
    assert error_code(replay) == "invalid_dpop_proof"


async def test_expired_token_asks_for_a_refresh(client, db_session_factory, monkeypatch):
    monkeypatch.setenv("ACCESS_TOKEN_TTL_S", "-1")
    get_identity_settings.cache_clear()
    signed = await sign_in(db_session_factory)

    response = await get_me(client, signed)

    assert error_code(response) == "token_expired"


async def test_token_of_another_installation_is_not_valid(client, db_session_factory):
    signed = await sign_in(db_session_factory, host="acme.localhost")

    response = await get_me(client, signed)

    assert error_code(response) == "invalid_token"


async def test_refresh_rotates_the_tokens(client, db_session_factory):
    signed = await sign_in(db_session_factory)

    response = await refresh(client, signed.device, signed.tokens.refresh_token)

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "DPoP"
    assert data["refresh_token"] != signed.tokens.refresh_token
    assert data["session_id"] == str(signed.tokens.session_id)
    headers = signed.device.headers("GET", f"{BASE}{ME}", data["access_token"])
    assert (await client.get(ME, headers=headers)).status_code == 200


async def test_reused_refresh_token_closes_the_session(client, db_session_factory):
    signed = await sign_in(db_session_factory)
    first = await refresh(client, signed.device, signed.tokens.refresh_token)

    reuse = await refresh(client, signed.device, signed.tokens.refresh_token)
    newest = await refresh(client, signed.device, first.json()["refresh_token"])

    assert error_code(reuse) == "session_revoked"
    assert error_code(newest) == "session_revoked"
    assert (await session_row(db_session_factory, signed)).revoked_reason == "refresh_reuse"


async def test_refresh_from_another_device_closes_the_session(client, db_session_factory):
    signed = await sign_in(db_session_factory)

    response = await refresh(client, DeviceKey(), signed.tokens.refresh_token)

    assert error_code(response) == "session_revoked"
    assert (await session_row(db_session_factory, signed)).revoked_reason == "key_mismatch"


async def test_two_concurrent_refreshes_of_one_token_close_the_session(client, db_session_factory):
    signed = await sign_in(db_session_factory)

    responses = await asyncio.gather(
        refresh(client, signed.device, signed.tokens.refresh_token),
        refresh(client, signed.device, signed.tokens.refresh_token),
    )

    assert sorted(r.status_code for r in responses) == [200, 401]
    assert (await session_row(db_session_factory, signed)).revoked_reason == "refresh_reuse"


async def test_unknown_refresh_token_is_not_valid(client):
    response = await refresh(client, DeviceKey(), "no-existe")

    assert error_code(response) == "invalid_token"


async def test_lists_devices_and_marks_the_current_one(client, db_session_factory):
    laptop = await sign_in(db_session_factory, device_name="Chrome en Windows")
    phone = await sign_in(db_session_factory, device_name="Safari en iPhone")

    response = await client.get("/api/v1/me/sessions", headers=laptop.headers("GET", "/api/v1/me/sessions"))

    sessions = response.json()["sessions"]
    assert {s["device_name"] for s in sessions} == {"Chrome en Windows", "Safari en iPhone"}
    assert [s["current"] for s in sessions if s["id"] == str(laptop.tokens.session_id)] == [True]
    assert [s["current"] for s in sessions if s["id"] == str(phone.tokens.session_id)] == [False]


async def test_closing_a_device_logs_it_out_at_once(client, db_session_factory):
    laptop = await sign_in(db_session_factory)
    phone = await sign_in(db_session_factory)
    assert (await get_me(client, phone)).status_code == 200  # now cached as open in Redis

    path = f"/api/v1/me/sessions/{phone.tokens.session_id}"
    closed = await client.delete(path, headers=laptop.headers("DELETE", path))

    assert closed.status_code == 204
    assert error_code(await get_me(client, phone)) == "session_revoked"
    assert (await get_me(client, laptop)).status_code == 200


async def test_cannot_close_a_session_of_another_user(client, db_session_factory):
    ana = await sign_in(db_session_factory, email="ana@example.test")
    beto = await sign_in(db_session_factory, email="beto@example.test")

    path = f"/api/v1/me/sessions/{beto.tokens.session_id}"
    response = await client.delete(path, headers=ana.headers("DELETE", path))

    assert error_code(response) == "session_not_found"
    assert (await get_me(client, beto)).status_code == 200


async def test_closing_the_other_devices_keeps_this_one(client, db_session_factory):
    laptop = await sign_in(db_session_factory)
    phone = await sign_in(db_session_factory)
    tablet = await sign_in(db_session_factory)

    path = "/api/v1/me/sessions?scope=others"
    response = await client.delete(path, headers=laptop.headers("DELETE", "/api/v1/me/sessions"))

    assert response.status_code == 204
    assert (await get_me(client, laptop)).status_code == 200
    assert error_code(await get_me(client, phone)) == "session_revoked"
    assert error_code(await get_me(client, tablet)) == "session_revoked"


async def test_signing_in_again_from_the_same_device_replaces_its_session(db_session_factory):
    first = await sign_in(db_session_factory)
    async with db_session_factory() as session, session.begin():
        user = await UserRepository(session).get(first.user.id)
        await open_device_session(
            session,
            SessionStatusCache(None),
            user=user,
            issuer="test",
            device=DeviceInfo(jkt=first.device.jkt, device_name="x"),
        )

    assert (await session_row(db_session_factory, first)).revoked_at is not None


async def test_logout_closes_this_device(client, db_session_factory):
    signed = await sign_in(db_session_factory)

    response = await client.post("/api/v1/auth/logout", headers=signed.headers("POST", "/api/v1/auth/logout"))

    assert response.status_code == 204
    assert error_code(await get_me(client, signed)) == "session_revoked"


async def test_works_without_redis(client, db_session_factory):
    app.dependency_overrides[get_identity_redis] = lambda: None
    signed = await sign_in(db_session_factory)

    assert (await get_me(client, signed)).status_code == 200
    await client.post("/api/v1/auth/logout", headers=signed.headers("POST", "/api/v1/auth/logout"))
    assert error_code(await get_me(client, signed)) == "session_revoked"


async def test_an_expired_session_says_so(client, db_session_factory):
    signed = await sign_in(db_session_factory)
    async with db_session_factory() as session, session.begin():
        row = await session.get(DeviceSession, signed.tokens.session_id)
        row.idle_expires_at = row.created_at

    me = await get_me(client, signed)
    renewed = await refresh(client, signed.device, signed.tokens.refresh_token)

    assert error_code(me) == "session_expired"
    assert error_code(renewed) == "session_expired"
