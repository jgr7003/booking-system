"""Email-and-password accounts through the API, against the test PostgreSQL and Redis."""

from datetime import UTC, datetime, timedelta

import anyio
import pytest
from sqlalchemy import select, update

from app.identity.commands import add_organization_user
from app.identity.core.config import get_identity_settings
from app.identity.domain.models.email_tokens import EmailToken
from app.identity.domain.models.sessions import DeviceSession
from app.identity.domain.models.users import User
from app.identity.services.organization_users import give_access
from app.identity.testing import DeviceKey, RecordingEmailSender, sign_in
from app.identity.tests.support import assert_refused

pytestmark = pytest.mark.anyio

BASE = "http://test"
PASSWORD = "una-clave-larga"
EMAIL = "ana@example.test"


async def post(client, path: str, body: dict, device: DeviceKey | None = None, base: str = BASE):
    """POSTs a JSON body, signed by a device when given."""
    headers = device.headers("POST", f"{base}{path}") if device else {}
    return await client.post(path, json=body, headers=headers)


async def sign_up(client, email: str = EMAIL, password: str = PASSWORD):
    """Signs a private traveller up."""
    return await post(
        client, "/api/v1/auth/password/signup", {"email": email, "display_name": "Ana", "password": password}
    )


async def login(client, email: str = EMAIL, password: str = PASSWORD, base: str = BASE):
    """Signs in from a new device."""
    body = {"email": email, "password": password}
    return await post(client, "/api/v1/auth/password/login", body, DeviceKey(), base)


async def verify(client, token: str):
    """Opens the verification link from a new device."""
    return await post(client, "/api/v1/auth/email/verify", {"token": token}, DeviceKey())


async def set_password(client, token: str, password: str, base: str = BASE):
    """Sets a password from a link."""
    return await post(client, "/api/v1/auth/password/set", {"token": token, "password": password}, base=base)


def error_code(response) -> str:
    """Machine-readable code of an error response."""
    return response.json()["error"]["code"]


async def test_sign_up_verify_and_sign_in(api, sender, caplog):
    async with api() as client:
        assert (await sign_up(client)).status_code == 202
        before = await login(client)
        verified = await verify(client, sender.last_token(EMAIL))
        after = await login(client)

    assert_refused(before, caplog, "email_not_verified")
    assert verified.status_code == 200 and verified.json()["token_type"] == "DPoP"
    assert after.status_code == 200
    assert "http://test:5173/account/verify-email?token=" in sender.sent[0].text
    assert sender.sent[-1].subject == "Te damos la bienvenida a Vuelos"
    assert "Verificaste tu email" in sender.sent[-1].text


async def test_verification_link_works_once(api, sender):
    async with api() as client:
        await sign_up(client)
        token = sender.last_token(EMAIL)
        await verify(client, token)
        again = await verify(client, token)

    assert again.status_code == 410
    assert error_code(again) == "invalid_link"


async def test_wrong_password_and_unknown_email_look_the_same(api, sender, caplog):
    async with api() as client:
        await sign_up(client)
        await verify(client, sender.last_token(EMAIL))
        wrong = await login(client, password="otra-clave-larga")
        unknown = await login(client, email="nadie@example.test")

    assert wrong.json() == unknown.json()
    assert_refused(wrong, caplog, "wrong_password")
    assert_refused(unknown, caplog, "unknown_email")


async def test_lookup_tells_whether_the_account_exists_and_has_a_password(api, sender, db_session_factory):
    await sign_in(db_session_factory, email="sso@example.test")  # created by SSO: no password
    async with api() as client:
        await sign_up(client)
        lookup = [
            (await post(client, "/api/v1/auth/password/lookup", {"email": e})).json()
            for e in (EMAIL, "sso@example.test", "nadie@example.test")
        ]

    assert lookup == [
        {"exists": True, "has_password": True},
        {"exists": True, "has_password": False},
        {"exists": False, "has_password": False},
    ]


