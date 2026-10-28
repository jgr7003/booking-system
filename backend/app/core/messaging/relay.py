"""Outbox relay: publishes the pending outbox events to RabbitMQ."""

import asyncio
import contextlib
import logging
from collections.abc import Sequence
from datetime import UTC, datetime

from aio_pika.abc import AbstractChannel, AbstractConnection
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.messaging.envelope import encode
from app.core.messaging.models import OutboxMessage
from app.core.messaging.topology import Topology, declare_topology

logger = logging.getLogger(__name__)

# Events published per transaction.
BATCH_SIZE = 100


async def publish_pending(
    session_factory: async_sessionmaker[AsyncSession],
    channel: AbstractChannel,
    *,
    batch_size: int = BATCH_SIZE,
) -> int:
    """Publishes one batch of pending events, oldest first.

    The rows are locked with `FOR UPDATE SKIP LOCKED`, so several relays can run at once without
    publishing the same event. Each event is marked as published only after RabbitMQ confirms
    it (publisher confirms). If the relay dies in between, the event is published again: the
    guarantee is *at-least-once* and consumers deduplicate with the inbox.

    Args:
        session_factory: Factory of database sessions.
        channel: A channel with publisher confirms.
        batch_size: Max events to publish.

    Returns:
        How many events were published.
    """
    async with session_factory() as session, session.begin():
        messages = (
            await session.scalars(
                select(OutboxMessage)
                .where(OutboxMessage.published_at.is_(None))
                .order_by(OutboxMessage.created_at)
                .limit(batch_size)
                .with_for_update(skip_locked=True)
            )
        ).all()
        for message in messages:
            exchange = await channel.get_exchange(message.exchange, ensure=False)
            # Not mandatory: an event nobody listens to (no API instance running) is dropped.
            # Commands always have their work queue, declared by the relay's topologies.
            await exchange.publish(encode(message), routing_key=message.routing_key, mandatory=False)
            message.published_at = datetime.now(UTC)
    return len(messages)


async def run_relay(
    session_factory: async_sessionmaker[AsyncSession],
    connection: AbstractConnection,
    topologies: Sequence[Topology],
    *,
    poll_interval_s: float,
    stop: asyncio.Event,
) -> None:
    """Publishes pending events until `stop` is set.

    It declares the topologies first, so commands are never published to a missing queue. When
    there is nothing to publish it waits `poll_interval_s`. Errors (database or RabbitMQ down)
    are logged and retried after the same wait.

    Args:
        session_factory: Factory of database sessions.
        connection: A RabbitMQ connection (robust, so it reconnects on its own).
        topologies: Exchanges and queues of every module.
        poll_interval_s: Wait between empty polls.
        stop: Set it to finish the loop.
    """
    channel = await connection.channel(publisher_confirms=True)
    for topology in topologies:
        await declare_topology(channel, topology)
    logger.info("Outbox relay started")
    while not stop.is_set():
        try:
            published = await publish_pending(session_factory, channel)
        except Exception:
            logger.exception("Outbox relay failed; retrying in %s s", poll_interval_s)
            published = 0
        if published:
            logger.info("Published %s outbox events", published)
        else:
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), poll_interval_s)
    logger.info("Outbox relay stopped")
