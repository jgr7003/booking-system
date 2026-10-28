from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from app.travellers.public import IdentityDocumentDetails, IdentityDocumentType, TravellerDetails


def details(**overrides) -> dict:
    """Valid personal data, with the given fields replaced.

    Args:
        **overrides: Fields to replace.

    Returns:
        The data, ready for `TravellerDetails.model_validate`.
    """
    return {
        "given_name": "Ana",
        "family_name": "Prueba",
        "born_on": "1990-05-20",
        "gender": "f",
        "email": "ana.prueba@example.com",
        "phone_number": "+5491112345678",
    } | overrides


def passport(**overrides) -> dict:
    """A valid passport, with the given fields replaced.

    Args:
        **overrides: Fields to replace.

    Returns:
        The data of the document.
    """
    return {"number": "AB1234567", "issuing_country_code": "AR", "expires_on": "2032-01-01"} | overrides


def test_normalizes_names_email_phone_and_document():
    traveller = TravellerDetails.model_validate(
        details(
            given_name="  Ana   María ",
            email=" Ana.Prueba@Example.COM ",
            phone_number="+54 9 11 1234-5678",
            identity_documents=[passport(number="ab-123 4567", issuing_country_code="ar")],
        )
    )

    assert traveller.given_name == "Ana María"
    assert traveller.email == "ana.prueba@example.com"
    assert traveller.phone_number == "+5491112345678"
    document = traveller.document(IdentityDocumentType.PASSPORT)
    assert document == IdentityDocumentDetails(number="AB1234567", issuing_country_code="AR", expires_on=date(2032, 1, 1))


def test_keeps_accents_because_transliteration_is_a_rule_of_each_vertical():
    assert TravellerDetails.model_validate(details(family_name="Muñoz")).family_name == "Muñoz"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("given_name", "   "),
        ("family_name", "x" * 61),
        ("email", "ana@example"),
        ("phone_number", "1112345678"),
        ("phone_number", "+0123456789"),
        ("phone_number", "+54911"),
        ("born_on", date.today().isoformat()),
        ("gender", "x"),
    ],
)
def test_rejects_invalid_personal_data(field, value):
    with pytest.raises(ValidationError) as error:
        TravellerDetails.model_validate(details(**{field: value}))
    assert error.value.errors()[0]["loc"][0] == field


@pytest.mark.parametrize(
    "document",
    [
        passport(expires_on=date.today().isoformat()),
        passport(expires_on=(date.today() - timedelta(days=1)).isoformat()),
        passport(issuing_country_code="ARG"),
        passport(number="AB/12"),
    ],
)
def test_rejects_invalid_or_expired_passports(document):
    with pytest.raises(ValidationError):
        TravellerDetails.model_validate(details(identity_documents=[document]))


def test_rejects_two_documents_of_the_same_type():
    with pytest.raises(ValidationError, match="at most one identity document"):
        TravellerDetails.model_validate(details(identity_documents=[passport(), passport(number="ZZ999")]))
