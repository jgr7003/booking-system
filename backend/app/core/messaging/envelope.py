"""How an outbox event travels as an AMQP message, and back."""

import json
import uuid
from dataclasses import dataclass
from typing import Any

from aio_pika import DeliveryMode, Message
from aio_pika.abc import AbstractIncomingMessage

from app.core.messaging.models import OutboxMessage

# AMQP header with the id of the entity the event is about.
AGGREGATE_ID_HEADER = "aggregate-id"


class InvalidMessageError(Exception):
    """A message doesn't have the shape the outbox relay gives it."""


@dataclass(frozen=True)
class Event:
    """An event received from RabbitMQ."""

    # Id of the message (`outbox.id`), the key of the consumers' inbox.
    message_id: uuid.UUID

    # Event type, e.g. `booking.confirmed`.
    type: str

    # Id of the entity the event is about.
    aggregate_id: uuid.UUID

    # Body of the event.
    payload: dict[str, Any]


def encode(message: OutboxMessage) -> Message:
    """Builds the AMQP message of an outbox event.

    The event type also travels in the `type` property, because a message that comes back from
    the retry queue arrives with the queue name as routing key.

    Args:
        message: The outbox row.

    Returns:
        A persistent JSON message.
    """
    return Message(
        body=json.dumps(message.payload).encode(),
        message_id=str(message.id),
        type=message.routing_key,
        content_type="application/json",
        delivery_mode=DeliveryMode.PERSISTENT,
        timestamp=message.created_at,
        headers={AGGREGATE_ID_HEADER: str(message.aggregate_id)},
    )


def decode(message: AbstractIncomingMessage) -> Event:
    """Reads an event from an incoming AMQP message.

    Args:
        message: The message as received.

    Returns:
        The event.

    Raises:
        InvalidMessageError: A property is missing or the body isn't a JSON object.
    """
    try:
        payload = json.loads(message.body)
        if not isinstance(payload, dict) or not message.type:
            raise ValueError("unexpected body or type")
        return Event(
            message_id=uuid.UUID(str(message.message_id)),
            type=message.type,
            aggregate_id=uuid.UUID(str((message.headers or {})[AGGREGATE_ID_HEADER])),
            payload=payload,
        )
    except (ValueError, KeyError, TypeError) as exc:
        raise InvalidMessageError(f"Malformed message {message.message_id!r}: {exc}") from exc
