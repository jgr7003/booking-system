"""Confirmation email process: `python -m app.workers.booking_notifier`."""

import asyncio
import logging

import aio_pika

from app.core.config import get_settings
from app.core.db import create_engine, create_session_factory
from app.core.messaging.consumer import consume
from app.core.messaging.topology import declare_topology
from app.flights.core.messaging import BOOKING_NOTIFIER_QUEUE, TOPOLOGY
from app.flights.notifications.booking_notifier import BookingConfirmationNotifier
from app.notifications.public import create_email_sender
from app.workers.runtime import configure_logging, stop_on_signals

logger = logging.getLogger(__name__)


async def main() -> None:
    """Consumes `booking.confirmed` until the process gets SIGTERM or SIGINT."""
    settings = get_settings()
    engine = create_engine(settings.database_url)
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    notifier = BookingConfirmationNotifier(
        create_session_factory(engine), create_email_sender(), app_url=settings.app_url
    )
    try:
        channel = await connection.channel(publisher_confirms=True)
        await declare_topology(channel, TOPOLOGY)
        await consume(channel, BOOKING_NOTIFIER_QUEUE, notifier.handle)
        logger.info("Booking notifier consuming %s", BOOKING_NOTIFIER_QUEUE.name)
        await stop_on_signals().wait()
    finally:
        await connection.close()
        await engine.dispose()


if __name__ == "__main__":
    configure_logging()
    asyncio.run(main())
