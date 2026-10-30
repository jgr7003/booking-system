"""Errors of access tokens, DPoP proofs and device sessions. All are answered as HTTP 401."""

from app.core.errors import AppError


class AuthenticationRequiredError(AppError):
    """The request has no `Authorization` header and the endpoint needs a session."""

    code = "authentication_required"


class InvalidTokenError(AppError):
    """The access or refresh token is malformed, badly signed, unknown or from another installation."""

    code = "invalid_token"


class TokenExpiredError(AppError):
    """The access token expired: the client refreshes it and retries."""

    code = "token_expired"


class InvalidDpopProofError(AppError):
    """The DPoP proof is missing a claim, stale, replayed or for another request. The session stays."""

    code = "invalid_dpop_proof"


class TokenBindingMismatchError(AppError):
    """The token was used without the key of its device: the session was revoked."""

    code = "token_binding_mismatch"


class SessionRevokedError(AppError):
    """The device session was closed: by the user, a password change or a theft check."""

    code = "session_revoked"


class SigningKeyMissingError(AppError):
    """`AUTH_SIGNING_KEYS` is not configured: the platform can't sign tokens."""

    code = "signing_key_missing"


class SessionExpiredError(AppError):
    """The device session ended because it wasn't used for long, or reached its maximum lifetime."""

    code = "session_expired"
