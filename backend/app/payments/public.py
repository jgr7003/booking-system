"""Public interface of the payments module: the only thing other modules may import.

Example, from a vertical that charges for a booking::

    from app.payments.public import PaymentRequest, create_payment_gateway

    gateway = create_payment_gateway(session_factory)
    authorization = await gateway.authorize(PaymentRequest(...))
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.payments.domain.dtos import (
    Authorization,
    AuthorizationStatus,
    CardVerification,
    CardVerificationRequest,
    PaymentRequest,
)
from app.payments.domain.errors import PaymentDeclinedError, PaymentError
from app.payments.providers.base import PaymentGateway
from app.payments.providers.fake.gateway import FakePaymentGateway


def create_payment_gateway(session_factory: async_sessionmaker[AsyncSession]) -> PaymentGateway:
    """Returns the payment gateway in use: the simulated one until a real one is chosen.

    Args:
        session_factory: Factory of database sessions.

    Returns:
        The gateway.
    """
    return FakePaymentGateway(session_factory)


__all__ = [
    "Authorization",
    "AuthorizationStatus",
    "CardVerification",
    "CardVerificationRequest",
    "PaymentDeclinedError",
    "PaymentError",
    "PaymentGateway",
    "PaymentRequest",
    "create_payment_gateway",
]
