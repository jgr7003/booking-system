"""Inbox: makes consumers idempotent, since RabbitMQ delivers each message at least once."""

import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.messaging.models import InboxMessage


async def was_processed(session: AsyncSession, message_id: uuid.UUID, consumer: str) -> bool:
    """Tells whether a consumer already processed a message.

    Args:
        session: An open session.
        message_id: Id of the message.
        consumer: Name of the consumer.

    Returns:
        `True` if the message is in the consumer's inbox.
    """
    found = await session.scalar(
        select(InboxMessage.message_id).where(
            InboxMessage.message_id == message_id,
            InboxMessage.consumer == consumer,
        )
    )
    return found is not None


async def mark_processed(session: AsyncSession, message_id: uuid.UUID, consumer: str) -> None:
    """Records a message as processed, inside the transaction that applies its effect.

    Recording it twice is harmless. The inbox lets a consumer skip a redelivered message
    without redoing work; what guarantees the effect is applied once is the consumer's own
    check, under a row lock, of the state it changes.

    Args:
        session: Session of the transaction that applies the effect.
        message_id: Id of the message.
        consumer: Name of the consumer.
    """
    await session.execute(
        insert(InboxMessage).values(message_id=message_id, consumer=consumer).on_conflict_do_nothing()
    )
