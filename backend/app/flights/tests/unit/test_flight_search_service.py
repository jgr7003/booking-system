from decimal import Decimal

import pytest

from app.core.money import Money
from app.core.pricing.fixed_fee_random_percent import FixedFeeRandomPercentPolicy
from app.flights.domain.errors.provider import ProviderTimeoutError
from app.flights.services.flight_search import FlightSearchService
from app.flights.tests.support import FakeFlightProvider, make_criteria

pytestmark = pytest.mark.anyio

ONE_STOP_LH = "off_034l6ScLRLhYObdEbC8k1g"


class FlatMarkup:
    def __init__(self, amount: str) -> None:
        self.amount = Decimal(amount)
        self.keys: list[str] = []

    def markup(self, cost: Money, key: str) -> Money:
        self.keys.append(key)
        return Money(amount=self.amount, currency=cost.currency)


def all_fares(result):
    return {fare.offer_id: fare for flight in result.flights for fare in flight.fares}


async def test_sale_price_is_cost_plus_markup(search_result):
    service = FlightSearchService(FakeFlightProvider(search_result), FlatMarkup("10.00"))

    result = await service.search(make_criteria())

    fare = all_fares(result)[ONE_STOP_LH]
    assert fare.markup == Money(amount=Decimal("10.00"), currency="USD")
    assert fare.price.total.amount == Decimal("412.74")
    # The markup goes into the base fare; taxes stay as the provider charges them.
    assert fare.price.base.amount == Decimal("34.07")
    assert fare.price.taxes == fare.cost.taxes
    assert fare.cost.total.amount == Decimal("402.74")


async def test_markup_key_identifies_provider_and_offer(search_result):
    pricing = FlatMarkup("1")
    service = FlightSearchService(FakeFlightProvider(search_result), pricing)

    await service.search(make_criteria())

    assert f"duffel:{ONE_STOP_LH}" in pricing.keys


async def test_keeps_search_and_passengers(search_result):
    service = FlightSearchService(FakeFlightProvider(search_result), FlatMarkup("1"))

    result = await service.search(make_criteria())

    assert result.search_id == "orq_0000BBiPI0fBoJ3vgP3eAA"
    assert [p.id for p in result.passengers] == ["pas_0000BBiPI0fXmzLVhVDviC"]
    assert len(all_fares(result)) == 56


async def test_same_offer_gets_the_same_price_in_every_search(search_result):
    service = FlightSearchService(FakeFlightProvider(search_result), FixedFeeRandomPercentPolicy("test-secret"))

    first = all_fares(await service.search(make_criteria()))
    second = all_fares(await service.search(make_criteria()))

    assert {k: f.price for k, f in first.items()} == {k: f.price for k, f in second.items()}


async def test_provider_errors_propagate():
    service = FlightSearchService(FakeFlightProvider(error=ProviderTimeoutError("slow")), FlatMarkup("1"))

    with pytest.raises(ProviderTimeoutError):
        await service.search(make_criteria())
