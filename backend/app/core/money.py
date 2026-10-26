"""Monetary amounts shared by every module."""

from decimal import ROUND_HALF_UP, Decimal

from pydantic import BaseModel, ConfigDict, Field

# One cent: precision of every sale price.
CENT = Decimal("0.01")


class Money(BaseModel):
    """An amount in a currency.

    Amounts are `Decimal` to avoid float rounding errors and are serialized as strings in JSON
    (e.g. `"402.74"`).
    """

    model_config = ConfigDict(frozen=True)

    amount: Decimal = Field(description="The amount, in units of `currency`.")

    currency: str = Field(description='ISO 4217 currency code, e.g. `"USD"`.')

    def __add__(self, other: "Money") -> "Money":
        """Adds two amounts in the same currency.

        Args:
            other: The amount to add.

        Returns:
            A new `Money` with the sum.

        Raises:
            ValueError: If the currencies differ.
        """
        if other.currency != self.currency:
            raise ValueError(f"Cannot add {other.currency} to {self.currency}")
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def rounded(self) -> "Money":
        """Rounds the amount to cents.

        Returns:
            A new `Money` rounded to 2 decimals, half up.
        """
        return Money(amount=self.amount.quantize(CENT, rounding=ROUND_HALF_UP), currency=self.currency)
