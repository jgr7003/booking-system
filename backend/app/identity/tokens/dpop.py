"""DPoP proofs (RFC 9449): each request is signed with the device's private key.

The device keeps a non-extractable key pair and signs a short JWT for every request: method,
URL, time, a unique id and the hash of the access token. A token copied to another device is
useless without that key (03-usuarios-y-acceso.md §11).
"""

import base64
import hashlib
import logging
import time
from urllib.parse import urlsplit

from joserfc import jws, jwt
from joserfc.errors import JoseError
from joserfc.jwk import ECKey
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.identity.core.config import get_identity_settings
from app.identity.domain.errors.tokens import InvalidDpopProofError

logger = logging.getLogger(__name__)

# Proof JWTs are short; anything longer is refused before parsing.
MAX_PROOF_LENGTH = 4096

# Prefix of the Redis keys that remember the `jti` of recent proofs.
JTI_CACHE_PREFIX = "identity:v1:dpop-jti:"


def token_hash(access_token: str) -> str:
    """The `ath` claim: base64url of the SHA-256 of the access token, without padding.

    Args:
        access_token: The compact JWT.

    Returns:
        The hash, as it appears in the proof.
    """
    digest = hashlib.sha256(access_token.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _same_target(htu: str, host: str, path: str) -> bool:
    """Whether the `htu` of a proof names the request.

    Behind the development proxy the API sees another scheme and port than the browser used, so
    the comparison is on the installation host and the path (RFC 9449 allows ignoring the query
    and fragment).
    """
    try:
        parts = urlsplit(htu)
    except ValueError:
        return False
    return (parts.hostname or "").lower() == host and parts.path == path


async def verify_proof(
    proof: str | None,
    *,
    method: str,
    host: str,
    path: str,
    redis: Redis | None,
    access_token: str | None = None,
) -> str:
    """Checks a DPoP proof and returns the thumbprint of the key that signed it.

    Args:
        proof: Value of the `DPoP` header.
        method: HTTP method of the request.
        host: Host of the installation the request arrived at.
        path: Path of the request.
        redis: Where recent `jti` values are remembered to refuse replays; `None` skips the check.
        access_token: The access token sent with the request, if any; its hash must be in `ath`.

    Returns:
        The JWK SHA-256 thumbprint of the device key (`jkt`).

    Raises:
        InvalidDpopProofError: Missing, malformed, badly signed, stale, replayed or for another request.
    """
    if not proof or len(proof) > MAX_PROOF_LENGTH:
        raise InvalidDpopProofError("A valid DPoP proof is required.")
    settings = get_identity_settings()
    try:
        header = jws.extract_compact(proof.encode("ascii")).protected
        if header.get("typ") != "dpop+jwt" or header.get("alg") != "ES256":
            raise InvalidDpopProofError("The DPoP proof must be a dpop+jwt signed with ES256.")
        public_jwk = header.get("jwk")
        if not isinstance(public_jwk, dict) or "d" in public_jwk:
            raise InvalidDpopProofError("The DPoP proof must carry the device's public key.")
        key = ECKey.import_key(public_jwk)
        claims = jwt.decode(proof, key, algorithms=["ES256"]).claims
    except (JoseError, ValueError, UnicodeError) as exc:
        raise InvalidDpopProofError("The DPoP proof is not valid.") from exc

    iat = claims.get("iat")
    jti = claims.get("jti")
    if not isinstance(iat, int) or abs(time.time() - iat) > settings.dpop_max_age_s:
        raise InvalidDpopProofError("The DPoP proof is too old or from the future.")
    if not isinstance(jti, str) or not 8 <= len(jti) <= 128:
        raise InvalidDpopProofError("The DPoP proof needs a unique jti.")
    if claims.get("htm") != method or not _same_target(str(claims.get("htu", "")), host, path):
        raise InvalidDpopProofError("The DPoP proof is for another request.")
    if access_token is not None and claims.get("ath") != token_hash(access_token):
        raise InvalidDpopProofError("The DPoP proof is for another access token.")

    jkt = key.thumbprint()
    if redis is not None:
        await _refuse_replay(redis, jkt, jti, ttl_s=2 * settings.dpop_max_age_s)
    return jkt


async def _refuse_replay(redis: Redis, jkt: str, jti: str, ttl_s: int) -> None:
    """Remembers a proof's `jti` and refuses it if it was already seen.

    Without Redis the check is skipped with a warning: the short `iat` window still limits a replay.
    """
    try:
        first_time = await redis.set(f"{JTI_CACHE_PREFIX}{jkt}:{jti}", "1", nx=True, ex=ttl_s)
    except RedisError as exc:
        logger.warning("DPoP replay check skipped, Redis failed: %s", exc)
        return
    if not first_time:
        raise InvalidDpopProofError("The DPoP proof was already used.")
