"""Database models of the flights module."""

from sqlalchemy import Float, ForeignKey, Index, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class City(Base):
    """A city served by several airports, with its own IATA code (e.g. NYC, LON).

    Cities with a single airport aren't stored: the airport's code is used instead.
    """

    __tablename__ = "cities"

    # IATA code of the city, e.g. `NYC`.
    iata_code: Mapped[str] = mapped_column(String(3), primary_key=True)

    # Name, e.g. `New York`.
    name: Mapped[str] = mapped_column(Text)

    # ISO 3166-1 alpha-2 country code.
    country_code: Mapped[str] = mapped_column(String(2))

    # Code and name normalized for searching (no accents, lower case).
    search_text: Mapped[str] = mapped_column(Text)

    __table_args__ = (
        Index(
            "ix_cities_search_text_trgm",
            "search_text",
            postgresql_using="gin",
            postgresql_ops={"search_text": "gin_trgm_ops"},
        ),
    )


class Airport(Base):
    """An airport with an IATA code."""

    __tablename__ = "airports"

    # IATA code, e.g. `JFK`.
    iata_code: Mapped[str] = mapped_column(String(3), primary_key=True)

    # ICAO code, e.g. `KJFK`.
    icao_code: Mapped[str | None] = mapped_column(String(4))

    # Name, e.g. `John F Kennedy International Airport`.
    name: Mapped[str] = mapped_column(Text)

    # City it serves; not every airport in the source has one.
    city_name: Mapped[str | None] = mapped_column(Text)

    # IATA code of its multi-airport city (e.g. `NYC`), if it belongs to one.
    city_code: Mapped[str | None] = mapped_column(ForeignKey("cities.iata_code"), index=True)

    # ISO 3166-1 alpha-2 country code.
    country_code: Mapped[str] = mapped_column(String(2))

    # IANA time zone, e.g. `America/New_York`.
    time_zone: Mapped[str] = mapped_column(Text)

    # Latitude in degrees.
    latitude: Mapped[float] = mapped_column(Float)

    # Longitude in degrees.
    longitude: Mapped[float] = mapped_column(Float)

    # Relevance for the autocomplete, from OurAirports: 4 = large with scheduled flights,
    # 3 = medium, 2 = small, 1 = other with scheduled flights, 0 = no scheduled flights or unknown.
    importance: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")

    # Code, city, name and alternative names (e.g. `Londres`) normalized for searching.
    search_text: Mapped[str] = mapped_column(Text)

    __table_args__ = (
        Index(
            "ix_airports_search_text_trgm",
            "search_text",
            postgresql_using="gin",
            postgresql_ops={"search_text": "gin_trgm_ops"},
        ),
    )
