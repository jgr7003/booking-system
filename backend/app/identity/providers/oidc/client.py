"""OIDC client (Relying Party) for Authorization Code + PKCE, written on `httpx2`.

The browser goes to the provider and comes back with a `code`; the backend exchanges it with its
`client_secret` and the PKCE verifier, which never left the server, and checks the id_token
(03-usuarios-y-acceso.md §7). Tokens of the provider are not kept: only who the person is.
"""

import base64
import hashlib
import logging
import secrets
from typing import Any
from urllib.parse import urlencode, urlsplit

import httpx2
from joserfc import jwt
from joserfc.errors import JoseError
from joserfc.jwk import KeySet
from redis.asyncio import Redis

from app.core.cache import JsonCache
from app.identity.core.config import get_identity_settings
from app.identity.domain.dtos.oidc import ProviderConfig, VerifiedIdentity
from app.identity.domain.errors.oidc import IdentityProviderError, InvalidIdentityError

logger = logging.getLogger(__name__)

# Prefix of the Redis keys of discovery documents and key sets.
OIDC_CACHE_PREFIX = "identity:v1:oidc:"

# Asymmetric algorithms accepted for id_tokens. `none` and the HMAC ones are never accepted.
ACCEPTED_ALGORITHMS = ["RS256", "RS384", "RS512", "PS256", "PS384", "PS512", "ES256", "ES384", "EdDSA"]

# Seconds of clock difference tolerated with the provider.
CLOCK_LEEWAY_S = 60


def new_pkce_pair() -> tuple[str, str]:
    """Creates a PKCE verifier and its `S256` challenge (RFC 7636).

    Returns:
        `(code_verifier, code_challenge)`.
    """
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return verifier, base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


