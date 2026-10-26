"""Wiring of the pricing policy."""

from typing import Annotated

from fastapi import Depends

from app.core.config import Settings, get_settings
from app.core.pricing.base import PricingPolicy
from app.core.pricing.fixed_fee_random_percent import FixedFeeRandomPercentPolicy


def get_pricing_policy(settings: Annotated[Settings, Depends(get_settings)]) -> PricingPolicy:
    """FastAPI dependency that provides the platform's pricing policy.

    Args:
        settings: Application settings, for the HMAC secret.

    Returns:
        The policy every module uses to calculate sale prices.
    """
    return FixedFeeRandomPercentPolicy(settings.pricing_secret.get_secret_value())