async def test_account_without_password_cant_sign_in_with_one(api, db_session_factory, caplog):
    await sign_in(db_session_factory, email="sso@example.test")
    async with api() as client:
        response = await login(client, email="sso@example.test")

    assert_refused(response, caplog, "password_not_set")


async def test_cannot_sign_up_twice_with_a_verified_email(api, sender):
    async with api() as client:
        await sign_up(client)
        await verify(client, sender.last_token(EMAIL))
        again = await sign_up(client)

    assert again.status_code == 409


async def test_signing_up_again_takes_over_an_unverified_account(api, sender, caplog):
    """Whoever registered the email first never proved it was theirs: their password stops working."""
    async with api() as client:
        await sign_up(client, password="clave-del-intruso")
        await sign_up(client, password=PASSWORD)
        await verify(client, sender.last_token(EMAIL))
        intruder = await login(client, password="clave-del-intruso")
        owner = await login(client)

    assert_refused(intruder, caplog, "wrong_password")
    assert owner.status_code == 200


async def test_reset_password_closes_every_session(api, sender, db_session_factory, caplog):
    async with api() as client:
        await sign_up(client)
        await verify(client, sender.last_token(EMAIL))
        await login(client)
        forgot = await post(client, "/api/v1/auth/password/forgot", {"email": EMAIL})
        assert "kind=reset" in sender.sent[-1].text
        reset = await set_password(client, sender.last_token(EMAIL), "nueva-clave-larga")
        old = await login(client)
        new = await login(client, password="nueva-clave-larga")

    assert forgot.status_code == 202 and reset.status_code == 204
    assert_refused(old, caplog, "wrong_password")
    assert new.status_code == 200
    async with db_session_factory() as session:
        reasons = set((await session.scalars(select(DeviceSession.revoked_reason))).all())
    assert "password_changed" in reasons


async def test_forgot_password_says_nothing_about_unknown_emails(api, sender):
    async with api() as client:
        response = await post(client, "/api/v1/auth/password/forgot", {"email": "nadie@example.test"})

    assert response.status_code == 202
    assert sender.sent == []


async def test_account_created_by_sso_can_create_its_first_password(api, sender, db_session_factory):
    await sign_in(db_session_factory, email="sso@example.test")
    async with api() as client:
        await post(client, "/api/v1/auth/password/forgot", {"email": "sso@example.test"})
        assert "kind=set" in sender.sent[-1].text
        created = await set_password(client, sender.last_token("sso@example.test"), PASSWORD)
        response = await login(client, email="sso@example.test")

    assert created.status_code == 204
    assert response.status_code == 200


async def test_expired_link_is_refused(api, sender, db_session_factory):
    async with api() as client:
        await sign_up(client)
        async with db_session_factory() as session, session.begin():
            await session.execute(update(EmailToken).values(expires_at=datetime.now(UTC) - timedelta(seconds=1)))
        response = await verify(client, sender.last_token(EMAIL))

    assert error_code(response) == "invalid_link"


async def test_new_link_replaces_the_previous_one(api, sender, db_session_factory):
    await sign_in(db_session_factory, email="sso@example.test")
    async with api() as client:
        await post(client, "/api/v1/auth/password/forgot", {"email": "sso@example.test"})
        first = sender.last_token("sso@example.test")
        await post(client, "/api/v1/auth/password/forgot", {"email": "sso@example.test"})
        response = await set_password(client, first, PASSWORD)

    assert error_code(response) == "invalid_link"


async def verified_account(client, sender, email: str = EMAIL) -> None:
    """Signs a private traveller up and verifies the email."""
    await sign_up(client, email=email)
    await verify(client, sender.last_token(email))


async def test_wrong_passwords_lock_the_account_and_email_the_user(api, sender, caplog):
    async with api() as client:
        await verified_account(client, sender)
        wrong = [await login(client, password="otra-clave-larga") for _ in range(3)]
        right_but_locked = await login(client)

    for response in wrong:
        assert_refused(response, caplog, "wrong_password")
    assert_refused(right_but_locked, caplog, "account_locked")
    locked_email = sender.sent[-1]
    assert locked_email.subject == "Bloqueamos el ingreso con tu contraseña"
    assert "¿Fuiste tú?" in locked_email.text and "30 minutos" in locked_email.text
    assert "/account/password?token=" in locked_email.text and "kind=reset" in locked_email.text


