"""Validated types of passwords and links."""

from typing import Annotated

from pydantic import AfterValidator, StringConstraints

from app.identity.domain.constants.passwords import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH


def _new_password(value: str) -> str:
    """Checks a password being chosen: only its length, as NIST recommends."""
    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"The password must have at least {MIN_PASSWORD_LENGTH} characters.")
    if not value.strip():
        raise ValueError("The password can't be only spaces.")
    return value


# A password the user is choosing (sign up, set or reset).
NewPassword = Annotated[str, StringConstraints(max_length=MAX_PASSWORD_LENGTH), AfterValidator(_new_password)]

# A password typed to sign in; never validated beyond its size, so old passwords keep working.
GivenPassword = Annotated[str, StringConstraints(min_length=1, max_length=MAX_PASSWORD_LENGTH)]

# A token from an email link.
LinkToken = Annotated[str, StringConstraints(min_length=20, max_length=200)]