class OidcClient:
    """Talks to OIDC providers. Discovery documents and keys are cached in Redis."""

    def __init__(self, http: httpx2.AsyncClient, redis: Redis | None) -> None:
        """Initializes the client.

        Args:
            http: Shared HTTP client.
            redis: Redis client for the cache; `None` asks the provider every time.
        """
        self._http = http
        self._cache = JsonCache(redis) if redis is not None else None

    def _backchannel(self, provider: ProviderConfig, url: str) -> str:
        """URL for a server-to-server call: the provider's host replaced by its backchannel base, if any."""
        if not provider.backchannel_base_url:
            return url
        public, target = urlsplit(provider.issuer), urlsplit(url)
        if (target.scheme, target.netloc) != (public.scheme, public.netloc):
            return url
        return provider.backchannel_base_url.rstrip("/") + url[len(f"{public.scheme}://{public.netloc}") :]

    async def _get_json(self, url: str) -> dict[str, Any]:
        """GETs a JSON document from the provider."""
        try:
            response = await self._http.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except (httpx2.HTTPError, ValueError) as exc:
            logger.warning("Identity provider request failed: GET %s: %s", url, exc)
            raise IdentityProviderError("The identity provider is not answering.") from exc

    async def _cached(self, key: str, url: str, *, refresh: bool = False) -> dict[str, Any]:
        """Reads a document through the cache."""
        if self._cache is not None and not refresh:
            cached = await self._cache.get(key)
            if cached is not None:
                return cached
        document = await self._get_json(url)
        if self._cache is not None:
            await self._cache.set(key, document, get_identity_settings().oidc_cache_ttl_s)
        return document

    async def discover(self, provider: ProviderConfig) -> dict[str, Any]:
        """Reads the provider's discovery document (`/.well-known/openid-configuration`).

        Args:
            provider: The provider.

        Returns:
            The document.

        Raises:
            IdentityProviderError: The provider didn't answer, or its document names another issuer.
        """
        url = self._backchannel(provider, provider.issuer.rstrip("/") + "/.well-known/openid-configuration")
        document = await self._cached(f"{OIDC_CACHE_PREFIX}discovery:{provider.issuer}", url)
        if document.get("issuer") != provider.issuer:
            raise IdentityProviderError("The identity provider's discovery names another issuer.")
        return document

    async def authorization_url(
        self,
        provider: ProviderConfig,
        *,
        redirect_uri: str,
        state: str,
        nonce: str,
        code_challenge: str,
        prompt: str | None = None,
    ) -> str:
        """Builds the URL the browser opens to sign in at the provider.

        Args:
            provider: The provider.
            redirect_uri: Where the provider sends the browser back.
            state: Random value the provider returns, to find the attempt.
            nonce: Random value the provider puts in the id_token.
            code_challenge: PKCE `S256` challenge.
            prompt: `prompt` of this request, e.g. `login` to choose another account; it replaces the
                provider's default.

        Returns:
            The URL of the provider's authorization endpoint.
        """
        document = await self.discover(provider)
        params = {
            "response_type": "code",
            "client_id": provider.client_id,
            "redirect_uri": redirect_uri,
            "scope": provider.scopes,
            "state": state,
            "nonce": nonce,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        } | provider.extra_authorize_params
        if prompt:
            params["prompt"] = prompt
        return f"{document['authorization_endpoint']}?{urlencode(params)}"

    async def exchange_code(
        self, provider: ProviderConfig, *, code: str, code_verifier: str, redirect_uri: str
    ) -> str:
        """Exchanges the authorization code for the id_token.

        Args:
            provider: The provider.
            code: Authorization code from the redirect.
            code_verifier: PKCE verifier of the attempt.
            redirect_uri: The same `redirect_uri` of the authorization request.

        Returns:
            The id_token, not checked yet.

        Raises:
            IdentityProviderError: The provider refused the code or didn't send an id_token.
        """
        document = await self.discover(provider)
        url = self._backchannel(provider, document["token_endpoint"])
        try:
            response = await self._http.post(
                url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "code_verifier": code_verifier,
                },
                auth=(provider.client_id, provider.client_secret.get_secret_value()),
                headers={"Accept": "application/json"},
                timeout=15,
            )
        except httpx2.HTTPError as exc:
            raise IdentityProviderError("The identity provider is not answering.") from exc
        if response.status_code != 200:
            # The body says why (`invalid_grant`...); it never carries secrets of ours.
            logger.warning("Code exchange refused by %s: %s %s", provider.slug, response.status_code, response.text[:300])
            raise IdentityProviderError("The identity provider refused the sign in. Try again.")
        id_token = response.json().get("id_token")
        if not isinstance(id_token, str):
            raise IdentityProviderError("The identity provider didn't send an id_token.")
        return id_token

    async def _keys(self, provider: ProviderConfig, *, refresh: bool = False) -> KeySet:
        """The provider's public keys."""
        document = await self.discover(provider)
        url = self._backchannel(provider, document["jwks_uri"])
        jwks = await self._cached(f"{OIDC_CACHE_PREFIX}jwks:{provider.issuer}", url, refresh=refresh)
        try:
            return KeySet.import_key_set(jwks)
        except (JoseError, ValueError) as exc:
            raise IdentityProviderError("The identity provider's keys can't be read.") from exc

    async def verify_id_token(self, provider: ProviderConfig, id_token: str, *, nonce: str) -> VerifiedIdentity:
        """Checks an id_token and reads who the person is.

        If no cached key fits, the keys are read again once: the provider may have rotated them.

        Args:
            provider: The provider.
            id_token: The id_token from the code exchange.
            nonce: `nonce` of the attempt.

        Returns:
            The verified identity.

        Raises:
            InvalidIdentityError: Bad signature, wrong issuer, audience or nonce, expired, or an
                email the provider didn't verify.
        """
        try:
            decoded = jwt.decode(id_token, await self._keys(provider), algorithms=ACCEPTED_ALGORITHMS)
        except JoseError:
            try:
                decoded = jwt.decode(id_token, await self._keys(provider, refresh=True), algorithms=ACCEPTED_ALGORITHMS)
            except (JoseError, ValueError) as exc:
                raise InvalidIdentityError("The identity provider's answer is not valid.") from exc
        except ValueError as exc:
            raise InvalidIdentityError("The identity provider's answer is not valid.") from exc

        claims = decoded.claims
        registry = jwt.JWTClaimsRegistry(
            leeway=CLOCK_LEEWAY_S,
            iss={"essential": True, "value": provider.issuer},
            aud={"essential": True, "value": provider.client_id},
            sub={"essential": True},
            exp={"essential": True},
            nonce={"essential": True, "value": nonce},
        )
        try:
            registry.validate(claims)
        except JoseError as exc:
            raise InvalidIdentityError("The identity provider's answer is not valid.") from exc
        audiences = claims["aud"] if isinstance(claims["aud"], list) else [claims["aud"]]
        if len(audiences) > 1 and claims.get("azp") != provider.client_id:
            raise InvalidIdentityError("The identity provider's answer is for another client.")

        email = claims.get("email")
        if not isinstance(email, str) or "@" not in email:
            raise InvalidIdentityError("The identity provider didn't share the email.")
        if claims.get("email_verified") is not True and not provider.trust_email:
            raise InvalidIdentityError("The identity provider didn't verify the email.")
        return VerifiedIdentity(
            subject=str(claims["sub"]), email=email.strip().lower(), display_name=_display_name(claims)
        )


def _display_name(claims: dict[str, Any]) -> str:
    """The name the provider gave (`name`, or given and family names), falling back to the email."""
    name = claims.get("name") or " ".join(p for p in (claims.get("given_name"), claims.get("family_name")) if p)
    return (name or str(claims.get("email", ""))).strip()[:100]
