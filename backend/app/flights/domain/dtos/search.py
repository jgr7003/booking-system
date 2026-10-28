"""What the traveler searches for: route, dates, passengers and cabin."""

from datetime import date
from enum import StrEnum
from typing import Annotated, Self

from pydantic import Field, model_validator

from app.flights.domain.constants.search import ADULT_AGE, MAX_CONNECTIONS, MIN_CONNECTIONS
from app.flights.domain.dtos.base import DTO
from app.flights.domain.validators.search import (
    AirlineCode,
    AirportCode,
    validate_passenger_limits,
    validate_route_and_dates,
)


class CabinClass(StrEnum):
    """Cabin the passengers want to travel in."""

    ECONOMY = "economy"
    PREMIUM_ECONOMY = "premium_economy"
    BUSINESS = "business"
    FIRST = "first"


class PassengerCount(DTO):
    """Who travels."""

    adults: int = Field(
        default=1, 
        ge=1, 
        description="Passengers aged 18 or over."
    )

    children_ages: list[Annotated[int, Field(ge=0, lt=ADULT_AGE)]] = Field(
        default_factory=list,
        description="Age of each passenger under 18. Ages 0-1 are infants.",
    )

    @model_validator(mode="after")
    def check_limits(self) -> Self:
        """Validates the passenger limits airlines impose.

        Returns:
            The validated instance.

        Raises:
            ValueError: See `validators.validate_passenger_limits`.
        """
        validate_passenger_limits(self.adults, self.children_ages)
        return self


class SearchCriteria(DTO):
    """What the traveler is looking for. This is the body of `POST /api/v1/flights/search`."""

    origin: AirportCode = Field(
        description="IATA code of the departure airport or city, e.g. `LHR` or `LON`. Required.",
    )

    destination: AirportCode = Field(
        description="IATA code of the arrival airport or city. Required.",
    )

    departure_date: date = Field(
        description="Outbound date. Can't be in the past. Required.",
    )

    return_date: date | None = Field(
        default=None,
        description="Inbound date for round trips; `null` for one way. Required if `return_date` is provided.",
    )

    passengers: PassengerCount = Field(
        default_factory=PassengerCount,
        description="Who travels. Defaults to one adult. Required.",
    )

    cabin_class: CabinClass | None = Field(
        default=None,
        description="Preferred cabin; `null` for any. Required if `cabin_class` is provided.",
    )

    max_connections: int = Field(
        default=1,
        ge=MIN_CONNECTIONS,
        le=MAX_CONNECTIONS,
        description="Maximum connections per slice; 0 means direct flights only.",
    )

    airlines: list[AirlineCode] | None = Field(
        default=None,
        description="Only offers sold by these airlines (2-letter IATA codes); `null` for all.",
    )

    @model_validator(mode="after")
    def check_route_and_dates(self) -> Self:
        """Validates the route and the dates.

        Returns:
            The validated instance.

        Raises:
            ValueError: See `validators.validate_route_and_dates`.
        """
        validate_route_and_dates(self.origin, self.destination, self.departure_date, self.return_date)
        return self
