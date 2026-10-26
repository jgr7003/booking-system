"""Pricing policy: fixed fee plus a deterministic random percentage (architecture option C)."""

import hashlib
import hmac
from decimal import Decimal

from app.core.money import Money

# Fixed fee added to every sale, in the currency of the product.
FIXED_FEE = Decimal("8.00")

# Lowest percentage of the cost added as markup.
MIN_PERCENT = Decimal("3")

# Highest percentage of the cost added as markup.
MAX_PERCENT = Decimal("6")


class FixedFeeRandomPercentPolicy:
    """Markup = `FIXED_FEE` + cost × a random % in [`MIN_PERCENT`, `MAX_PERCENT`].

    The "random" percentage is derived from `HMAC(secret, key)`: the same product always gets the
    same markup (search, refresh and booking agree) without storing anything, and it can't be
    predicted from outside without the secret.

    Implements `app.core.pricing.base.PricingPolicy`.
    """

    def __init__(self, secret: str) -> None:
        """Initializes the policy.

        Args:
            secret: HMAC key. Changing it changes every markup.
        """
        self._secret = secret.encode()

    def markup(self, cost: Money, key: str) -> Money:
        """Calculates the markup for a product.

        Args:
            cost: What the provider charges for the product.
            key: Stable identifier of the product, e.g. `"duffel:off_..."`.

        Returns:
            The markup in the currency of `cost`, rounded to 2 decimals.
        """
        percent = MIN_PERCENT + (MAX_PERCENT - MIN_PERCENT) * self._fraction(key)
        amount = FIXED_FEE + cost.amount * percent / 100
        return Money(amount=amount, currency=cost.currency).rounded()

    def _fraction(self, key: str) -> Decimal:
        """Maps `key` to a deterministic number in [0, 1)."""
        digest = hmac.new(self._secret, key.encode(), hashlib.sha256).digest()
        return Decimal(int.from_bytes(digest[:8], "big")) / Decimal(2**64)
