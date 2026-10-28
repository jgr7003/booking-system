"""Airport and city autocomplete."""

from enum import StrEnum

from pydantic import Field

from app.flights.domain.dtos.base import DTO


class PlaceType(StrEnum):
    """Kind of place a traveler can fly from or to."""

    CITY = "city"
    AIRPORT = "airport"


class PlaceSuggestion(DTO):
    """A city or airport that matches what the traveler typed."""

    type: PlaceType = Field(
        description="`city` (all its airports) or `airport`.",
    )

    code: str = Field(
        description="IATA code to search with, e.g. `NYC` or `JFK`.",
    )

    name: str = Field(
        description="Name of the city or airport.",
    )

    city: str | None = Field(
        default=None,
        description="City the airport serves; `null` for cities and for airports without one.",
    )

    country_code: str = Field(
        description="ISO 3166-1 alpha-2 country code.",
    )

    time_zone: str | None = Field(
        default=None,
        description="IANA time zone of the airport; `null` for cities.",
    )

    airports: list[str] = Field(
        default_factory=list,
        description="IATA codes of the city's airports; empty for airports.",
    )
