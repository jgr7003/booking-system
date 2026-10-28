"""Validation rules of a flight search, used by the DTOs."""

from datetime import date
from typing import Annotated

from pydantic import AfterValidator

from app.flights.domain.constants.search import INFANT_MAX_AGE, MAX_PASSENGERS


def iata_code(length: int) -> AfterValidator:
    """Builds a validator that normalizes an IATA code to upper case and checks its length.

    Args:
        length: Expected length: 3 for airports and cities, 2 for airlines.

    Returns:
        A Pydantic validator to use in `Annotated`.
    """

    def validate(value: str) -> str:
        value = value.strip().upper()
        if len(value) != length or not value.isalnum():
            raise ValueError(f"must be a {length}-character IATA code")
        return value

    return AfterValidator(validate)


# 3-letter IATA code of an airport or city, normalized to upper case.
AirportCode = Annotated[str, iata_code(3)]


# 2-character IATA code of an airline, normalized to upper case.
AirlineCode = Annotated[str, iata_code(2)]


def validate_passenger_limits(adults: int, children_ages: list[int]) -> None:
    """Validates the passenger limits airlines impose.

    Args:
        adults: Passengers aged 18 or over.
        children_ages: Age of each passenger under 18.

    Raises:
        ValueError: If there are more than `MAX_PASSENGERS` passengers, or more infants than
            adults (each infant needs a different adult).
    """
    if adults + len(children_ages) > MAX_PASSENGERS:
        raise ValueError(f"at most {MAX_PASSENGERS} passengers per search")
    infants = sum(1 for age in children_ages if age <= INFANT_MAX_AGE)
    if infants > adults:
        raise ValueError("each infant (age 0-1) must travel with a different adult")


def validate_route_and_dates(
    origin: str,
    destination: str,
    departure_date: date,
    return_date: date | None,
) -> None:
    """Validates the route and the travel dates of a search.

    Args:
        origin: IATA code of the departure airport or city.
        destination: IATA code of the arrival airport or city.
        departure_date: Outbound date.
        return_date: Inbound date, or `None` for one way.

    Raises:
        ValueError: If origin and destination are equal, the departure is in the past, or the
            return is before the departure.
    """
    if origin == destination:
        raise ValueError("origin and destination must differ")
    if departure_date < date.today():
        raise ValueError("departure_date can't be in the past")
    if return_date is not None and return_date < departure_date:
        raise ValueError("return_date can't be before departure_date")
