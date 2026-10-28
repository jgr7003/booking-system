import asyncio
from decimal import Decimal

import pytest

from app.core.money import Money
from app.payments.public import (
    AuthorizationStatus,
    CardVerificationRequest,
    PaymentDeclinedError,
    PaymentError,
    PaymentRequest,
    create_payment_gateway,
)

pytestmark = pytest.mark.anyio


def request(key: str = "booking-1", amount: str = "524.44", token: str = "tok_fake_4242") -> PaymentRequest:
    """A charge in USD.

    Args:
        key: Idempotency key.
        amount: Amount to charge.
        token: Simulated card token.

    Returns:
        The request.
    """
    return PaymentRequest(idempotency_key=key, amount=Money(amount=Decimal(amount), currency="USD"), payment_token=token)


async def test_authorizing_twice_with_the_same_key_returns_the_same_authorization(db_session_factory):
    gateway = create_payment_gateway(db_session_factory)

    first, second = await asyncio.gather(gateway.authorize(request()), gateway.authorize(request()))

    assert first == second
    assert first.status == AuthorizationStatus.AUTHORIZED
    assert first.amount == Money(amount=Decimal("524.44"), currency="USD")


async def test_reusing_a_key_for_another_amount_fails(db_session_factory):
    gateway = create_payment_gateway(db_session_factory)
    await gateway.authorize(request())

    with pytest.raises(PaymentError, match="another amount"):
        await gateway.authorize(request(amount="600.00"))


async def test_cards_ending_in_0002_are_declined_every_time(db_session_factory):
    gateway = create_payment_gateway(db_session_factory)

    for _ in range(2):
        with pytest.raises(PaymentDeclinedError):
            await gateway.authorize(request(token="tok_fake_0002"))


async def test_rejects_a_token_that_isnt_a_simulated_one(db_session_factory):
    with pytest.raises(PaymentError, match="Invalid payment token"):
        await create_payment_gateway(db_session_factory).authorize(request(token="4111111111111111"))


async def test_capture_and_void_are_idempotent_and_exclusive(db_session_factory):
    gateway = create_payment_gateway(db_session_factory)
    captured = await gateway.authorize(request("captured"))
    voided = await gateway.authorize(request("voided"))

    assert (await gateway.capture(captured.id)).status == AuthorizationStatus.CAPTURED
    assert (await gateway.capture(captured.id)).status == AuthorizationStatus.CAPTURED
    assert (await gateway.void(voided.id)).status == AuthorizationStatus.VOIDED
    assert (await gateway.void(voided.id)).status == AuthorizationStatus.VOIDED
    with pytest.raises(PaymentError):
        await gateway.void(captured.id)
    with pytest.raises(PaymentError):
        await gateway.capture(voided.id)


def verification(key: str = "booking-1:verification", token: str = "tok_fake_4242") -> CardVerificationRequest:
    """A card verification in USD."""
    return CardVerificationRequest(idempotency_key=key, currency="USD", payment_token=token)


async def test_verifying_a_card_charges_a_small_purchase_and_reverses_it(db_session_factory):
    gateway = create_payment_gateway(db_session_factory)

    result = await gateway.verify_card(verification())

    assert result.amount == Money(amount=Decimal("1.00"), currency="USD")
    assert result.reversed
    # The small purchase is not left on the card, and it is not the booking's charge.
    assert (await gateway.get(result.id)).status == AuthorizationStatus.REFUNDED


async def test_verifying_a_declined_card_raises_and_charges_nothing(db_session_factory):
    gateway = create_payment_gateway(db_session_factory)

    with pytest.raises(PaymentDeclinedError):
        await gateway.verify_card(verification(token="tok_fake_0002"))


async def test_if_the_reversal_fails_it_says_so_instead_of_raising(db_session_factory):
    gateway = create_payment_gateway(db_session_factory)

    result = await gateway.verify_card(verification(token="tok_fake_0003"))

    assert not result.reversed
    assert (await gateway.get(result.id)).status == AuthorizationStatus.CAPTURED


async def test_verifying_twice_with_the_same_key_charges_once(db_session_factory):
    gateway = create_payment_gateway(db_session_factory)

    first, second = await asyncio.gather(gateway.verify_card(verification()), gateway.verify_card(verification()))

    assert first.id == second.id
    assert first.reversed and second.reversed
