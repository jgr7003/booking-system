"""Validated types of users."""

import re
from typing import Annotated

from pydantic import AfterValidator

from app.identity.domain.constants.users import PHONE_MAX_DIGITS, PHONE_MIN_DIGITS

# Something@something.tld, without spaces. The real check is the verification email.
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# `+`, country code and number: E.164 without separators.
_PHONE = re.compile(rf"^\+[1-9]\d{{{PHONE_MIN_DIGITS - 1},{PHONE_MAX_DIGITS - 1}}}$")


def _email(value: str) -> str:
    """Normalizes an email to lower case and checks its shape."""
    value = value.strip().lower()
    if len(value) > 254 or not _EMAIL.match(value):
        raise ValueError("Not a valid email address.")
    return value


def _phone_number(value: str) -> str:
    """Removes spaces, dashes and parentheses and checks the E.164 format."""
    value = re.sub(r"[\s\-()]", "", value)
    if not _PHONE.match(value):
        raise ValueError(
            f"Use the E.164 format, e.g. +573001234567 ({PHONE_MIN_DIGITS}-{PHONE_MAX_DIGITS} digits)."
        )
    return value


def _display_name(value: str) -> str:
    """Collapses spaces in a display name and checks its length."""
    value = " ".join(value.split())
    if not 1 <= len(value) <= 100:
        raise ValueError("The name must have between 1 and 100 characters.")
    return value


# Email address, in lower case.
Email = Annotated[str, AfterValidator(_email)]

# Name shown in the interface, with single spaces.
DisplayName = Annotated[str, AfterValidator(_display_name)]

# Phone number in E.164 format, e.g. `+573001234567`.
PhoneNumber = Annotated[str, AfterValidator(_phone_number)]
