"""Access tokens of the platform: JWTs signed with ES256 and bound to the device key (`cnf.jkt`).

Signed is not encrypted: anyone holding a token can read its claims. They carry only what the
user may see (03-usuarios-y-acceso.md §10.1).
"""

import json
import time
import uuid
from functools import lru_cache
from typing import Any

from joserfc import jwt
from joserfc.errors import BadSignatureError, DecodeError, ExpiredTokenError, JoseError
from joserfc.jwk import ECKey, KeySet

from app.identity.core.config import get_identity_settings
from app.identity.domain.dtos.tokens import AccessTokenClaims
from app.identity.domain.errors.tokens import InvalidTokenError, SigningKeyMissingError, TokenExpiredError

# The only algorithm the platform signs with and accepts (decision 52).
ALGORITHM = "ES256"


def generate_signing_key(kid: str) -> dict[str, Any]:
    """Creates a new private signing key.

    Args:
        kid: Id of the key, published in the JWKS and in the header of each token.

    Returns:
        The private key as a JWK.
    """
    return ECKey.generate_key("P-256", parameters={"kid": kid}, private=True).as_dict(private=True)


@lru_cache
def _load_keys(raw: str) -> KeySet:
    """Parses the configured keys once per value."""
    keys = [ECKey.import_key(jwk) for jwk in json.loads(raw)]
    if not keys or any(not key.kid for key in keys):
        raise SigningKeyMissingError("AUTH_SIGNING_KEYS must list at least one key, each with its kid.")
    return KeySet(keys)


def signing_keys() -> KeySet:
    """The configured keys; the first one signs.

    Returns:
        The key set.

    Raises:
        SigningKeyMissingError: `AUTH_SIGNING_KEYS` is not set.
    """
    raw = get_identity_settings().auth_signing_keys
    if raw is None:
        raise SigningKeyMissingError("AUTH_SIGNING_KEYS is not set; generate one with `make auth-keygen`.")
    return _load_keys(raw.get_secret_value())


def public_jwks() -> dict[str, Any]:
    """The public keys, to publish at `/auth/jwks.json`.

    Returns:
        A JWKS document without private parts.
    """
    keys = signing_keys().as_dict(private=False)["keys"]
    return {"keys": [key | {"use": "sig", "alg": ALGORITHM} for key in keys]}


def issue_access_token(claims: AccessTokenClaims) -> str:
    """Signs an access token with the active key.

    Args:
        claims: What the token says.

    Returns:
        The compact JWT.
    """
    key = signing_keys().keys[0]
    payload = claims.model_dump(mode="json", by_alias=True)
    return jwt.encode({"alg": ALGORITHM, "typ": "at+jwt", "kid": key.kid}, payload, key)


def new_access_claims(
    *,
    issuer: str,
    user_id: uuid.UUID,
    organization_id: uuid.UUID | None,
    session_id: uuid.UUID,
    name: str,
    email: str,
    language: str | None,
    jkt: str,
) -> AccessTokenClaims:
    """Builds the claims of a new access token, valid from now on.

    Args:
        issuer: Host of the installation that issues it.
        user_id: The user.
        organization_id: Organization of the user; `None` for private travellers.
        session_id: Device session.
        name: Display name.
        email: Email.
        language: Language the user chose, if any.
        jkt: Thumbprint of the device key.

    Returns:
        The claims.
    """
    settings = get_identity_settings()
    now = int(time.time())
    return AccessTokenClaims.model_validate(
        {
            "iss": issuer,
            "aud": settings.auth_audience,
            "sub": user_id,
            "org": organization_id,
            "sid": session_id,
            "iat": now,
            "exp": now + settings.access_token_ttl_s,
            "jti": uuid.uuid4(),
            "name": name,
            "email": email,
            "lang": language,
            "cnf": {"jkt": jkt},
        }
    )


def read_access_token(token: str, *, verify_expiry: bool = True) -> AccessTokenClaims:
    """Checks the signature of an access token and reads its claims.

    The issuer and the organization are checked by the caller, against the installation of the
    request.

    Args:
        token: The compact JWT.
        verify_expiry: `False` reads an expired token too; used only to revoke the session of a
            token presented without its device key.

    Returns:
        The claims.

    Raises:
        InvalidTokenError: Malformed, unknown key, bad signature or wrong audience.
        TokenExpiredError: The token expired.
    """
    try:
        decoded = jwt.decode(token, signing_keys(), algorithms=[ALGORITHM])
        if decoded.header.get("typ") != "at+jwt":
            raise InvalidTokenError("Not an access token.")
        registry = jwt.JWTClaimsRegistry(
            leeway=0,
            aud={"essential": True, "value": get_identity_settings().auth_audience},
            exp={"essential": True},
            sub={"essential": True},
        )
        if verify_expiry:
            registry.validate(decoded.claims)
        else:
            registry.validate_aud(decoded.claims.get("aud"))
        return AccessTokenClaims.model_validate(decoded.claims)
    except ExpiredTokenError as exc:
        raise TokenExpiredError("The access token expired.") from exc
    except (BadSignatureError, DecodeError, JoseError, ValueError) as exc:
        raise InvalidTokenError("The access token is not valid.") from exc
