"""Outbox, relay, consumer, inbox and broadcaster against the test PostgreSQL and RabbitMQ."""

import asyncio
import os
import uuid

import aio_pika
import pytest
from aio_pika import ExchangeType
from sqlalchemy import select

from app.core.messaging.broadcaster import EventBinding, EventBroadcaster
from app.core.messaging.consumer import ATTEMPT_HEADER, Delivery, RetryLater, consume
from app.core.messaging.inbox import mark_processed, was_processed
from app.core.messaging.models import OutboxMessage
from app.core.messaging.outbox import add_event
from app.core.messaging.relay import publish_pending
from app.core.messaging.topology import ExchangeSpec, QueueSpec, Topology, declare_topology

pytestmark = pytest.mark.anyio

# Routing key of the test command.
REQUESTED = "thing.requested"


async def wait_until(condition, timeout_s: float = 5) -> None:
    """Polls `condition` until it is true.

    Args:
        condition: A function without arguments returning a bool.
        timeout_s: Max wait.

    Raises:
        AssertionError: The condition didn't hold in time.
    """
    deadline = asyncio.get_running_loop().time() + timeout_s
    while not condition():
        if asyncio.get_running_loop().time() > deadline:
            raise AssertionError("condition not met in time")
        await asyncio.sleep(0.05)


@pytest.fixture
async def channel(rabbitmq_connection):
    """Channel with publisher confirms on the test vhost.

    Args:
        rabbitmq_connection: Connection to the test vhost.

    Yields:
        The channel, closed after the test.
    """
    channel = await rabbitmq_connection.channel(publisher_confirms=True)
    yield channel
    await channel.close()


@pytest.fixture
async def work_queue(channel):
    """A command exchange and a work queue with unique names, deleted after the test.

    Retries are fast (0.2 s) and there are 3 attempts, so tests don't wait long.

    Args:
        channel: Channel on the test vhost.

    Yields:
        The `QueueSpec`.
    """
    suffix = uuid.uuid4().hex[:8]
    exchange = ExchangeSpec(f"test.commands.{suffix}", ExchangeType.DIRECT)
    queue = QueueSpec(f"test.work.{suffix}", exchange, (REQUESTED,), retry_delay_s=0.2, max_attempts=3)
    await declare_topology(channel, Topology(exchanges=(exchange,), queues=(queue,)))
    yield queue
    for name in (queue.name, queue.retry_queue, queue.dead_letter_queue):
        await channel.queue_delete(name)
    await channel.exchange_delete(exchange.name)


async def save_event(session_factory, queue: QueueSpec, *, commit: bool = True) -> uuid.UUID:
    """Adds one command to the outbox in its own transaction.

    Args:
        session_factory: Factory of sessions on the test database.
        queue: Work queue whose exchange receives the command.
        commit: Whether to commit or roll back the transaction.

    Returns:
        The message id.
    """
    async with session_factory() as session:
        message_id = add_event(
            session,
            exchange=queue.exchange.name,
            routing_key=REQUESTED,
            aggregate_id=uuid.uuid4(),
            payload={"n": 1},
        )
        await (session.commit() if commit else session.rollback())
    return message_id


async def drain(channel, queue_name: str) -> list[aio_pika.abc.AbstractIncomingMessage]:
    """Takes every message left in a queue, acknowledging them.

    Args:
        channel: Channel on the test vhost.
        queue_name: Queue to empty.

    Returns:
        The messages, in order.
    """
    queue = await channel.get_queue(queue_name)
    messages = []
    while (message := await queue.get(fail=False, timeout=2)) is not None:
        await message.ack()
        messages.append(message)
    return messages


async def test_relay_publishes_committed_events_and_never_rolled_back_ones(db_session_factory, channel, work_queue):
    committed = await save_event(db_session_factory, work_queue)
    await save_event(db_session_factory, work_queue, commit=False)

    assert await publish_pending(db_session_factory, channel) == 1

    messages = await drain(channel, work_queue.name)
    assert [m.message_id for m in messages] == [str(committed)]
    assert messages[0].type == REQUESTED
    async with db_session_factory() as session:
        row = await session.get(OutboxMessage, committed)
        assert row.published_at is not None


async def test_relay_doesnt_publish_twice(db_session_factory, channel, work_queue):
    await save_event(db_session_factory, work_queue)
    await publish_pending(db_session_factory, channel)

    assert await publish_pending(db_session_factory, channel) == 0
    assert len(await drain(channel, work_queue.name)) == 1


