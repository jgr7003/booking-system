"""Rules airlines impose on a passenger: name alphabet and length, and age."""

import re
import unicodedata
from datetime import date

from app.flights.domain.constants.bookings import MAX_PASSENGER_NAME_LENGTH


# Letters that don't decompose into an ASCII letter plus accents.
_TRANSLITERATIONS = str.maketrans(
    {
        "ß": "SS", "Æ": "AE", "æ": "AE", "Ø": "O", "ø": "O", "Œ": "OE", "œ": "OE", "Đ": "D", "đ": "D",
        "Ð": "D", "ð": "D", "Ł": "L", "ł": "L", "Þ": "TH", "þ": "TH", "ı": "I", "’": "'", "‘": "'",
    }
)  # fmt: skip


# What airlines accept in a name: words of letters joined by a space, a hyphen or an apostrophe.
_AIRLINE_NAME = re.compile(r"^[A-Z]+(?:[ '\-][A-Z]+)*$")


def to_airline_name(name: str) -> str:
    """Transliterates a name to what airlines accept: upper-case ASCII letters, spaces, `-` and `'`.

    Accents and the ñ are removed (`Muñoz` → `MUNOZ`); the frontend warns about it before sending.

    Args:
        name: The name as typed.

    Returns:
        The name as it goes to the airline.

    Raises:
        ValueError: The name has characters that can't be transliterated, such as digits or
            letters of a non-Latin script.
    """
    decomposed = unicodedata.normalize("NFKD", name.translate(_TRANSLITERATIONS))
    result = " ".join("".join(c for c in decomposed if not unicodedata.combining(c)).upper().split())
    if not _AIRLINE_NAME.match(result):
        raise ValueError("must contain only letters, spaces, hyphens (-) or apostrophes (')")
    return result


def validate_airline_name_length(given_name: str, family_name: str) -> None:
    """Validates the length airlines accept for a passenger's names.

    Args:
        given_name: Given name, already transliterated.
        family_name: Family name, already transliterated.

    Raises:
        ValueError: Both names together are longer than `MAX_PASSENGER_NAME_LENGTH`.
    """
    if len(given_name) + len(family_name) > MAX_PASSENGER_NAME_LENGTH:
        raise ValueError(f"given and family names together can't exceed {MAX_PASSENGER_NAME_LENGTH} characters")


def age_on(born_on: date, day: date) -> int:
    """Calculates the age a person has on a day.

    Args:
        born_on: Date of birth.
        day: Day of the age, e.g. the departure date.

    Returns:
        Age in whole years.
    """
    return day.year - born_on.year - ((day.month, day.day) < (born_on.month, born_on.day))
