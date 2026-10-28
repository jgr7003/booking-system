"""Booking worker process: `python -m app.workers.booking_worker`."""

import asyncio
import logging

import aio_pika
import httpx2

from app.core.config import get_settings
from app.core.db import create_engine, create_session_factory
from app.core.messaging.consumer import consume
from app.core.messaging.topology import declare_topology
from app.core.pricing.dependencies import get_pricing_policy
from app.flights.core.config import get_duffel_settings
from app.flights.core.messaging import BOOKING_WORKER_QUEUE, TOPOLOGY
from app.flights.providers.duffel.client import DuffelClient
from app.flights.providers.duffel.provider import DuffelFlightProvider
from app.flights.services.booking_worker import BookingProcessor
from app.payments.public import create_payment_gateway
from app.workers.runtime import configure_logging, stop_on_signals

logger = logging.getLogger(__name__)

# Bookings processed at once by one worker process.
PREFETCH = 4


async def main() -> None:
    """Consumes `booking.requested` until the process gets SIGTERM or SIGINT."""
    settings = get_settings()
    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    async with httpx2.AsyncClient() as http:
        processor = BookingProcessor(
            session_factory,
            DuffelFlightProvider(DuffelClient(http, get_duffel_settings())),
            get_pricing_policy(settings),
            create_payment_gateway(session_factory),
        )
        try:
            channel = await connection.channel(publisher_confirms=True)
            await declare_topology(channel, TOPOLOGY)
            await consume(channel, BOOKING_WORKER_QUEUE, processor.handle, prefetch_count=PREFETCH)
            logger.info("Booking worker consuming %s", BOOKING_WORKER_QUEUE.name)
            await stop_on_signals().wait()
        finally:
            await connection.close()
            await engine.dispose()


if __name__ == "__main__":
    configure_logging()
    asyncio.run(main())