async def test_changing_the_password_unlocks_the_account(api, sender):
    async with api() as client:
        await verified_account(client, sender)
        for _ in range(3):
            await login(client, password="otra-clave-larga")
        changed = await set_password(client, sender.last_token(EMAIL), "nueva-clave-larga")
        response = await login(client, password="nueva-clave-larga")

    assert changed.status_code == 204
    assert response.status_code == 200


async def test_the_lock_expires(api, sender, db_session_factory):
    async with api() as client:
        await verified_account(client, sender)
        for _ in range(3):
            await login(client, password="otra-clave-larga")
        async with db_session_factory() as session, session.begin():
            await session.execute(update(User).values(locked_until=datetime.now(UTC) - timedelta(seconds=1)))
        response = await login(client)

    assert response.status_code == 200
    async with db_session_factory() as session:
        user = await session.scalar(select(User).where(User.email == EMAIL))
    assert user.failed_login_attempts == 0 and user.locked_until is None


async def test_a_successful_sign_in_starts_the_count_again(api, sender):
    async with api() as client:
        await verified_account(client, sender)
        for _ in range(2):
            await login(client, password="otra-clave-larga")
        await login(client)
        for _ in range(2):
            await login(client, password="otra-clave-larga")
        response = await login(client)

    assert response.status_code == 200
    assert all(m.subject != "Bloqueamos el ingreso con tu contraseña" for m in sender.sent)


async def test_each_organization_sets_its_own_limit(api, add_organization, db_session_factory):
    acme = await add_organization(max_failed_logins=5)
    async with db_session_factory() as session, session.begin():
        await give_access(session, acme, email="viajero@acme.test", display_name="Viajero")
    base = "http://acme.localhost"
    async with api(base) as client:
        attempts = [await login(client, email="viajero@acme.test", base=base) for _ in range(4)]

    async with db_session_factory() as session:
        user = await session.scalar(select(User).where(User.email == "viajero@acme.test"))
    assert all(r.status_code == 401 for r in attempts)
    assert user.failed_login_attempts == 0  # no password set yet: nothing to guess
    assert user.locked_until is None


async def test_an_address_trying_many_emails_is_blocked(api, sender, caplog, monkeypatch):
    monkeypatch.setenv("IP_DISTINCT_EMAILS_LIMIT", "3")
    get_identity_settings.cache_clear()
    async with api() as client:
        await verified_account(client, sender)
        for name in ("uno", "dos", "tres"):
            await login(client, email=f"{name}@example.test")
        blocked = await login(client)
        lookup = await post(client, "/api/v1/auth/password/lookup", {"email": EMAIL})

    assert_refused(blocked, caplog, "address_blocked")
    assert lookup.status_code == 401
    assert "ip=127.0.0.1 installation=test reason=too_many_emails" in caplog.text


async def test_an_address_with_many_failures_is_blocked(api, sender, caplog, monkeypatch):
    monkeypatch.setenv("IP_FAILED_LOGINS_LIMIT", "4")
    get_identity_settings.cache_clear()
    async with api() as client:
        await verified_account(client, sender)
        await verified_account(client, sender, email="beto@example.test")
        for _ in range(2):
            await login(client, password="otra-clave-larga")
            await login(client, email="beto@example.test", password="otra-clave-larga")
        response = await login(client, email="beto@example.test")

    assert_refused(response, caplog, "address_blocked")


async def test_lookups_of_unknown_emails_count_against_the_address(api, sender, monkeypatch):
    monkeypatch.setenv("IP_DISTINCT_EMAILS_LIMIT", "3")
    get_identity_settings.cache_clear()
    async with api() as client:
        await verified_account(client, sender)
        for name in ("uno", "dos", "tres"):
            await post(client, "/api/v1/auth/password/lookup", {"email": f"{name}@example.test"})
        response = await login(client)

    assert response.status_code == 401


