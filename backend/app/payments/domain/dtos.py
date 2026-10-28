"""DTOs of the payments module. They are also its public contract (see `public.py`)."""

import uuid
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.core.money import Money


class DTO(BaseModel):
    """Base of every payments DTO: immutable."""

    model_config = ConfigDict(frozen=True)


class AuthorizationStatus(StrEnum):
    """Life of a charge: authorized, then captured (charged) or voided (released)."""

    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    VOIDED = "voided"
    DECLINED = "declined"
    # Only for the small purchase that verifies a card: it was charged and then given back.
    REFUNDED = "refunded"


class PaymentRequest(DTO):
    """A charge to authorize on the customer's card."""

    idempotency_key: str = Field(
        description="Same key, same authorization: retrying never charges twice.",
    )

    amount: Money = Field(
        description="Amount to charge, in its currency.",
    )

    payment_token: str = Field(
        description="Token of the card, produced by the gateway's tokenization; never the card number.",
    )


class CardVerificationRequest(DTO):
    """A card to verify with a small purchase that is then reversed."""

    idempotency_key: str = Field(
        description="Same key, same verification: retrying never charges the card twice.",
    )

    currency: str = Field(
        description="ISO 4217 currency of the booking; the verification amount is charged in it.",
    )

    payment_token: str = Field(
        description="Token of the card, produced by the gateway's tokenization; never the card number.",
    )


class CardVerification(DTO):
    """Result of verifying a card with a small purchase."""

    id: uuid.UUID = Field(
        description="Id of the small purchase at the gateway.",
    )

    amount: Money = Field(
        description="Amount of the small purchase.",
    )

    reversed: bool = Field(
        description="Whether the small purchase was given back. If not, it is still on the card and "
        "has to be refunded by hand.",
    )


class Authorization(DTO):
    """An authorized charge, waiting to be captured or voided."""

    id: uuid.UUID = Field(
        description="Id of the authorization at the gateway.",
    )

    amount: Money = Field(
        description="Authorized amount.",
    )

    status: AuthorizationStatus = Field(
        description="Current state.",
    )
