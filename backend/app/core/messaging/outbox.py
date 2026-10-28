"""Transactional Outbox: events are saved in the same transaction as the change they announce."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.messaging.models import OutboxMessage


def add_event(
    session: AsyncSession,
    *,
    exchange: str,
    routing_key: str,
    aggregate_id: uuid.UUID,
    payload: dict[str, Any],
) -> uuid.UUID:
    """Adds an event to the outbox, inside the caller's transaction.

    The event is published only if that transaction commits, and it is published even if the
    process dies right after committing: the relay picks it up from the table.

    Args:
        session: Session of the transaction that changes the state.
        exchange: Exchange to publish to.
        routing_key: Routing key, which is also the event type.
        aggregate_id: Id of the entity the event is about.
        payload: JSON body. Never personal data: only ids, states and versions.

    Returns:
        The id of the message.
    """
    message = OutboxMessage(
        id=uuid.uuid4(),
        exchange=exchange,
        routing_key=routing_key,
        aggregate_id=aggregate_id,
        payload=payload,
    )
    session.add(message)
    return message.id
