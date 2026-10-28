"""Simulated payment gateway: approves every card except the ones ending in `0002`."""

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.money import Money
from app.payments.domain.constants import (
    FAKE_DECLINED_LAST4,
    FAKE_REVERSAL_FAILS_LAST4,
    FAKE_TOKEN_PREFIX,
    VERIFICATION_AMOUNT,
)
from app.payments.domain.dtos import (
    Authorization,
    AuthorizationStatus,
    CardVerification,
    CardVerificationRequest,
    PaymentRequest,
)
from app.payments.domain.errors import PaymentDeclinedError, PaymentError
from app.payments.domain.models import PaymentAuthorization


class FakePaymentGateway:
    """A gateway that keeps its authorizations in `payments.payment_authorizations`.

    It behaves like a remote gateway: each call runs in its own transaction, independent of the
    caller's, and authorizations are idempotent by key, so a worker that retries never charges
    twice.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        """Initializes the gateway.

        Args:
            session_factory: Factory of database sessions.
        """
        self._session_factory = session_factory

    async def verify_card(self, request: CardVerificationRequest) -> CardVerification:
        """Verifies a card with a small purchase and reverses it; see `PaymentGateway.verify_card`."""
        amount = Money(amount=Decimal(VERIFICATION_AMOUNT), currency=request.currency)
        purchase = await self.authorize(
            PaymentRequest(idempotency_key=request.idempotency_key, amount=amount, payment_token=request.payment_token)
        )
        async with self._session_factory() as session, session.begin():
            row = await session.get(PaymentAuthorization, purchase.id, with_for_update=True)
            # The small purchase is a purchase, not a hold: it is charged right away...
            if row.status == AuthorizationStatus.AUTHORIZED:
                row.status = AuthorizationStatus.CAPTURED
            # ...and then given back, unless this card can't be reversed.
            if row.status == AuthorizationStatus.CAPTURED and row.card_last4 != FAKE_REVERSAL_FAILS_LAST4:
                row.status = AuthorizationStatus.REFUNDED
            return CardVerification(
                id=row.id,
                amount=amount,
                reversed=row.status == AuthorizationStatus.REFUNDED,
            )

    async def authorize(self, request: PaymentRequest) -> Authorization:
        """Authorizes a charge; see `PaymentGateway.authorize`."""
        async with self._session_factory() as session:
            existing = await self._by_key(session, request.idempotency_key)
            if existing is None:
                existing = PaymentAuthorization(
                    id=uuid.uuid4(),
                    idempotency_key=request.idempotency_key,
                    amount=request.amount.amount,
                    currency=request.amount.currency,
                    card_last4=_last4(request.payment_token),
                    status=(
                        AuthorizationStatus.DECLINED
                        if _last4(request.payment_token) == FAKE_DECLINED_LAST4
                        else AuthorizationStatus.AUTHORIZED
                    ),
                )
                session.add(existing)
                try:
                    await session.commit()
                except IntegrityError:
                    # Another call with the same key won the race: answer with its result.
                    await session.rollback()
                    existing = await self._by_key(session, request.idempotency_key)
            if (existing.amount, existing.currency) != (request.amount.amount, request.amount.currency):
                raise PaymentError("The idempotency key was already used for another amount.")
            if existing.status == AuthorizationStatus.DECLINED:
                raise PaymentDeclinedError("The card was declined.")
            return _to_dto(existing)

    async def capture(self, authorization_id: uuid.UUID) -> Authorization:
        """Captures a charge; see `PaymentGateway.capture`."""
        return await self._move(authorization_id, AuthorizationStatus.CAPTURED, allowed_from=AuthorizationStatus.AUTHORIZED)

    async def void(self, authorization_id: uuid.UUID) -> Authorization:
        """Voids a charge; see `PaymentGateway.void`."""
        return await self._move(authorization_id, AuthorizationStatus.VOIDED, allowed_from=AuthorizationStatus.AUTHORIZED)

    async def get(self, authorization_id: uuid.UUID) -> Authorization | None:
        """Reads an authorization; see `PaymentGateway.get`."""
        async with self._session_factory() as session:
            authorization = await session.get(PaymentAuthorization, authorization_id)
            return _to_dto(authorization) if authorization is not None else None

    async def _move(
        self,
        authorization_id: uuid.UUID,
        target: AuthorizationStatus,
        *,
        allowed_from: AuthorizationStatus,
    ) -> Authorization:
        """Changes the status of an authorization; repeating the same change is harmless."""
        async with self._session_factory() as session, session.begin():
            authorization = await session.get(PaymentAuthorization, authorization_id, with_for_update=True)
            if authorization is None:
                raise PaymentError("Unknown authorization.")
            if authorization.status not in (allowed_from, target):
                raise PaymentError(f"Can't move a {authorization.status} authorization to {target}.")
            authorization.status = target
            return _to_dto(authorization)

    @staticmethod
    async def _by_key(session: AsyncSession, idempotency_key: str) -> PaymentAuthorization | None:
        """Finds the authorization of an idempotency key."""
        return await session.scalar(
            select(PaymentAuthorization).where(PaymentAuthorization.idempotency_key == idempotency_key)
        )


def _last4(payment_token: str) -> str:
    """Reads the last 4 digits of the card from a simulated token."""
    last4 = payment_token.removeprefix(FAKE_TOKEN_PREFIX)
    if not payment_token.startswith(FAKE_TOKEN_PREFIX) or len(last4) != 4 or not last4.isdigit():
        raise PaymentError(f"Invalid payment token; expected {FAKE_TOKEN_PREFIX}<last 4 digits>.")
    return last4


def _to_dto(authorization: PaymentAuthorization) -> Authorization:
    """Builds the public view of an authorization."""
    return Authorization(
        id=authorization.id,
        amount=Money(amount=authorization.amount, currency=authorization.currency),
        status=AuthorizationStatus(authorization.status),
    )
