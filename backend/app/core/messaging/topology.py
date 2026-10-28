"""Exchanges and queues a module declares in RabbitMQ."""

from dataclasses import dataclass

from aio_pika import ExchangeType
from aio_pika.abc import AbstractChannel


@dataclass(frozen=True)
class ExchangeSpec:
    """An exchange, e.g. `bookings.events` (topic)."""

    # Name of the exchange.
    name: str

    # Routing behavior: `direct` for commands, `topic` for events.
    type: ExchangeType


@dataclass(frozen=True)
class QueueSpec:
    """A durable work queue, with its retry queue and its dead-letter queue.

    A message that fails waits `retry_delay_s` in `<name>.retry` and comes back to the queue.
    After `max_attempts` it goes to `<name>.dlq`, where it stays for someone to look at it.
    """

    # Name of the queue, e.g. `flights.booking-worker`.
    name: str

    # Exchange the queue listens to.
    exchange: ExchangeSpec

    # Routing keys bound to the queue, e.g. `("booking.requested",)`.
    routing_keys: tuple[str, ...]

    # Wait before a failed message is delivered again.
    retry_delay_s: float = 30

    # Deliveries before the message is moved to the dead-letter queue.
    max_attempts: int = 5

    @property
    def retry_queue(self) -> str:
        """Name of the queue where failed messages wait before the next attempt."""
        return f"{self.name}.retry"

    @property
    def dead_letter_queue(self) -> str:
        """Name of the queue that keeps the messages that ran out of attempts."""
        return f"{self.name}.dlq"


@dataclass(frozen=True)
class Topology:
    """Everything a module needs in RabbitMQ."""

    # Exchanges the module publishes to.
    exchanges: tuple[ExchangeSpec, ...]

    # Work queues of the module's consumers.
    queues: tuple[QueueSpec, ...] = ()


async def declare_topology(channel: AbstractChannel, topology: Topology) -> None:
    """Declares the exchanges and queues of a topology. Declaring them again is harmless.

    Args:
        channel: An open channel.
        topology: What to declare.
    """
    for exchange in topology.exchanges:
        await channel.declare_exchange(exchange.name, exchange.type, durable=True)
    for queue in topology.queues:
        work_queue = await channel.declare_queue(queue.name, durable=True)
        for routing_key in queue.routing_keys:
            await work_queue.bind(queue.exchange.name, routing_key)
        # Expired messages go back to the work queue through the default exchange.
        await channel.declare_queue(
            queue.retry_queue,
            durable=True,
            arguments={
                "x-message-ttl": int(queue.retry_delay_s * 1000),
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": queue.name,
            },
        )
        await channel.declare_queue(queue.dead_letter_queue, durable=True)
