"""Validation rules of a traveller's personal data, valid for every vertical.

Rules that belong to a vertical (an airline's alphabet for names, the age of an adult on the day
of the flight...) live in that vertical, not here.
"""

import re
from datetime import date
from typing import Annotated

from pydantic import AfterValidator, Field

from app.travellers.domain.constants import (
    MAX_DOCUMENT_NUMBER_LENGTH,
    MAX_NAME_LENGTH,
    PHONE_MAX_DIGITS,
    PHONE_MIN_DIGITS,
)

# Deliberately loose: the address is confirmed by actually writing to it, not by a regex.
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_PHONE = re.compile(rf"^\+[1-9]\d{{{PHONE_MIN_DIGITS - 1},{PHONE_MAX_DIGITS - 1}}}$")

_DOCUMENT_NUMBER = re.compile(rf"^[A-Z0-9]{{1,{MAX_DOCUMENT_NUMBER_LENGTH}}}$")


def _person_name(value: str) -> str:
    """Collapses inner spaces and rejects blank names."""
    value = " ".join(value.split())
    if not value:
        raise ValueError("must not be blank")
    return value


def _email(value: str) -> str:
    """Normalizes an email to lower case and checks its shape."""
    value = value.strip().lower()
    if not _EMAIL.match(value):
        raise ValueError("must be a valid email address")
    return value


def _phone_number(value: str) -> str:
    """Removes spaces, dashes and parentheses and checks the E.164 format."""
    value = re.sub(r"[\s\-()]", "", value)
    if not _PHONE.match(value):
        raise ValueError(f"must be in international E.164 format, e.g. +5491112345678 ({PHONE_MIN_DIGITS}-{PHONE_MAX_DIGITS} digits)")
    return value


def _country_code(value: str) -> str:
    """Normalizes an ISO 3166-1 alpha-2 code to upper case."""
    value = value.strip().upper()
    if len(value) != 2 or not value.isalpha():
        raise ValueError("must be an ISO 3166-1 alpha-2 country code, e.g. AR")
    return value


def _document_number(value: str) -> str:
    """Removes spaces and dashes and checks the characters of a document number."""
    value = re.sub(r"[\s\-]", "", value).upper()
    if not _DOCUMENT_NUMBER.match(value):
        raise ValueError(f"must have only letters and digits, up to {MAX_DOCUMENT_NUMBER_LENGTH}")
    return value


def _in_the_past(value: date) -> date:
    """Rejects dates from today on."""
    if value >= date.today():
        raise ValueError("must be in the past")
    return value


def _in_the_future(value: date) -> date:
    """Rejects dates up to today."""
    if value <= date.today():
        raise ValueError("must be in the future")
    return value


# Given or family name, with its spaces collapsed.
PersonName = Annotated[str, Field(max_length=MAX_NAME_LENGTH), AfterValidator(_person_name)]

# Email address, in lower case.
Email = Annotated[str, AfterValidator(_email)]

# Phone number in E.164 format, e.g. `+5491112345678`.
PhoneNumber = Annotated[str, AfterValidator(_phone_number)]

# ISO 3166-1 alpha-2 country code, in upper case.
CountryCode = Annotated[str, AfterValidator(_country_code)]

# Number of an identity document, in upper case without separators.
DocumentNumber = Annotated[str, AfterValidator(_document_number)]

# A date of birth.
BirthDate = Annotated[date, AfterValidator(_in_the_past)]

# The expiry date of a document that is still valid.
ExpiryDate = Annotated[date, AfterValidator(_in_the_future)]
