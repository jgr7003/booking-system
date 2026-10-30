"""Argon2id password hashing with `pwdlib`."""

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher


class Argon2PasswordHasher:
    """Argon2id with the library's recommended parameters; old hashes are upgraded on sign in."""

    def __init__(self) -> None:
        """Initializes the hasher."""
        self._hash = PasswordHash((Argon2Hasher(),))

    def hash(self, password: str) -> str:
        """Hashes a password.

        Args:
            password: The password in clear.

        Returns:
            The Argon2id hash.
        """
        return self._hash.hash(password)

    def verify(self, password: str, password_hash: str) -> tuple[bool, str | None]:
        """Checks a password and upgrades its hash if the parameters changed.

        Args:
            password: The password typed by the user.
            password_hash: The stored hash.

        Returns:
            Whether it matches, and a new hash to store if it needs an upgrade.
        """
        return self._hash.verify_and_update(password, password_hash)
