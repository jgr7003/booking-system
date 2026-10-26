"""Helpers shared by the flights tests."""

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from app.flights.domain.dtos import SearchCriteria, SearchResult

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
