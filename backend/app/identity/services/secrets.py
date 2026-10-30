"""Encryption of the client secrets of identity providers stored in the database."""

from cryptography.fernet import Fernet, InvalidToken

from app.identity.core.config import get_identity_settings
from app.identity.domain.errors.oidc import SecretsKeyMissingError


def _fernet() -> Fernet:
    """The cipher of the configured key."""
    key = get_identity_settings().identity_secrets_key
    if key is None:
        raise SecretsKeyMissingError("IDENTITY_SECRETS_KEY is not set; generate one with `make auth-keygen`.")
    return Fernet(key.get_secret_value().encode("ascii"))


def generate_secrets_key() -> str:
    """Creates a new key for `IDENTITY_SECRETS_KEY`.

    Returns:
        A Fernet key.
    """
    return Fernet.generate_key().decode("ascii")


def encrypt_secret(secret: str) -> bytes:
    """Encrypts a secret to store it.

    Args:
        secret: The secret in clear.

    Returns:
        The encrypted secret.
    """
    return _fernet().encrypt(secret.encode("utf-8"))


def decrypt_secret(encrypted: bytes) -> str:
    """Decrypts a stored secret.

    Args:
        encrypted: The encrypted secret.

    Returns:
        The secret in clear.

    Raises:
        SecretsKeyMissingError: The key isn't configured or isn't the one that encrypted it.
    """
    try:
        return _fernet().decrypt(encrypted).decode("utf-8")
    except InvalidToken as exc:
        raise SecretsKeyMissingError("IDENTITY_SECRETS_KEY is not the key that encrypted this secret.") from exc