async def test_sign_up_keeps_the_optional_phone_and_language(api, sender):
    async with api() as client:
        await post(
            client,
            "/api/v1/auth/password/signup",
            {
                "email": EMAIL,
                "display_name": "Ana",
                "password": PASSWORD,
                "phone_number": "+54 9 11 1234-5678",
                "language": "en",
            },
        )
        tokens = (await verify(client, sender.last_token(EMAIL))).json()
        device = DeviceKey()
        login_response = await post(
            client, "/api/v1/auth/password/login", {"email": EMAIL, "password": PASSWORD}, device
        )
        access = login_response.json()["access_token"]
        me = await client.get("/api/v1/me", headers=device.headers("GET", f"{BASE}/api/v1/me", access))

    assert tokens["token_type"] == "DPoP"
    assert me.json()["phone_number"] == "+5491112345678"
    assert me.json()["language"] == "en"


async def test_without_a_language_the_app_decides(api, sender):
    async with api() as client:
        await verified_account(client, sender)
        device = DeviceKey()
        access = (
            await post(client, "/api/v1/auth/password/login", {"email": EMAIL, "password": PASSWORD}, device)
        ).json()["access_token"]
        me = await client.get("/api/v1/me", headers=device.headers("GET", f"{BASE}/api/v1/me", access))

    assert me.json()["language"] is None
    assert me.json()["phone_number"] is None


@pytest.mark.parametrize("field", [{"phone_number": "1234"}, {"language": "fr"}])
async def test_rejects_an_invalid_phone_or_language(api, field):
    body = {"email": EMAIL, "display_name": "Ana", "password": PASSWORD} | field
    async with api() as client:
        response = await post(client, "/api/v1/auth/password/signup", body)

    assert response.status_code == 422


async def test_rejects_a_short_password(api):
    async with api() as client:
        response = await sign_up(client, password="corta")

    assert response.status_code == 422


async def test_organization_without_passwords_has_no_password_routes(api, add_organization):
    await add_organization(password_login_enabled=False)
    base = "http://acme.localhost"
    async with api(base) as client:
        responses = [
            await post(client, "/api/v1/auth/password/lookup", {"email": EMAIL}),
            await login(client, base=base),
            await post(client, "/api/v1/auth/password/forgot", {"email": EMAIL}),
            await set_password(client, "x" * 30, PASSWORD, base=base),
        ]

    assert [r.status_code for r in responses] == [404, 404, 404, 404]


async def test_organizations_have_no_sign_up(api, add_organization):
    await add_organization()
    async with api("http://acme.localhost") as client:
        response = await sign_up(client)

    assert response.status_code == 404


async def test_link_of_one_installation_is_refused_in_another(api, sender, add_organization):
    await add_organization()
    async with api() as client:
        await sign_up(client)
    async with api("http://acme.localhost") as client:
        response = await post(
            client,
            "/api/v1/auth/email/verify",
            {"token": sender.last_token(EMAIL)},
            DeviceKey(),
            base="http://acme.localhost",
        )

    assert error_code(response) == "invalid_link"


@pytest.mark.parametrize(("password_login", "emails"), [(True, 2), (False, 1)])
async def test_organization_user_gets_the_password_email_only_if_allowed(
    add_organization, db_session_factory, monkeypatch, password_login, emails
):
    recorder = RecordingEmailSender()
    monkeypatch.setattr(add_organization_user, "create_email_sender", lambda: recorder)
    await add_organization(password_login_enabled=password_login)

    code = await anyio.to_thread.run_sync(
        add_organization_user.main, ["--org", "acme", "--email", "viajero@acme.test", "--name", "Viajero"]
    )

    assert code == 0
    assert len(recorder.sent) == emails
    assert "Acme te dio acceso" in recorder.sent[0].text
    if emails == 2:
        assert "http://acme.localhost:5173/account/password?token=" in recorder.sent[1].text
    async with db_session_factory() as session:
        user = await session.scalar(select(User).where(User.email == "viajero@acme.test"))
    assert user.password is None


