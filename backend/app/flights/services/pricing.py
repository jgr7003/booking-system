"""Sale price of an offer, shared by the search and the booking."""

from app.core.pricing.base import PricingPolicy
from app.flights.domain.dtos.offers import Offer, OfferAmounts


def apply_pricing(offer: Offer, pricing: PricingPolicy) -> Offer:
    """Sets the sale price of an offer.

    Taxes stay as charged by the provider; the markup goes into the base fare. The markup is
    keyed by `provider:offer_id`, so the same offer has the same price in the search, when it is
    refreshed and when it is booked.

    Args:
        offer: Offer with its cost.
        pricing: Rule that decides the markup.

    Returns:
        A copy of the offer with `price` and `markup` set.
    """
    markup = pricing.markup(offer.cost.total, key=f"{offer.provider}:{offer.id}")
    price = OfferAmounts(
        total=offer.cost.total + markup,
        base=offer.cost.base + markup if offer.cost.base is not None else None,
        taxes=offer.cost.taxes,
    )
    return offer.model_copy(update={"price": price, "markup": markup})
