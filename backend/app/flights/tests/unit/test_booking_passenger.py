from datetime import date

import pytest
from pydantic import ValidationError

from app.flights.domain.dtos.bookings import AirlinePassenger
from app.flights.domain.validators.passengers import age_on, to_airline_name
from app.flights.tests.support import make_booking_passenger


@pytest.mark.parametrize(
    ("typed", "sent"),
    [
        ("Muñoz", "MUNOZ"),
        ("José María", "JOSE MARIA"),
        ("  Ana   Lía ", "ANA LIA"),
        ("O’Brien", "O'BRIEN"),
        ("Müller-Lüdenscheidt", "MULLER-LUDENSCHEIDT"),
        ("Straße", "STRASSE"),
        ("Łukasz", "LUKASZ"),
    ],
)
def test_names_are_transliterated_to_what_airlines_accept(typed, sent):
    assert to_airline_name(typed) == sent


@pytest.mark.parametrize("name", ["Ana2", "李", "Ana_Lía", "-Ana", "Ana--Lía", "@"])
def test_names_airlines_cant_take_are_rejected(name):
    with pytest.raises(ValueError, match="only letters"):
        to_airline_name(name)


def test_given_and_family_names_together_are_at_most_40_characters():
    make_booking_passenger(given_name="A" * 20, family_name="B" * 20)

    with pytest.raises(ValidationError, match="40 characters"):
        make_booking_passenger(given_name="A" * 20, family_name="B" * 21)


def test_the_length_counts_the_transliterated_names():
    # "ß" becomes "SS": 20 + 20 typed characters are 41 for the airline.
    with pytest.raises(ValidationError, match="40 characters"):
        make_booking_passenger(given_name="A" * 20, family_name="ß" + "B" * 19)


def test_a_name_with_digits_is_rejected_before_reaching_the_airline():
    with pytest.raises(ValidationError, match="only letters"):
        make_booking_passenger(family_name="Prueba2")


def test_the_airline_passenger_is_a_fixed_copy_with_transliterated_names():
    passenger = make_booking_passenger(
        given_name="José",
        family_name="Muñoz",
        identity_documents=[{"number": "AB1234567", "issuing_country_code": "AR", "expires_on": "2032-01-01"}],
    )

    airline = AirlinePassenger.from_booking(passenger)

    assert (airline.given_name, airline.family_name) == ("JOSE", "MUNOZ")
    assert airline.title == "ms"
    assert airline.passport.number == "AB1234567"


@pytest.mark.parametrize(
    ("born_on", "day", "age"),
    [
        (date(2008, 12, 15), date(2026, 12, 15), 18),
        (date(2008, 12, 16), date(2026, 12, 15), 17),
        (date(2008, 2, 29), date(2026, 2, 28), 17),
        (date(2008, 2, 29), date(2026, 3, 1), 18),
    ],
)
def test_age_on_a_day(born_on, day, age):
    assert age_on(born_on, day) == age
