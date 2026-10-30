"""Ports of the identity module."""

from typing import Protocol


class PasswordHasher(Protocol):
    """Turns passwords into slow, salted hashes and checks them."""

    def hash(self, password: str) -> str:
        """Hashes a password.

        Args:
            password: The password in clear.

        Returns:
            The hash, with its algorithm and parameters.
        """
        ...

    def verify(self, password: str, password_hash: str) -> tuple[bool, str | None]:
        """Checks a password against its hash.

        Args:
            password: The password typed by the user.
            password_hash: The stored hash.

        Returns:
            Whether it matches, and a new hash when the stored one uses old parameters (to save it).
        """
        ...
