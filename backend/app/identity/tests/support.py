"""A fake OIDC provider for the tests, served by `httpx2.MockTransport`. No test reaches a real one."""

import base64
import hashlib
import json
import secrets
import time
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx2
from joserfc import jwt
from joserfc.jwk import KeySet, RSAKey

from app.identity.testing import DeviceKey

# Issuer of the fake provider.
ISSUER = "https://idp.test/realms/test"

# Client registered at the fake provider.
CLIENT_ID = "booking-test"
CLIENT_SECRET = "secret-de-prueba"


class FakeIdp:
    """Discovery, keys and a token endpoint that checks PKCE, like a real provider.

    `sign_in(authorization_url, **claims)` plays the person signing in at the provider: it
    returns the `code` and `state` the provider would put in the redirect.
    """

    def __init__(self) -> None:
        """Creates the provider with one signing key."""
        self.key = RSAKey.generate_key(2048, parameters={"kid": "k1"}, private=True)
        self.codes: dict[str, dict[str, Any]] = {}
        self.token_requests = 0
        self.jwks_requests = 0
        self.discovery = {
            "issuer": ISSUER,
            "authorization_endpoint": f"{ISSUER}/auth",
            "token_endpoint": f"{ISSUER}/token",
            "jwks_uri": f"{ISSUER}/certs",
        }

    def rotate_key(self) -> None:
        """Replaces the signing key, as a provider does from time to time."""
        self.key = RSAKey.generate_key(2048, parameters={"kid": "k2"}, private=True)

    def sign_in(self, authorization_url: str, **claims: Any) -> tuple[str, str]:
        """The person signs in at the provider.

        Args:
            authorization_url: URL the platform sent the browser to.
            **claims: Claims of the id_token to replace (`sub`, `email`, `email_verified`...).

        Returns:
            `(code, state)` of the redirect back to the platform.
        """
        query = {k: v[0] for k, v in parse_qs(urlsplit(authorization_url).query).items()}
        assert query["code_challenge_method"] == "S256"
        code = secrets.token_urlsafe(16)
        self.codes[code] = {
            "challenge": query["code_challenge"],
            "redirect_uri": query["redirect_uri"],
            "claims": {
                "iss": ISSUER,
                "aud": CLIENT_ID,
                "sub": "sub-ana",
                "email": "ana@example.test",
                "email_verified": True,
                "name": "Ana Proveedor",
                "nonce": query["nonce"],
                "iat": int(time.time()),
                "exp": int(time.time()) + 300,
            }
            | claims,
        }
        return code, query["state"]

    def handler(self, request: httpx2.Request) -> httpx2.Response:
        """`MockTransport` handler of the provider's endpoints."""
        url = str(request.url)
        if url == f"{ISSUER}/.well-known/openid-configuration":
            return httpx2.Response(200, json=self.discovery)
        if url == f"{ISSUER}/certs":
            self.jwks_requests += 1
            return httpx2.Response(200, json=KeySet([self.key]).as_dict(private=False))
        if url == f"{ISSUER}/token" and request.method == "POST":
            return self._token(request)
        raise AssertionError(f"Unexpected request to the fake provider: {request.method} {url}")

    def _token(self, request: httpx2.Request) -> httpx2.Response:
        """Token endpoint: checks client credentials, the code and the PKCE verifier."""
        self.token_requests += 1
        expected = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
        if request.headers.get("authorization") != f"Basic {expected}":
            return httpx2.Response(401, json={"error": "invalid_client"})
        form = {k: v[0] for k, v in parse_qs(request.content.decode()).items()}
        grant = self.codes.pop(form.get("code", ""), None)
        if grant is None or form.get("redirect_uri") != grant["redirect_uri"]:
            return httpx2.Response(400, json={"error": "invalid_grant"})
        digest = hashlib.sha256(form.get("code_verifier", "").encode()).digest()
        if base64.urlsafe_b64encode(digest).rstrip(b"=").decode() != grant["challenge"]:
            return httpx2.Response(400, json={"error": "invalid_grant", "error_description": "PKCE"})
        id_token = jwt.encode({"alg": "RS256", "kid": self.key.kid}, grant["claims"], self.key)
        return httpx2.Response(200, content=json.dumps({"id_token": id_token, "access_token": "x"}))


async def authorize(
    client: httpx2.AsyncClient, device: DeviceKey, base: str = "http://test", slug: str = "test-idp", **body: Any
) -> httpx2.Response:
    """Starts a sign in through a provider from a device (`POST /auth/oidc/{slug}/authorize`).

    Args:
        client: HTTP client of the app.
        device: Device that starts it.
        base: Base URL of the installation.
        slug: Provider.
        **body: Body fields, e.g. `return_to`.

    Returns:
        The response.
    """
    path = f"/api/v1/auth/oidc/{slug}/authorize"
    return await client.post(path, json=body, headers=device.headers("POST", f"{base}{path}"))


async def callback(
    client: httpx2.AsyncClient,
    device: DeviceKey,
    code: str,
    state: str,
    base: str = "http://test",
    slug: str = "test-idp",
) -> httpx2.Response:
    """Finishes a sign in from a device (`POST /auth/oidc/{slug}/callback`).

    Args:
        client: HTTP client of the app.
        device: Device that finishes it.
        code: Code from the provider's redirect.
        state: State from the provider's redirect.
        base: Base URL of the installation.
        slug: Provider.

    Returns:
        The response.
    """
    path = f"/api/v1/auth/oidc/{slug}/callback"
    return await client.post(path, json={"code": code, "state": state}, headers=device.headers("POST", f"{base}{path}"))


def assert_refused(response: httpx2.Response, caplog: Any, reason: str) -> None:
    """The sign in failed with the one answer that says nothing, and the real reason was logged.

    Args:
        response: The response of the sign in.
        caplog: Pytest's log capture.
        reason: Reason expected in the log, e.g. `wrong_password`.
    """
    assert response.status_code == 401
    assert response.json()["error"] == {"code": "login_failed", "message": "We couldn't sign you in."}
    assert f"reason={reason}" in caplog.text
