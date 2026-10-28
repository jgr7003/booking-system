"""Helpers shared by the flights tests."""

import asyncio
import contextlib
import json
import uuid
from collections.abc import AsyncIterator
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from app.core.messaging.envelope import Event
from app.flights.domain.dtos.bookings import BookingPassenger
from app.flights.domain.dtos.offers import SearchResult
from app.flights.domain.dtos.search import SearchCriteria

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict[str, Any]:
    """Loads a real provider response captured from the Duffel test environment.

    Args:
        name: Path relative to `tests/fixtures`, e.g. `"duffel/offer_request_response.json"`.

    Returns:
        The parsed JSON.
    """
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def make_criteria(**overrides: Any) -> SearchCriteria:
    """Builds valid search criteria: LHR → JFK, one adult, 30 days from today.

    Args:
        **overrides: Fields to change, e.g. `airlines=["BA"]`.

    Returns:
        The criteria.
    """
    values = {"origin": "LHR", "destination": "JFK", "departure_date": date.today() + timedelta(days=30)}
    return SearchCriteria(**(values | overrides))


class FakeFlightProvider:
    """In-memory `FlightProvider` that returns a fixed result or raises a fixed error.

    Attributes:
        calls: Criteria of every search received, in order.
    """

    # Identifier of the provider: always `"fake"`.
    name = "fake"

    def __init__(self, result: SearchResult | None = None, error: Exception | None = None) -> None:
        """Initializes the fake.

        Args:
            result: What `search` returns.
            error: If set, what `search` raises instead.
        """
        self._result = result
        self._error = error
        self.calls: list[SearchCriteria] = []

    async def search(self, criteria: SearchCriteria) -> SearchResult:
        """Records the criteria and returns the fixed result.

        Args:
            criteria: Search criteria.

        Returns:
            The result given to the constructor.

        Raises:
            Exception: The error given to the constructor, if any.
        """
        self.calls.append(criteria)
        if self._error:
            raise self._error
        return self._result


# Offer and passenger of the booking fixtures (`duffel/offer_get_response.json` and friends):
# Duffel Airways LHR → JFK, 226.75 USD, booked as order `ord_0000BBq6AsxIyF0XrJSB82`.
BOOKING_OFFER_ID = "off_034nDasbn3bsLTwi7Lxldw"

# Duffel passenger of that offer.
BOOKING_PASSENGER_ID = "pas_0000BBq6AZuVnyKVD7xG8Q"

# Booking id saved in the metadata of the captured order.
CAPTURED_BOOKING_ID = "41be601f-7471-4edf-9c9f-5162d4b02f6a"


def make_booking_passenger(**traveller_overrides: Any) -> BookingPassenger:
    """Builds a valid adult passenger (a fictitious one), with the given personal data replaced.

    Args:
        **traveller_overrides: Fields of `TravellerDetails` to change, e.g. `family_name="Muñoz"`.

    Returns:
        The passenger.
    """
    traveller = {
        "given_name": "Ana",
        "family_name": "Prueba",
        "born_on": "1990-05-20",
        "gender": "f",
        "email": "ana.prueba@example.com",
        "phone_number": "+5491112345678",
    } | traveller_overrides
    return BookingPassenger.model_validate({"title": "ms", "traveller": traveller})


class FakeBroadcaster:
    """In-memory stand-in for `EventBroadcaster`: tests push the events themselves."""

    def __init__(self) -> None:
        """Initializes the fake without subscribers."""
        self._subscribers: dict[uuid.UUID, list[asyncio.Queue[Event]]] = {}

    @contextlib.asynccontextmanager
    async def subscribe(self, aggregate_id: uuid.UUID) -> AsyncIterator[asyncio.Queue[Event]]:
        """Receives the events pushed for one entity while the context is open.

        Args:
            aggregate_id: Id of the entity.

        Yields:
            The queue of events.
        """
        queue: asyncio.Queue[Event] = asyncio.Queue()
        self._subscribers.setdefault(aggregate_id, []).append(queue)
        try:
            yield queue
        finally:
            self._subscribers[aggregate_id].remove(queue)

    def subscribers(self, aggregate_id: uuid.UUID) -> int:
        """How many streams listen to an entity.

        Args:
            aggregate_id: Id of the entity.

        Returns:
            The number of subscribers.
        """
        return len(self._subscribers.get(aggregate_id, []))

    def push(self, aggregate_id: uuid.UUID, payload: dict[str, Any]) -> None:
        """Delivers an event to the subscribers of an entity.

        Args:
            aggregate_id: Id of the entity.
            payload: Body of the event.
        """
        event = Event(message_id=uuid.uuid4(), type=f"booking.{payload['status']}", aggregate_id=aggregate_id, payload=payload)
        for queue in self._subscribers.get(aggregate_id, []):
            queue.put_nowait(event)
