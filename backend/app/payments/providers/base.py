"""Port every payment gateway adapter implements."""

import uuid
from typing import Protocol

from app.payments.domain.dtos import Authorization, CardVerification, CardVerificationRequest, PaymentRequest


class PaymentGateway(Protocol):
    """Charges the customer's card in two steps: authorize, then capture or void.

    The booking authorizes before asking the provider for the order, captures if the order was
    created and voids if it wasn't, so the customer is never charged for a booking that failed.
    """

    async def verify_card(self, request: CardVerificationRequest) -> CardVerification:
        """Checks that the card works with a small purchase, then asks to reverse it.

        It runs before the real charge is authorized, as most platforms do: purchase, check that
        it went through, request the reversal and only then follow the flow. Idempotent by
        `request.idempotency_key`: a retry never charges the card twice.

        If the purchase goes through but the reversal fails, it doesn't raise: it returns
        `reversed=False` so the booking can go on, and the caller records that the small charge
        must be refunded by hand.

        Args:
            request: The card and the currency of the booking.

        Returns:
            The verification, with whether the small purchase was given back.

        Raises:
            PaymentDeclinedError: The small purchase was declined.
            PaymentError: The token is invalid, or the key was used for another amount.
        """
        ...

    async def authorize(self, request: PaymentRequest) -> Authorization:
        """Reserves the amount on the card. Idempotent by `request.idempotency_key`.

        Args:
            request: What to charge and to which card.

        Returns:
            The authorization; the same one if the key was already used.

        Raises:
            PaymentDeclinedError: The card was declined.
            PaymentError: The key was already used for another amount.
        """
        ...

    async def capture(self, authorization_id: uuid.UUID) -> Authorization:
        """Charges an authorized amount. Capturing twice is harmless.

        Args:
            authorization_id: Id returned by `authorize`.

        Returns:
            The captured authorization.

        Raises:
            PaymentError: Unknown id, or the authorization was voided or declined.
        """
        ...

    async def void(self, authorization_id: uuid.UUID) -> Authorization:
        """Releases an authorized amount without charging it. Voiding twice is harmless.

        Args:
            authorization_id: Id returned by `authorize`.

        Returns:
            The voided authorization.

        Raises:
            PaymentError: Unknown id, or the amount was already captured.
        """
        ...

    async def get(self, authorization_id: uuid.UUID) -> Authorization | None:
        """Reads an authorization.

        Args:
            authorization_id: Id returned by `authorize`.

        Returns:
            The authorization, or `None` if the gateway doesn't know it.
        """
        ...
