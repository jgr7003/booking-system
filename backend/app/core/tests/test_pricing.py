from decimal import Decimal

import pytest

from app.core.money import Money
from app.core.pricing.fixed_fee_random_percent import (
    FIXED_FEE,
    MAX_PERCENT,
    MIN_PERCENT,
    FixedFeeRandomPercentPolicy,
)

policy = FixedFeeRandomPercentPolicy("test-secret")
CENT = Decimal("0.01")


def usd(amount: str) -> Money:
    return Money(amount=Decimal(amount), currency="USD")


@pytest.mark.parametrize("cost", ["214.34", "402.74", "6146.64"])
def test_markup_is_fixed_fee_plus_percent_within_bounds(cost):
    cost = usd(cost)
    lowest = FIXED_FEE + cost.amount * MIN_PERCENT / 100
    highest = FIXED_FEE + cost.amount * MAX_PERCENT / 100

    for i in range(200):
        markup = policy.markup(cost, key=f"duffel:off_{i}")
        assert lowest - CENT <= markup.amount <= highest + CENT


def test_same_key_always_gets_the_same_markup():
    cost = usd("402.74")

    first = policy.markup(cost, key="duffel:off_034l6ScLRLhYObdEbC8k1g")
    again = FixedFeeRandomPercentPolicy("test-secret").markup(cost, key="duffel:off_034l6ScLRLhYObdEbC8k1g")

    assert first == again


def test_markup_varies_between_offers():
    cost = usd("402.74")

    markups = {policy.markup(cost, key=f"duffel:off_{i}").amount for i in range(20)}

    assert len(markups) > 10


def test_markup_depends_on_the_secret():
    cost = usd("402.74")
    key = "duffel:off_034l6ScLRLhYObdEbC8k1g"

    assert policy.markup(cost, key) != FixedFeeRandomPercentPolicy("other-secret").markup(cost, key)


def test_markup_keeps_currency_and_has_two_decimals():
    markup = policy.markup(Money(amount=Decimal("199.999"), currency="GBP"), key="duffel:off_1")

    assert markup.currency == "GBP"
    assert markup.amount.as_tuple().exponent == -2


def test_money_refuses_to_add_different_currencies():
    with pytest.raises(ValueError):
        usd("1") + Money(amount=Decimal("1"), currency="GBP")
