"""Fans events from RabbitMQ out to the connections open in this API instance (SSE)."""

import asyncio
import contextlib
import logging
import uuid
from collections import defaultdict
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass

import aio_pika
from aio_pika.abc import AbstractIncomingMessage, AbstractRobustConnection

from app.core.messaging.envelope import Event, InvalidMessageError, decode
from app.core.messaging.topology import ExchangeSpec

logger = logging.getLogger(__name__)

# Wait before trying again to reach RabbitMQ when it's down at startup.
RECONNECT_DELAY_S = 5


@dataclass(frozen=True)
class EventBinding:
    """Events of an exchange that the API forwards to its subscribers."""

    # Exchange of the events.
    exchange: ExchangeSpec

    # Routing key pattern, e.g. `booking.*`.
    routing_key: str


class EventBroadcaster:
    """Delivers events to in-process subscribers, keyed by the id of the entity.

    Each API instance has its own exclusive, temporary queue bound to the exchanges it cares
    about, so every instance receives every event and forwards it to the connections it holds.
    If RabbitMQ is down, the API keeps working: subscribers just get no pushes until it's back,
    and they can always read the current state from the database.
    """

    def __init__(self, url: str, bindings: Sequence[EventBinding]) -> None:
        """Initializes the broadcaster; call `start` to connect.

        Args:
            url: AMQP URL of RabbitMQ.
            bindings: Events to listen to.
        """
        self._url = url
        self._bindings = tuple(bindings)
        self._subscribers: defaultdict[uuid.UUID, set[asyncio.Queue[Event]]] = defaultdict(set)
        self._connection: AbstractRobustConnection | None = None
        self._task: asyncio.Task[None] | None = None
        self._ready = asyncio.Event()

    async def start(self) -> None:
        """Starts connecting in the background; it doesn't wait for RabbitMQ."""
        if self._bindings:
            self._task = asyncio.create_task(self._connect())

    async def wait_ready(self, timeout_s: float) -> bool:
        """Waits until the broadcaster is listening. Meant for tests.

        Args:
            timeout_s: Max wait.

        Returns:
            Whether it is listening.
        """
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(self._ready.wait(), timeout_s)
        return self._ready.is_set()

    async def stop(self) -> None:
        """Stops listening and closes the connection."""
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        if self._connection:
            await self._connection.close()

    @contextlib.asynccontextmanager
    async def subscribe(self, aggregate_id: uuid.UUID) -> AsyncIterator[asyncio.Queue[Event]]:
        """Receives the events of one entity while the context is open.

        Subscribe **before** reading the current state, so no event is lost in between.

        Args:
            aggregate_id: Id of the entity, e.g. a booking id.

        Yields:
            A queue that gets every event of that entity.
        """
        queue: asyncio.Queue[Event] = asyncio.Queue()
        self._subscribers[aggregate_id].add(queue)
        try:
            yield queue
        finally:
            self._subscribers[aggregate_id].discard(queue)
            if not self._subscribers[aggregate_id]:
                del self._subscribers[aggregate_id]

    async def _connect(self) -> None:
        """Connects, declares the instance queue and consumes it, retrying until RabbitMQ answers."""
        while True:
            try:
                self._connection = await aio_pika.connect_robust(self._url)
                break
            except Exception as exc:
                logger.warning("RabbitMQ unreachable for events (%s); retrying in %s s", exc, RECONNECT_DELAY_S)
                await asyncio.sleep(RECONNECT_DELAY_S)
        channel = await self._connection.channel()
        queue = await channel.declare_queue(f"api.events.{uuid.uuid4().hex}", exclusive=True, auto_delete=True)
        for binding in self._bindings:
            exchange = await channel.declare_exchange(binding.exchange.name, binding.exchange.type, durable=True)
            await queue.bind(exchange, binding.routing_key)
        await queue.consume(self._dispatch, no_ack=True)
        self._ready.set()
        logger.info("Listening to events: %s", [b.routing_key for b in self._bindings])

    async def _dispatch(self, message: AbstractIncomingMessage) -> None:
        """Hands an event to the subscribers of its entity."""
        try:
            event = decode(message)
        except InvalidMessageError:
            logger.exception("Ignoring malformed event")
            return
        for queue in self._subscribers.get(event.aggregate_id, ()):
            queue.put_nowait(event)
