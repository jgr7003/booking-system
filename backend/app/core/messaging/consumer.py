"""Consumers of a work queue, with retries and a dead-letter queue."""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from aio_pika import DeliveryMode, Message
from aio_pika.abc import AbstractChannel, AbstractIncomingMessage

from app.core.messaging.envelope import Event, InvalidMessageError, decode
from app.core.messaging.topology import QueueSpec

logger = logging.getLogger(__name__)

# AMQP header with the number of the delivery attempt, starting at 1.
ATTEMPT_HEADER = "x-attempt"


class RetryLater(Exception):
    """The handler couldn't finish for a transient reason (provider down, timeout...)."""


@dataclass(frozen=True)
class Delivery:
    """An event handed to a consumer, with its attempt number."""

    # The event.
    event: Event

    # Attempt number, starting at 1.
    attempt: int

    # Attempts allowed before the message goes to the dead-letter queue.
    max_attempts: int

    @property
    def is_last_attempt(self) -> bool:
        """Whether a failure now sends the message to the dead-letter queue."""
        return self.attempt >= self.max_attempts


# Processes one delivery. Raising `RetryLater` (or any error) schedules another attempt.
Handler = Callable[[Delivery], Awaitable[None]]


async def consume(
    channel: AbstractChannel,
    queue: QueueSpec,
    handler: Handler,
    *,
    prefetch_count: int = 10,
) -> str:
    """Starts consuming a work queue declared with `declare_topology`.

    Each message is acknowledged after the handler returns. If the handler fails, the message is
    copied to the retry queue (or, on the last attempt, to the dead-letter queue) and then
    acknowledged, so it never blocks the queue. A malformed message goes straight to the
    dead-letter queue.

    Args:
        channel: A channel with publisher confirms, used to consume and to republish.
        queue: The work queue.
        handler: What to do with each delivery. It must be idempotent.
        prefetch_count: Unacknowledged messages a consumer holds at once.

    Returns:
        The consumer tag.
    """
    await channel.set_qos(prefetch_count=prefetch_count)
    work_queue = await channel.get_queue(queue.name, ensure=False)

    async def on_message(message: AbstractIncomingMessage) -> None:
        """Runs the handler on one message and settles it."""
        attempt = int((message.headers or {}).get(ATTEMPT_HEADER, 1))
        try:
            delivery = Delivery(event=decode(message), attempt=attempt, max_attempts=queue.max_attempts)
        except InvalidMessageError:
            logger.exception("Malformed message on %s; moving it to %s", queue.name, queue.dead_letter_queue)
            await _republish(channel, message, queue.dead_letter_queue, attempt)
            await message.ack()
            return

        try:
            await handler(delivery)
        except Exception as exc:
            if isinstance(exc, RetryLater):
                logger.warning("Attempt %s of %s failed on %s: %s", attempt, queue.max_attempts, queue.name, exc)
            else:
                logger.exception("Attempt %s of %s failed on %s", attempt, queue.max_attempts, queue.name)
            target = queue.retry_queue if not delivery.is_last_attempt else queue.dead_letter_queue
            if target == queue.dead_letter_queue:
                logger.error(
                    "Message %s (%s) ran out of attempts; moved to %s",
                    delivery.event.message_id,
                    delivery.event.type,
                    target,
                )
            try:
                await _republish(channel, message, target, attempt + 1)
            except Exception:
                logger.exception("Couldn't move message %s to %s; requeueing it", message.message_id, target)
                await message.nack(requeue=True)
                return
        await message.ack()

    return await work_queue.consume(on_message)


async def _republish(channel: AbstractChannel, message: AbstractIncomingMessage, queue_name: str, attempt: int) -> None:
    """Copies a message to a queue through the default exchange, with its attempt number."""
    await channel.default_exchange.publish(
        Message(
            body=message.body,
            headers={**(message.headers or {}), ATTEMPT_HEADER: attempt},
            message_id=message.message_id,
            type=message.type,
            content_type=message.content_type,
            delivery_mode=DeliveryMode.PERSISTENT,
            timestamp=message.timestamp,
        ),
        routing_key=queue_name,
    )
