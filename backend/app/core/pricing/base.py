"""Port for the platform's pricing rules."""

from typing import Protocol

from app.core.money import Money


class PricingPolicy(Protocol):
    """Decides the platform's profit on top of what a provider charges.

    Shared by every module (flights, hotels...). Any class with a matching `markup` method
    satisfies it; no inheritance is needed.
    """

    def markup(self, cost: Money, key: str) -> Money:
        """Calculates the markup for a product.

        Args:
            cost: What the provider charges for the product.
            key: Stable identifier of the product, e.g. `"duffel:off_..."`. The same key must
                always produce the same markup, so the price doesn't change between search and
                booking.

        Returns:
            The markup, in the currency of `cost`.
        """
        ...