async def test_a_device_that_fails_too_much_is_stopped_but_others_arent(api, sender, caplog, monkeypatch):
    """People behind one office address are different devices: one failing doesn't stop the rest."""
    monkeypatch.setenv("DEVICE_FAILED_LOGINS_LIMIT", "2")
    get_identity_settings.cache_clear()
    path = "/api/v1/auth/password/login"
    async with api() as client:
        await verified_account(client, sender)
        await verified_account(client, sender, email="beto@example.test")
        noisy = DeviceKey()
        for _ in range(2):
            await post(client, path, {"email": "beto@example.test", "password": "otra-clave-larga"}, noisy)
        stopped = await post(client, path, {"email": "beto@example.test", "password": PASSWORD}, noisy)
        other_device = await login(client)

    assert_refused(stopped, caplog, "device_limited")
    assert other_device.status_code == 200


async def test_a_block_in_one_installation_doesnt_reach_another(api, sender, add_organization, monkeypatch):
    monkeypatch.setenv("IP_FAILED_LOGINS_LIMIT", "2")
    get_identity_settings.cache_clear()
    await add_organization()
    async with api() as client:
        await verified_account(client, sender)
        for _ in range(2):
            await login(client, password="otra-clave-larga")
        blocked_here = await login(client)
    async with api("http://acme.localhost") as acme:
        lookup = await post(acme, "/api/v1/auth/password/lookup", {"email": EMAIL}, base="http://acme.localhost")

    assert blocked_here.status_code == 401
    assert lookup.status_code == 200


async def test_trusted_networks_of_an_organization_are_never_blocked(api, add_organization, monkeypatch):
    monkeypatch.setenv("IP_FAILED_LOGINS_LIMIT", "2")
    get_identity_settings.cache_clear()
    await add_organization(trusted_networks=["127.0.0.0/8"])
    base = "http://acme.localhost"
    async with api(base) as client:
        for name in ("uno", "dos", "tres", "cuatro"):
            await login(client, email=f"{name}@acme.test", base=base)
        lookup = await post(client, "/api/v1/auth/password/lookup", {"email": "uno@acme.test"}, base=base)

    assert lookup.status_code == 200


async def test_a_password_link_tells_its_account_without_being_used(api, sender, db_session_factory):
    await sign_in(db_session_factory, email="sso@example.test")
    async with api() as client:
        await post(client, "/api/v1/auth/password/forgot", {"email": "sso@example.test"})
        token = sender.last_token("sso@example.test")
        info = await post(client, "/api/v1/auth/password/link", {"token": token})
        still_valid = await set_password(client, token, PASSWORD)

    assert info.json() == {"email": "sso@example.test", "kind": "set", "signs_in_with": None}
    assert still_valid.status_code == 204


async def test_an_organization_link_says_it_also_signs_in_with_its_sso(api, add_organization, db_session_factory):
    recorder = RecordingEmailSender()
    acme = await add_organization()
    async with db_session_factory() as session, session.begin():
        _, emails = await give_access(session, acme, email="viajero@acme.test", display_name="Viajero")
    token = emails[-1].token
    base = "http://acme.localhost"
    async with api(base) as client:
        info = await post(client, "/api/v1/auth/password/link", {"token": token}, base=base)

    assert info.json() == {"email": "viajero@acme.test", "kind": "set", "signs_in_with": "el SSO de Acme"}
    assert recorder.sent == []


async def test_a_used_password_link_says_so(api, sender, db_session_factory):
    await sign_in(db_session_factory, email="sso@example.test")
    async with api() as client:
        await post(client, "/api/v1/auth/password/forgot", {"email": "sso@example.test"})
        token = sender.last_token("sso@example.test")
        await set_password(client, token, PASSWORD)
        info = await post(client, "/api/v1/auth/password/link", {"token": token})

    assert info.status_code == 410
