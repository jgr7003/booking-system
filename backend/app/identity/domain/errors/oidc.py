"""Errors of sign in through an OIDC provider."""

from app.core.errors import AppError


class UnknownProviderError(AppError):
    """The installation has no enabled provider with that name. Answered as HTTP 404."""

    code = "provider_not_found"


class InvalidLoginAttemptError(AppError):
    """The `state` or attempt is unknown, expired, already used or from another device. Answered as HTTP 400."""

    code = "invalid_login_attempt"


class IdentityProviderError(AppError):
    """The provider didn't answer as expected (discovery, code exchange, keys). Answered as HTTP 502."""

    code = "identity_provider_error"


class InvalidIdentityError(AppError):
    """The id_token didn't pass the checks, or the provider didn't verify the email. Answered as HTTP 401."""

    code = "invalid_identity"


class SignupNotAllowedError(AppError):
    """Accounts can't be created from the sign in here (organizations create their users). Answered as HTTP 403."""

    code = "signup_not_allowed"


class SecretsKeyMissingError(AppError):
    """`IDENTITY_SECRETS_KEY` is not configured: provider secrets can't be read. Answered as HTTP 500."""

    code = "secrets_key_missing"
