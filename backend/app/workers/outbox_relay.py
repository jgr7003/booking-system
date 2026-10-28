"""Outbox relay process: `python -m app.workers.outbox_relay`."""

import asyncio

import aio_pika

from app.core.config import get_settings
from app.core.db import create_engine, create_session_factory
from app.core.messaging.relay import run_relay
from app.flights.core.messaging import TOPOLOGY as FLIGHTS_TOPOLOGY
from app.workers.runtime import configure_logging, stop_on_signals

# Exchanges and queues of every module.
TOPOLOGIES = (FLIGHTS_TOPOLOGY,)


async def main() -> None:
    """Runs the relay until the process gets SIGTERM or SIGINT."""
    settings = get_settings()
    engine = create_engine(settings.database_url)
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    try:
        await run_relay(
            create_session_factory(engine),
            connection,
            TOPOLOGIES,
            poll_interval_s=settings.outbox_poll_interval_s,
            stop=stop_on_signals(),
        )
    finally:
        await connection.close()
        await engine.dispose()


if __name__ == "__main__":
    configure_logging()
    asyncio.run(main())