async def test_two_relays_in_parallel_publish_each_event_once(db_session_factory, rabbitmq_connection, work_queue):
    saved = {await save_event(db_session_factory, work_queue) for _ in range(40)}
    channels = [await rabbitmq_connection.channel(publisher_confirms=True) for _ in range(2)]

    async def relay(channel) -> None:
        """Publishes in small batches until nothing is left."""
        while await publish_pending(db_session_factory, channel, batch_size=3):
            pass

    await asyncio.gather(*(relay(c) for c in channels))

    received = [uuid.UUID(m.message_id) for m in await drain(channels[0], work_queue.name)]
    assert sorted(received) == sorted(saved)
    async with db_session_factory() as session:
        pending = await session.scalars(select(OutboxMessage).where(OutboxMessage.published_at.is_(None)))
        assert pending.all() == []


async def test_consumer_hands_each_message_to_the_handler_and_acknowledges_it(db_session_factory, channel, work_queue):
    message_id = await save_event(db_session_factory, work_queue)
    await publish_pending(db_session_factory, channel)
    handled: list[Delivery] = []

    async def handler(delivery: Delivery) -> None:
        """Records the delivery."""
        handled.append(delivery)

    await consume(channel, work_queue, handler)
    await wait_until(lambda: handled)

    assert handled[0].event.message_id == message_id
    assert handled[0].event.type == REQUESTED
    assert handled[0].attempt == 1
    await asyncio.sleep(0.2)
    declared = await channel.declare_queue(work_queue.name, passive=True)
    assert declared.declaration_result.message_count == 0


async def test_consumer_retries_a_failing_message_then_moves_it_to_the_dead_letter_queue(
    db_session_factory, channel, work_queue
):
    message_id = await save_event(db_session_factory, work_queue)
    await publish_pending(db_session_factory, channel)
    attempts: list[tuple[int, bool]] = []

    async def handler(delivery: Delivery) -> None:
        """Always fails transiently."""
        attempts.append((delivery.attempt, delivery.is_last_attempt))
        raise RetryLater("provider down")

    await consume(channel, work_queue, handler)
    await wait_until(lambda: len(attempts) == 3)
    await asyncio.sleep(0.5)

    assert attempts == [(1, False), (2, False), (3, True)]
    dead = await drain(channel, work_queue.dead_letter_queue)
    assert [m.message_id for m in dead] == [str(message_id)]
    assert dead[0].type == REQUESTED
    assert dead[0].headers[ATTEMPT_HEADER] == 4


async def test_consumer_moves_a_malformed_message_to_the_dead_letter_queue(channel, work_queue):
    handled = []

    async def handler(delivery: Delivery) -> None:
        """Records the delivery."""
        handled.append(delivery)

    await consume(channel, work_queue, handler)
    await channel.default_exchange.publish(aio_pika.Message(b"not json"), routing_key=work_queue.name)
    await asyncio.sleep(0.5)

    assert handled == []
    assert len(await drain(channel, work_queue.dead_letter_queue)) == 1


async def test_inbox_remembers_processed_messages_per_consumer(db_session_factory):
    message_id = uuid.uuid4()
    async with db_session_factory() as session:
        await mark_processed(session, message_id, "worker-a")
        await session.commit()

    async with db_session_factory() as session:
        assert await was_processed(session, message_id, "worker-a")
        assert not await was_processed(session, message_id, "worker-b")


async def test_marking_a_message_twice_is_harmless(db_session_factory):
    message_id = uuid.uuid4()
    for _ in range(2):
        async with db_session_factory() as session:
            await mark_processed(session, message_id, "worker-a")
            await session.commit()

    async with db_session_factory() as session:
        assert await was_processed(session, message_id, "worker-a")


async def test_broadcaster_delivers_events_only_to_subscribers_of_that_entity(db_session_factory, channel):
    # The channel fixture already skips the test when the variable is missing.
    rabbitmq_url = os.environ["TEST_RABBITMQ_URL"]
    events = ExchangeSpec(f"test.events.{uuid.uuid4().hex[:8]}", ExchangeType.TOPIC)
    await declare_topology(channel, Topology(exchanges=(events,)))
    broadcaster = EventBroadcaster(rabbitmq_url, [EventBinding(events, "thing.*")])
    await broadcaster.start()
    try:
        assert await broadcaster.wait_ready(timeout_s=5)
        mine, other = uuid.uuid4(), uuid.uuid4()
        async with broadcaster.subscribe(mine) as received:
            async with db_session_factory() as session:
                for aggregate_id, status in ((other, "x"), (mine, "confirmed")):
                    add_event(
                        session,
                        exchange=events.name,
                        routing_key="thing.confirmed",
                        aggregate_id=aggregate_id,
                        payload={"status": status},
                    )
                await session.commit()
            await publish_pending(db_session_factory, channel)

            event = await asyncio.wait_for(received.get(), timeout=5)
            assert event.aggregate_id == mine
            assert event.payload == {"status": "confirmed"}
            await asyncio.sleep(0.2)
            assert received.empty()
    finally:
        await broadcaster.stop()
        await channel.exchange_delete(events.name)
