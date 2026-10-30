"""HTTP status codes of the identity errors."""

from fastapi import FastAPI

from app.core.errors import add_error_handlers
from app.identity.domain.errors.oidc import (
    IdentityProviderError,
    InvalidIdentityError,
    InvalidLoginAttemptError,
    SecretsKeyMissingError,
    SignupNotAllowedError,
    UnknownProviderError,
)
from app.identity.domain.errors.passwords import (
    InvalidLinkError,
    LoginFailedError,
    PasswordLoginDisabledError,
    TooManyAttemptsError,
)
from app.identity.domain.errors.sessions import DeviceSessionNotFoundError
from app.identity.domain.errors.tokens import (
    AuthenticationRequiredError,
    InvalidDpopProofError,
    InvalidTokenError,
    SessionExpiredError,
    SessionRevokedError,
    SigningKeyMissingError,
    TokenBindingMismatchError,
    TokenExpiredError,
)
from app.identity.domain.errors.users import UserAlreadyExistsError


def register_identity_error_handlers(app: FastAPI) -> None:
    """Registers how identity errors are answered over HTTP.

    Args:
        app: The FastAPI application.
    """
    add_error_handlers(
        app,
        {
            AuthenticationRequiredError: 401,
            InvalidTokenError: 401,
            TokenExpiredError: 401,
            InvalidDpopProofError: 401,
            TokenBindingMismatchError: 401,
            SessionRevokedError: 401,
            SessionExpiredError: 401,
            SigningKeyMissingError: 500,
            DeviceSessionNotFoundError: 404,
            UserAlreadyExistsError: 409,
            PasswordLoginDisabledError: 404,
            LoginFailedError: 401,
            InvalidLinkError: 410,
            TooManyAttemptsError: 429,
            UnknownProviderError: 404,
            InvalidLoginAttemptError: 400,
            IdentityProviderError: 502,
            InvalidIdentityError: 401,
            SignupNotAllowedError: 403,
            SecretsKeyMissingError: 500,
        },
    )
